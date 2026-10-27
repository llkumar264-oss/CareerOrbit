import csv, hashlib, io, json, re, secrets, zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pypdf import PdfReader
from docx import Document
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from .config import settings, validate_runtime
from .db import Base, engine, get_db, now
from .models import *
from .schemas import *
from .security import current_user, passwords, create_session, token_hash, cipher, audit
from .matching import company_key, match
from . import providers, mail
from .outreach import write_email, validate_draft, resume_bytes, scope_hash

@asynccontextmanager
async def lifespan(app):
    validate_runtime()
    cipher(); Base.metadata.create_all(engine)
    yield
app=FastAPI(title='CareerOrbit API',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[settings.app_url],allow_credentials=True,allow_methods=['GET','POST','PUT','DELETE','OPTIONS'],allow_headers=['Content-Type','X-CareerOrbit-Request'])
@app.middleware('http')
async def headers(request,call_next):
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff'; r.headers['Referrer-Policy']='no-referrer'; r.headers['Cache-Control']='no-store'
    return r
@app.exception_handler(providers.ProviderError)
async def provider_failure(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=502,content={'detail':str(exc)})
def owned(db,model,id,user):
    obj=db.get(model,id)
    if not obj: raise HTTPException(404,'Record not found')
    owner=getattr(obj,'user_id',None)
    if owner is None and hasattr(obj,'campaign_id'):
        c=db.get(Campaign,obj.campaign_id); owner=c.user_id if c else None
    if owner!=user.id: raise HTTPException(404,'Record not found')
    return obj
def data(obj,omit=()): return {col.name:getattr(obj,col.name) for col in obj.__table__.columns if col.name not in omit}
def cookie(response,token): response.set_cookie('careerorbit_session',token,httponly=True,secure=settings.production,samesite='lax',max_age=604800,path='/')
def public_origin(request):
    if request.headers.get('origin')!=settings.app_url or request.headers.get('x-careerorbit-request')!='1': raise HTTPException(403,'Untrusted request origin')

def usage(db,user,c,provider):
    since=now().replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    n=db.scalar(select(func.count()).select_from(Usage).where(Usage.user_id==user.id,Usage.created_at>=since))
    if n>=c.preferences.get('monthly_api_call_cap',300): raise HTTPException(429,'Monthly API-call budget reached')
    db.add(Usage(user_id=user.id,provider=provider)); db.commit()

@app.get('/api/health')
def health(db=Depends(get_db)):
    db.execute(select(1)); return {'status':'ok','live_sending':'approval required','version':'0.1.0'}
@app.post('/api/auth/register')
def register(payload:Credentials,request:Request,response:Response,db=Depends(get_db)):
    public_origin(request)
    user=User(email=str(payload.email).lower(),password_hash=passwords.hash(payload.password))
    db.add(user)
    try: db.flush()
    except IntegrityError: db.rollback(); raise HTTPException(409,'Account already exists')
    db.add(Profile(user_id=user.id,data={},confirmed=False)); db.commit()
    cookie(response,create_session(db,user)); return {'id':user.id,'email':user.email}
@app.post('/api/auth/login')
def login(payload:Credentials,request:Request,response:Response,db=Depends(get_db)):
    public_origin(request)
    # Persistent audit-based throttling survives process restarts.
    identity=hashlib.sha256(str(payload.email).lower().encode()).hexdigest()
    attempts=db.scalars(select(Audit).where(Audit.action=='login_failed',Audit.created_at>=now()-timedelta(minutes=15))).all()
    if sum(a.details.get('identity')==identity for a in attempts)>=10: raise HTTPException(429,'Too many attempts; try again in 15 minutes')
    user=db.scalar(select(User).where(User.email==str(payload.email).lower()))
    if not user or not passwords.verify(payload.password,user.password_hash):
        if user: audit(db,user.id,'login_failed',identity=identity); db.commit()
        raise HTTPException(401,'Invalid email or password')
    cookie(response,create_session(db,user)); return {'id':user.id,'email':user.email}
@app.get('/api/auth/me')
def me(user=Depends(current_user)): return {'id':user.id,'email':user.email}
@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    db.execute(delete(Session).where(Session.token==token_hash(request.cookies.get('careerorbit_session','')))); db.commit(); response.delete_cookie('careerorbit_session'); return {'ok':True}
@app.get('/api/profile')
def profile(user=Depends(current_user),db=Depends(get_db)):
    p=db.get(Profile,user.id); return {**p.data,'confirmed':p.confirmed,'email':user.email}
@app.put('/api/profile')
def save_profile(payload:ProfileInput,user=Depends(current_user),db=Depends(get_db)):
    p=db.get(Profile,user.id); p.data=payload.model_dump(exclude={'confirmed'}); p.confirmed=payload.confirmed
    # Profile changes revoke all previous sending scope.
    for c in db.scalars(select(Campaign).where(Campaign.user_id==user.id)):
        c.revision+=1; c.status='paused'
    audit(db,user.id,'profile_updated'); db.commit(); return {**p.data,'confirmed':p.confirmed}
@app.get('/api/resumes')
def resumes(user=Depends(current_user),db=Depends(get_db)):
    return [data(r,('path',)) for r in db.scalars(select(Resume).where(Resume.user_id==user.id))]
@app.post('/api/resumes')
async def upload_resume(file:UploadFile=File(...),name:str=Form(...),user=Depends(current_user),db=Depends(get_db)):
    content=await file.read(settings.max_upload_mb*1024*1024+1)
    if len(content)>settings.max_upload_mb*1024*1024: raise HTTPException(413,'Resume exceeds size limit')
    filename=Path(file.filename or '').name
    if any(ch in filename for ch in '\r\n') or len(name)>150: raise HTTPException(422,'Invalid filename or label')
    suffix=Path(filename).suffix.lower()
    try:
        if suffix=='.pdf' and content.startswith(b'%PDF-'):
            reader=PdfReader(io.BytesIO(content));
            if len(reader.pages)>30: raise ValueError('Too many pages')
            text='\n'.join(p.extract_text() or '' for p in reader.pages); mime='application/pdf'
        elif suffix=='.docx' and content.startswith(b'PK'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if sum(x.file_size for x in z.infolist())>30*1024*1024: raise ValueError('Expanded document too large')
                if any('vbaProject' in x.filename for x in z.infolist()): raise ValueError('Macros forbidden')
            doc=Document(io.BytesIO(content)); text='\n'.join(p.text for p in doc.paragraphs); mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else: raise ValueError('Only PDF and DOCX allowed')
        if len(text.strip())<30: raise ValueError('No usable text; scanned PDFs require OCR outside this app')
        if len(text)>100000: raise ValueError('Resume text too long')
    except Exception as e: raise HTTPException(422,'Cannot parse resume: '+str(e)[:200])
    path=Path(settings.storage_dir)/f'{uid()}.enc'; path.write_bytes(cipher().encrypt(content)); path.chmod(0o600)
    p=db.get(Profile,user.id)
    skills=[s for s in p.data.get('skills',[]) if s.lower() in text.lower()]
    r=Resume(user_id=user.id,name=name,filename=filename,path=str(path),mime=mime,sha256=hashlib.sha256(content).hexdigest(),text=text,skills=skills)
    db.add(r); audit(db,user.id,'resume_uploaded',filename=filename); db.commit()
    return {**data(r,('path',)),'extracted':{'emails':re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text),'matched_skills':skills,'review_required':True}}
@app.post('/api/resumes/{id}/approve')
def approve_resume(id:str,user=Depends(current_user),db=Depends(get_db)):
    r=owned(db,Resume,id,user); r.approved=True; audit(db,user.id,'resume_approved',resume_id=id); db.commit(); return data(r,('path',))
@app.get('/api/resumes/{id}/download')
def download_resume(id:str,user=Depends(current_user),db=Depends(get_db)):
    r=owned(db,Resume,id,user); return Response(resume_bytes(r),media_type=r.mime,headers={'Content-Disposition':f'attachment; filename="resume{Path(r.filename).suffix}"'})
@app.get('/api/campaigns')
def campaigns(user=Depends(current_user),db=Depends(get_db)):
    return [data(c) for c in db.scalars(select(Campaign).where(Campaign.user_id==user.id).order_by(Campaign.created_at.desc()))]
@app.post('/api/campaigns')
def create_campaign(payload:CampaignInput,user=Depends(current_user),db=Depends(get_db)):
    c=Campaign(user_id=user.id,name=payload.name,preferences=payload.preferences.model_dump(mode='json')); db.add(c); db.commit(); return data(c)
@app.put('/api/campaigns/{id}')
def edit_campaign(id:str,payload:CampaignInput,user=Depends(current_user),db=Depends(get_db)):
    c=owned(db,Campaign,id,user); c.name=payload.name;c.preferences=payload.preferences.model_dump(mode='json');c.revision+=1;c.status='paused';audit(db,user.id,'campaign_scope_changed',campaign_id=id);db.commit();return data(c)
@app.post('/api/campaigns/{id}/pause')
def pause(id:str,user=Depends(current_user),db=Depends(get_db)):
    c=owned(db,Campaign,id,user); c.status='paused'; audit(db,user.id,'campaign_paused',campaign_id=id); db.commit();return data(c)
@app.post('/api/campaigns/{id}/resume')
def resume_campaign(id:str,user=Depends(current_user),db=Depends(get_db)):
    c=owned(db,Campaign,id,user)
    if not db.scalar(select(Approval).where(Approval.campaign_id==id,Approval.revision==c.revision)): raise HTTPException(409,'New approval required')
    c.status='active'; audit(db,user.id,'campaign_resumed',campaign_id=id);db.commit();return data(c)

def research_campaign(db,c,user):
    profile=db.get(Profile,user.id)
    sources=c.preferences.get('sources',{}); rows=[]; errors=[]
    jobs=[]
    for source in ('greenhouse','lever'):
        jobs.extend((source,board) for board in sources.get(source,[]))
    if sources.get('adzuna'): jobs.extend(('adzuna',country) for country in sources['adzuna'])
    if sources.get('serpapi'): jobs.append(('serpapi','search'))
    if not jobs: raise HTTPException(422,'Configure Greenhouse/Lever board slugs or a credentialed discovery source first')
    for source,board in jobs[:20]:
        usage(db,user,c,source)
        try:
            if source=='adzuna': found=providers.adzuna(c.preferences['query'],board,', '.join(c.preferences.get('locations',[])[:1]))
            elif source=='serpapi': found=providers.serpapi(c.preferences['query'],', '.join(c.preferences.get('locations',[])[:1]))
            else: found=getattr(providers,source)(board)
            rows.extend(found)
        except providers.ProviderError as e: errors.append({'source':source,'board':board,'error':str(e)})
    added=0
    for row in rows:
        from .compensation import compare_compensation
        conversion=compare_compensation(row.get('data',{}).get('compensation'),c.preferences)
        if conversion: row['data']['compensation_comparison']=conversion
        existing=db.scalar(select(Opportunity).where(Opportunity.campaign_id==c.id,Opportunity.source==row['source'],Opportunity.external_id==row['external_id']))
        if existing:
            # Refresh evidence, rescoring, and source text. Any change invalidates existing approvals.
            score,explanation,eligible=match(row,c.preferences,profile.data)
            if existing.description!=row['description'] or existing.url!=row['url'] or existing.eligible!=eligible:
                c.revision+=1;c.status='paused'
            existing.description=row['description'];existing.url=row['url'];existing.data=row['data'];existing.verified_at=now();existing.eligible=eligible;existing.score=score;existing.explanation=explanation
            continue
        score,explanation,eligible=match(row,c.preferences,profile.data)
        op=Opportunity(campaign_id=c.id,company_key=company_key(row['company']),score=score,explanation=explanation,eligible=eligible,**row);db.add(op);added+=1
    audit(db,user.id,'research_completed',campaign_id=c.id,added=added,errors=errors);db.commit()
    return {'added':added,'sources_checked':len(jobs[:20]),'errors':errors,'note':'Only source-returned records; target counts are not guaranteed.'}
@app.post('/api/campaigns/{id}/research')
def research(id:str,user=Depends(current_user),db=Depends(get_db)): return research_campaign(db,owned(db,Campaign,id,user),user)
@app.get('/api/campaigns/{id}/opportunities')
def opportunities(id:str,q:str='',eligible_only:bool=False,user=Depends(current_user),db=Depends(get_db)):
    owned(db,Campaign,id,user)
    stmt=select(Opportunity).where(Opportunity.campaign_id==id)
    if q: stmt=stmt.where((Opportunity.company.ilike('%'+q+'%')) | (Opportunity.title.ilike('%'+q+'%')))
    if eligible_only: stmt=stmt.where(Opportunity.eligible==True)
    return [data(o) for o in db.scalars(stmt.order_by(Opportunity.score.desc()).limit(2000))]
@app.get('/api/campaigns/{id}/export.csv')
def export_csv(id:str,user=Depends(current_user),db=Depends(get_db)):
    owned(db,Campaign,id,user); buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['Company','Role','Location','Score','Classification','Eligible','Source','URL','Compensation'])
    def safe(v):
        s=str(v); return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
    for o in db.scalars(select(Opportunity).where(Opportunity.campaign_id==id)):
        writer.writerow([safe(v) for v in [o.company,o.title,o.location,o.score,o.classification,o.eligible,o.source,o.url,json.dumps(o.data.get('compensation'))]])
    return Response(buf.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="careerorbit.csv"'})
@app.get('/api/contacts')
def contacts(user=Depends(current_user),db=Depends(get_db)): return [data(x) for x in db.scalars(select(Contact).where(Contact.user_id==user.id))]
@app.post('/api/contacts')
def add_contact(payload:ContactInput,user=Depends(current_user),db=Depends(get_db)):
    op=owned(db,Opportunity,payload.opportunity_id,user)
    email=str(payload.email).lower()
    c=db.scalar(select(Contact).where(Contact.user_id==user.id,Contact.email==email))
    if c and c.company_key!=op.company_key: raise HTTPException(409,'Contact already belongs to another company')
    if not c:
        c=Contact(user_id=user.id,company_key=op.company_key,email=email,source_url=str(payload.source_url),role=payload.role);db.add(c)
    audit(db,user.id,'contact_added',opportunity_id=op.id); db.commit();return data(c)
@app.post('/api/contacts/{id}/verify')
def verify_contact(id:str,user=Depends(current_user),db=Depends(get_db)):
    c=owned(db,Contact,id,user)
    result=providers.hunter_verify(c.email); c.verification='valid' if result['status']=='valid' else result['status'] or 'unverified';c.checked_at=now();db.add(Usage(user_id=user.id,provider='hunter'));db.commit();return {**data(c),'provider_result':result}
@app.get('/api/contact-discovery')
def discover_contacts(domain:str,user=Depends(current_user),db=Depends(get_db)):
    result=providers.hunter_search(domain);db.add(Usage(user_id=user.id,provider='hunter'));db.commit();return result
@app.get('/api/drafts')
def drafts(campaign_id:str,user=Depends(current_user),db=Depends(get_db)):
    owned(db,Campaign,campaign_id,user);return [data(x) for x in db.scalars(select(Draft).where(Draft.campaign_id==campaign_id))]
@app.post('/api/drafts')
def make_draft(payload:DraftInput,user=Depends(current_user),db=Depends(get_db)):
    op=owned(db,Opportunity,payload.opportunity_id,user);contact=owned(db,Contact,payload.contact_id,user);profile=db.get(Profile,user.id)
    if not op.eligible or op.classification not in ('A','B','C'): raise HTTPException(409,'Opportunity is not eligible')
    if contact.company_key!=op.company_key: raise HTTPException(409,'Wrong-company contact')
    if op.data.get('application_method')=='portal': raise HTTPException(409,'This source specifies an ATS portal. Use the official link; no email application will be generated.')
    available=list(db.scalars(select(Resume).where(Resume.user_id==user.id,Resume.approved==True)))
    r=owned(db,Resume,payload.resume_id,user) if payload.resume_id else max(available,key=lambda r:sum(s.lower() in r.text.lower() and s.lower() in (op.title+' '+op.description).lower() for s in profile.data.get('skills',[])),default=None)
    if not r: raise HTTPException(422,'Approve a resume first')
    try: subject,body=write_email(profile.data,op,r)
    except ValueError as e: raise HTTPException(422,str(e))
    d=Draft(campaign_id=op.campaign_id,opportunity_id=op.id,contact_id=contact.id,resume_id=r.id,subject=subject,body=body)
    d.validation=validate_draft(d,op,contact,r,{**profile.data,'confirmed':profile.confirmed});db.add(d)
    try: db.commit()
    except IntegrityError: db.rollback();raise HTTPException(409,'Draft already exists for this opportunity')
    return data(d)
@app.put('/api/drafts/{id}')
def edit_draft(id:str,payload:DraftEdit,user=Depends(current_user),db=Depends(get_db)):
    d=owned(db,Draft,id,user)
    if d.status in ('sent','sending','unknown'): raise HTTPException(409,'Cannot edit dispatched message')
    d.subject=payload.subject;d.body=payload.body;d.status='draft'
    c=db.get(Campaign,d.campaign_id);c.revision+=1;c.status='paused'
    p=db.get(Profile,user.id);d.validation=validate_draft(d,db.get(Opportunity,d.opportunity_id),db.get(Contact,d.contact_id),db.get(Resume,d.resume_id),{**p.data,'confirmed':p.confirmed})
    audit(db,user.id,'draft_edited',draft_id=id);db.commit();return data(d)
@app.post('/api/campaigns/{id}/approve')
def approve_campaign(id:str,payload:ApprovalInput,user=Depends(current_user),db=Depends(get_db)):
    c=owned(db,Campaign,id,user);box=owned(db,Mailbox,payload.mailbox_id,user)
    if c.preferences['mode']=='draft_only': raise HTTPException(409,'Change mode to review before authorizing sends')
    if len(set(payload.draft_ids))!=len(payload.draft_ids): raise HTTPException(422,'Duplicate draft IDs')
    ds=[owned(db,Draft,i,user) for i in payload.draft_ids]
    if any(d.campaign_id!=id for d in ds): raise HTTPException(422,'Wrong campaign draft')
    if len(ds)>min(c.preferences['initial_emails'],c.preferences['target_companies']): raise HTTPException(422,'Approval exceeds campaign target')
    p=db.get(Profile,user.id); companies=set();emails=set()
    for d in ds:
        op=db.get(Opportunity,d.opportunity_id);contact=db.get(Contact,d.contact_id);r=db.get(Resume,d.resume_id)
        issues=validate_draft(d,op,contact,r,{**p.data,'confirmed':p.confirmed})
        if issues: raise HTTPException(422,{'draft_id':d.id,'issues':issues})
        if op.company_key in companies or contact.email in emails: raise HTTPException(409,'Only one recipient per company is allowed')
        companies.add(op.company_key);emails.add(contact.email)
        if db.scalar(select(Message).where(Message.user_id==user.id,(Message.company_key==op.company_key)|(Message.recipient==contact.email))): raise HTTPException(409,'Company or recipient already contacted')
        if db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==contact.email)): raise HTTPException(409,'Recipient suppressed')
    a=Approval(campaign_id=id,revision=c.revision,scope_hash=scope_hash(c,ds),draft_ids=[d.id for d in ds],max_messages=len(ds));db.add(a);db.flush()
    for d in ds:
        job=db.scalar(select(QueueJob).where(QueueJob.draft_id==d.id))
        if job and job.status in ('sending','unknown','sent'): raise HTTPException(409,'Message already dispatched or needs reconciliation')
        if job: job.approval_id=a.id;job.mailbox_id=box.id;job.status='pending';job.next_at=now();job.error=''
        else: db.add(QueueJob(draft_id=d.id,approval_id=a.id,mailbox_id=box.id))
        d.status='approved'
    c.status='active';audit(db,user.id,'campaign_approved',campaign_id=id,approval_id=a.id,recipient_count=len(ds));db.commit();return data(a)
@app.get('/api/queue')
def queue(user=Depends(current_user),db=Depends(get_db)):
    return [data(x) for x in db.scalars(select(QueueJob).join(Draft).join(Campaign).where(Campaign.user_id==user.id))]
@app.get('/api/mailboxes')
def mailboxes(user=Depends(current_user),db=Depends(get_db)): return [data(x,('tokens',)) for x in db.scalars(select(Mailbox).where(Mailbox.user_id==user.id))]
@app.post('/api/oauth/{provider}/connect')
def connect(provider:str,read:bool=False,user=Depends(current_user),db=Depends(get_db)):
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64);url=mail.auth_url(provider,state,verifier,read)
    db.add(OAuthState(state=state,user_id=user.id,provider=provider,read_enabled=read,verifier=verifier,expires_at=now()+timedelta(minutes=10)));db.commit();return {'url':url}
@app.get('/api/oauth/{provider}/callback')
def callback(provider:str,state:str,code:str='',error:str='',request:Request=None,db=Depends(get_db)):
    s=db.get(OAuthState,state)
    session=db.get(Session,token_hash(request.cookies.get('careerorbit_session','')))
    if not s or s.expires_at<now() or s.provider!=provider or not session or session.expires_at<now() or session.user_id!=s.user_id: raise HTTPException(400,'Invalid or expired OAuth state/session')
    user_id=s.user_id;read=s.read_enabled;verifier=s.verifier;db.delete(s);db.commit()
    if error or not code: raise HTTPException(400,'Mailbox connection was declined')
    t=mail.token_request(provider,{'grant_type':'authorization_code','code':code,'code_verifier':verifier});address=mail.identity(provider,t)
    box=db.scalar(select(Mailbox).where(Mailbox.user_id==user_id,Mailbox.provider==provider))
    if box:
        old=json.loads(cipher().decrypt(box.tokens.encode()))
        if not t.get('refresh_token') and old.get('refresh_token'): t['refresh_token']=old['refresh_token']
        box.address=address;box.tokens=cipher().encrypt(json.dumps(t).encode()).decode();box.read_enabled=read
    else: db.add(Mailbox(user_id=user_id,provider=provider,address=address,tokens=cipher().encrypt(json.dumps(t).encode()).decode(),read_enabled=read))
    audit(db,user_id,'mailbox_connected',provider=provider,read_enabled=read);db.commit();return RedirectResponse(settings.app_url+'/?connected='+provider)
@app.delete('/api/mailboxes/{id}')
def disconnect(id:str,user=Depends(current_user),db=Depends(get_db)):
    box=owned(db,Mailbox,id,user);db.delete(box);audit(db,user.id,'mailbox_disconnected');db.commit();return {'ok':True}
@app.post('/api/mailboxes/{id}/sync')
def sync(id:str,user=Depends(current_user),db=Depends(get_db)):
    box=owned(db,Mailbox,id,user);results=mail.list_replies(db,box);count=0
    messages=list(db.scalars(select(Message).where(Message.user_id==user.id)))
    for item in results:
        if db.scalar(select(Reply).where(Reply.mailbox_id==id,Reply.provider_id==item['id'])): continue
        # Match by thread or original Message-ID, not sender alone.
        m=next((m for m in messages if (m.thread_id and m.thread_id==item['thread_id']) or (db.scalar(select(QueueJob.id).where(QueueJob.draft_id==m.draft_id)) or 'impossible')+'@careerorbit.local' in item['in_reply_to']),None)
        category=mail.classify_reply(item['body'])
        if not m and category=='unsubscribe':
            sender=parseaddr(item['from'])[1].lower()
            m=next((candidate for candidate in messages if candidate.recipient==sender),None)
        if not m: continue
        db.add(Reply(user_id=user.id,mailbox_id=id,message_id=m.id,provider_id=item['id'],body=item['body'],category=category));count+=1
        if category not in ('acknowledgment','out_of_office'): m.status='replied'
        if category in ('unsubscribe','bounce') and not db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==m.recipient)):
            db.add(Suppression(user_id=user.id,email=m.recipient,reason=category))
        db.add(Notification(user_id=user.id,text=f'{category.replace("_"," ").title()} from {m.recipient}'))
    db.commit();return {'persisted':count,'scope':'most recent 100 inbox messages; last 30 days for Gmail'}
@app.get('/api/replies')
def replies(user=Depends(current_user),db=Depends(get_db)): return [data(x) for x in db.scalars(select(Reply).where(Reply.user_id==user.id))]
@app.get('/api/follow-ups')
def followups(user=Depends(current_user),db=Depends(get_db)):
    result=[]
    for m in db.scalars(select(Message).where(Message.user_id==user.id,Message.status=='sent')):
        c=db.get(Campaign,m.campaign_id)
        if (now()-m.sent_at).days < c.preferences.get('follow_up_days',8): continue
        if db.scalar(select(FollowUp).where(FollowUp.message_id==m.id)): continue
        if db.scalar(select(Reply).where(Reply.message_id==m.id,Reply.category.not_in(['acknowledgment','out_of_office']))): continue
        if db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==m.recipient)): continue
        d=db.get(Draft,m.draft_id);op=db.get(Opportunity,d.opportunity_id)
        result.append({'message_id':m.id,'recipient':m.recipient,'subject':'Re: '+d.subject,'suggested_body':f'Hello,\n\nI wanted to follow up on my application for {op.title} at {op.company}. If the position is still open, I would appreciate any update on the next steps. Thank you for your time.','status':'review_required','reason':'One follow-up only, with explicit approval; meaningful replies suppress sending'})
    return result
@app.put('/api/applications/{opportunity_id}')
def update_application(opportunity_id:str,payload:ApplicationInput,user=Depends(current_user),db=Depends(get_db)):
    op=owned(db,Opportunity,opportunity_id,user)
    a=db.scalar(select(Application).where(Application.user_id==user.id,Application.opportunity_id==op.id))
    if not a: a=Application(user_id=user.id,opportunity_id=op.id);db.add(a)
    a.status=payload.status;a.notes=payload.notes;a.updated_at=now()
    if payload.interview_at:
        try: a.interview_at=datetime.fromisoformat(payload.interview_at).replace(tzinfo=None)
        except ValueError: raise HTTPException(422,'Invalid interview datetime')
    audit(db,user.id,'application_status_user_reported',opportunity_id=op.id,status=a.status);db.commit();return data(a)
@app.get('/api/applications')
def applications(user=Depends(current_user),db=Depends(get_db)): return [data(x) for x in db.scalars(select(Application).where(Application.user_id==user.id))]
@app.post('/api/campaigns/{id}/schedule')
def schedule(id:str,payload:ScheduleInput,user=Depends(current_user),db=Depends(get_db)):
    owned(db,Campaign,id,user)
    if payload.expires_at<=now().date(): raise HTTPException(422,'Expiry must be in the future')
    s=db.get(ResearchSchedule,id)
    if not s: s=ResearchSchedule(campaign_id=id);db.add(s)
    s.interval_hours=payload.interval_hours;s.expires_at=datetime.combine(payload.expires_at,datetime.min.time());s.enabled=payload.enabled;s.next_at=now()+timedelta(hours=payload.interval_hours);db.commit();return data(s)
@app.get('/api/dashboard')
def dashboard(user=Depends(current_user),db=Depends(get_db)):
    cs=list(db.scalars(select(Campaign).where(Campaign.user_id==user.id)));ids=[c.id for c in cs]
    ops=list(db.scalars(select(Opportunity).where(Opportunity.campaign_id.in_(ids))));ds=list(db.scalars(select(Draft).where(Draft.campaign_id.in_(ids))));ms=list(db.scalars(select(Message).where(Message.user_id==user.id)));rs=list(db.scalars(select(Reply).where(Reply.user_id==user.id)));apps=list(db.scalars(select(Application).where(Application.user_id==user.id)))
    jobs=list(db.scalars(select(QueueJob).join(Draft).where(Draft.campaign_id.in_(ids))))
    return {'target':sum(c.preferences['target_companies'] for c in cs),'researched':len({o.company_key for o in ops}),'verified_eligible':len({o.company_key for o in ops if o.eligible and o.classification in ('A','B')}),'contacts':db.scalar(select(func.count()).select_from(Contact).where(Contact.user_id==user.id)),'drafts':len(ds),'approved':sum(d.status=='approved' for d in ds),'sent':len(ms),'failed':sum(j.status in ('failed','unknown') for j in jobs),'awaiting_reply':sum(m.status=='sent' for m in ms),'replies':len(rs),'positive':sum(r.category in ('positive','interview') for r in rs),'interviews':sum(a.status=='interview' for a in apps),'rejections':sum(a.status=='rejected' for a in apps),'portal_submitted':sum(a.status=='portal_submitted' for a in apps),'queued':sum(j.status=='pending' for j in jobs),'api_calls':db.scalar(select(func.count()).select_from(Usage).where(Usage.user_id==user.id)),'cost':'Provider billing not synchronized; no estimated prices invented','geography':dict((loc,sum(o.location==loc for o in ops)) for loc in {o.location for o in ops}),'types':dict((typ,sum(o.data.get('type')==typ for o in ops)) for typ in {o.data.get('type','unknown') for o in ops})}
@app.get('/api/audit')
def audit_log(user=Depends(current_user),db=Depends(get_db)): return [data(x) for x in db.scalars(select(Audit).where(Audit.user_id==user.id).order_by(Audit.created_at.desc()).limit(200))]
@app.get('/api/notifications')
def notifications(user=Depends(current_user),db=Depends(get_db)): return [data(x) for x in db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(100))]
@app.post('/api/suppressions')
def suppress(payload:dict,user=Depends(current_user),db=Depends(get_db)):
    from pydantic import TypeAdapter, EmailStr
    try: email=str(TypeAdapter(EmailStr).validate_python(payload.get('email'))).lower()
    except Exception: raise HTTPException(422,'Valid email required')
    if not db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==email)): db.add(Suppression(user_id=user.id,email=email,reason='user requested'))
    audit(db,user.id,'recipient_suppressed');db.commit();return {'ok':True}
@app.get('/api/account/export')
def export_account(user=Depends(current_user),db=Depends(get_db)):
    cs=list(db.scalars(select(Campaign).where(Campaign.user_id==user.id)));ids=[c.id for c in cs]
    return {'user':data(user,('password_hash',)),'profile':data(db.get(Profile,user.id)),'campaigns':[data(c) for c in cs],'resumes':[data(r,('path',)) for r in db.scalars(select(Resume).where(Resume.user_id==user.id))],'opportunities':[data(o) for o in db.scalars(select(Opportunity).where(Opportunity.campaign_id.in_(ids)))],'drafts':[data(d) for d in db.scalars(select(Draft).where(Draft.campaign_id.in_(ids)))],'messages':[data(m) for m in db.scalars(select(Message).where(Message.user_id==user.id))],'replies':[data(r) for r in db.scalars(select(Reply).where(Reply.user_id==user.id))],'contacts':[data(r) for r in db.scalars(select(Contact).where(Contact.user_id==user.id))],'applications':[data(r) for r in db.scalars(select(Application).where(Application.user_id==user.id))],'follow_ups':[data(r) for r in db.scalars(select(FollowUp).where(FollowUp.user_id==user.id))],'suppressions':[data(r) for r in db.scalars(select(Suppression).where(Suppression.user_id==user.id))],'notifications':[data(r) for r in db.scalars(select(Notification).where(Notification.user_id==user.id))],'api_usage':[data(r) for r in db.scalars(select(Usage).where(Usage.user_id==user.id))],'mailboxes':[data(r,('tokens',)) for r in db.scalars(select(Mailbox).where(Mailbox.user_id==user.id))],'scheduled_research':[data(r) for r in db.scalars(select(ResearchSchedule).where(ResearchSchedule.campaign_id.in_(ids)))],'audit':[data(r) for r in db.scalars(select(Audit).where(Audit.user_id==user.id))]}
@app.delete('/api/account')
def delete_account(request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    paths=[r.path for r in db.scalars(select(Resume).where(Resume.user_id==user.id))]
    # Delete dependent campaign trees before RESTRICTed resume rows.
    for c in db.scalars(select(Campaign).where(Campaign.user_id==user.id)): db.delete(c)
    db.flush();db.delete(user);db.commit()
    for p in paths: Path(p).unlink(missing_ok=True)
    response.delete_cookie('careerorbit_session');return {'deleted':True,'note':'Provider Sent mail and external backups require separate retention handling'}

@app.post('/api/opportunities/{id}/discover-contact')
def vacancy_contact(id:str,user=Depends(current_user),db=Depends(get_db)):
    op=owned(db,Opportunity,id,user);c=db.get(Campaign,op.campaign_id)
    # Only email addresses literally published in the official source description.
    candidates=sorted(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',op.description)))
    consumer={'gmail.com','yahoo.com','hotmail.com','outlook.com','proton.me','icloud.com','aol.com'}
    candidates=[e.lower().strip('.') for e in candidates if e.split('@')[-1].lower() not in consumer]
    if not candidates: return {'contacts':[],'next_action':'Use the official application portal. No professional email was published in source text.'}
    found=[]
    for email in candidates[:3]:
        usage(db,user,c,'hunter');result=providers.hunter_verify(email)
        ct=db.scalar(select(Contact).where(Contact.user_id==user.id,Contact.email==email))
        if ct and ct.company_key!=op.company_key: continue
        if not ct: ct=Contact(user_id=user.id,company_key=op.company_key,email=email,source_url=op.url,role='Source-listed contact');db.add(ct)
        ct.verification='valid' if result['status']=='valid' else result['status'] or 'unverified';ct.checked_at=now();db.flush();found.append(data(ct))
    audit(db,user.id,'source_contacts_discovered',opportunity_id=id,count=len(found));db.commit();return {'contacts':found,'next_action':'Review the published application instructions and each contact before drafting.'}

@app.get('/api/opportunities/{id}/fit')
def career_fit(id:str,user=Depends(current_user),db=Depends(get_db)):
    op=owned(db,Opportunity,id,user);p=db.get(Profile,user.id)
    score,explanation,eligible=match(data(op),db.get(Campaign,op.campaign_id).preferences,p.data)
    known=['python','javascript','typescript','sql','react','java','c++','excel','tableau','pytorch','tensorflow','docker','kubernetes','aws','statistics','communication','research','leadership']
    missing=[s for s in known if re.search(r'\b'+re.escape(s)+r'\b',op.description,re.I) and not any(s==k.lower() for k in p.data.get('skills',[]))]
    flags=[]
    if re.search(r'pay.*(?:fee|deposit)|upfront payment|registration fee|purchase.*equipment',op.description,re.I): flags.append('Potential upfront-payment language; investigate before applying')
    if not op.url.startswith('https://'): flags.append('Source does not use HTTPS')
    if op.classification=='E': flags.append('Unverified lead; outreach disabled')
    return {'score':score,'explanation':explanation,'eligible':eligible,'skills_to_review':missing,'note':'Keyword gaps are suggestions, not a definitive eligibility assessment. No claim is made that a company is authentic.','authenticity_flags':flags}

@app.post('/api/messages/{id}/follow-up')
def approve_follow_up(id:str,payload:FollowUpApproval,user=Depends(current_user),db=Depends(get_db)):
    m=owned(db,Message,id,user);box=owned(db,Mailbox,payload.mailbox_id,user);c=db.get(Campaign,m.campaign_id)
    if m.status!='sent': raise HTTPException(409,'Meaningful reply already received')
    if c.status!='active' or c.preferences['mode']=='draft_only': raise HTTPException(409,'Campaign is not authorized to send')
    if db.scalar(select(FollowUp).where(FollowUp.message_id==id)): raise HTTPException(409,'Maximum one follow-up; already queued or attempted')
    if db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==m.recipient)): raise HTTPException(409,'Recipient suppressed')
    if db.scalar(select(Reply).where(Reply.message_id==id,Reply.category.not_in(['acknowledgment','out_of_office']))): raise HTTPException(409,'Reply suppresses follow-up')
    original_box=db.scalar(select(QueueJob.mailbox_id).where(QueueJob.draft_id==m.draft_id))
    if original_box!=box.id: raise HTTPException(422,'Use the original sending mailbox')
    original=db.get(Draft,m.draft_id)
    f=FollowUp(user_id=user.id,message_id=id,mailbox_id=box.id,campaign_revision=c.revision,subject='Re: '+original.subject,body=payload.body,next_at=max(now(),m.sent_at+timedelta(days=c.preferences.get('follow_up_days',8))))
    db.add(f);audit(db,user.id,'follow_up_authorized',message_id=id);db.commit();return data(f)

@app.get('/api/follow-up-queue')
def follow_up_queue(user=Depends(current_user),db=Depends(get_db)):
    return [data(f) for f in db.scalars(select(FollowUp).where(FollowUp.user_id==user.id))]

@app.post('/api/campaigns/parse')
def parse_campaign_input(payload:dict,user=Depends(current_user)):
    from .campaign_parser import parse_campaign
    text=payload.get('text','')
    if not isinstance(text,str) or not 10<=len(text)<=4000: raise HTTPException(422,'Describe the campaign in 10–4000 characters')
    return parse_campaign(text)
