"""Single dispatch worker. PostgreSQL row locks also serialize multiple workers per user.
Never retry an uncertain send; operator reconciliation is required.
"""
import time
from datetime import timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from .db import SessionLocal, now, Base, engine
from .models import *
from .outreach import scope_hash, validate_draft, resume_bytes
from . import mail, providers

def tick(db):
    job=db.scalar(select(QueueJob).where(QueueJob.status=='pending',QueueJob.next_at<=now()).order_by(QueueJob.next_at).with_for_update(skip_locked=True).limit(1))
    if not job: return False
    d=db.get(Draft,job.draft_id);c=db.get(Campaign,d.campaign_id)
    # Serialize total/daily quotas and cross-campaign duplicates for one account.
    user=db.scalar(select(User).where(User.id==c.user_id).with_for_update())
    if c.status!='active': job.next_at=now()+timedelta(minutes=1);db.commit();return True
    a=db.get(Approval,job.approval_id);box=db.get(Mailbox,job.mailbox_id)
    ds=[db.get(Draft,i) for i in a.draft_ids] if a else []
    def fail(reason,status='failed'):
        job.status=status;job.error=reason;d.status=status
        db.add(Audit(user_id=user.id,action='dispatch_'+status,details={'draft_id':d.id,'reason':reason}));db.commit()
    if not a or d.id not in a.draft_ids or a.revision!=c.revision or any(x is None for x in ds) or scope_hash(c,ds)!=a.scope_hash:
        fail('Approval scope changed');return True
    if not box or box.user_id!=c.user_id: fail('Mailbox unavailable');return True
    if c.preferences['mode']=='draft_only': fail('Draft-only mode');return True
    local=now().replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(c.preferences['timezone']))
    p=c.preferences
    if p.get('end_date') and local.date().isoformat()>p['end_date']: fail('Campaign ended');return True
    if (p.get('start_date') and local.date().isoformat()<p['start_date']) or not p['send_start_hour']<=local.hour<p['send_end_hour']:
        job.next_at=now()+timedelta(minutes=15);db.commit();return True
    op=db.get(Opportunity,d.opportunity_id);contact=db.get(Contact,d.contact_id);r=db.get(Resume,d.resume_id);profile=db.get(Profile,user.id)
    issues=validate_draft(d,op,contact,r,{**profile.data,'confirmed':profile.confirmed})
    if issues: fail('; '.join(issues));return True
    if op.verified_at<now()-timedelta(hours=24): fail('Vacancy evidence older than 24h; re-research and reapprove');return True
    if contact.checked_at<now()-timedelta(days=7): fail('Contact verification expired; reverify');return True
    if op.data.get('application_method')=='portal': fail('Portal application required');return True
    if op.data.get('deadline') and op.data['deadline']<local.date().isoformat(): fail('Application deadline passed');return True
    if db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==contact.email)): fail('Recipient suppressed');return True
    if db.scalar(select(Message).where(Message.user_id==user.id,(Message.company_key==op.company_key)|(Message.recipient==contact.email))): fail('Recipient or company already contacted');return True
    # Unknown and in-flight sends reserve company + recipient across campaigns.
    other_jobs=db.execute(select(QueueJob,Draft,Opportunity,Contact).join(Draft,QueueJob.draft_id==Draft.id).join(Campaign,Draft.campaign_id==Campaign.id).join(Opportunity,Draft.opportunity_id==Opportunity.id).join(Contact,Draft.contact_id==Contact.id).where(Campaign.user_id==user.id,QueueJob.id!=job.id,QueueJob.status.in_(['sending','unknown','sent']))).all()
    if any(o.company_key==op.company_key or co.email==contact.email for _,_,o,co in other_jobs): fail('Recipient/company already reserved by another dispatch');return True
    midnight=local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    sent=db.scalar(select(func.count()).select_from(Message).where(Message.campaign_id==c.id))
    today=db.scalar(select(func.count()).select_from(Message).where(Message.user_id==user.id,Message.sent_at>=midnight))
    # Unknown requests may have been accepted. Count them against limits.
    uncertain=db.scalar(select(func.count()).select_from(QueueJob).join(Draft).where(Draft.campaign_id==c.id,QueueJob.status.in_(['sending','unknown'])))
    if sent+uncertain>=min(p['initial_emails'],p['target_companies']): fail('Total quota reached');return True
    global_uncertain=db.scalar(select(func.count()).select_from(QueueJob).join(Draft).join(Campaign).where(Campaign.user_id==user.id,QueueJob.status.in_(['sending','unknown'])))
    follow_count=db.scalar(select(func.count()).select_from(FollowUp).where(FollowUp.user_id==user.id,((FollowUp.status=='sent') & (FollowUp.sent_at>=midnight)) | FollowUp.status.in_(['sending','unknown'])))
    if today+global_uncertain+follow_count>=p['daily_limit']:
        job.next_at=now()+timedelta(hours=1);db.commit();return True
    # Refresh before marking sending; refresh cannot dispatch a message.
    try: mail.access_token(db,box);content=resume_bytes(r)
    except Exception: fail('Mailbox authentication or resume decryption failed; reconnect/check attachment');return True
    # Durable marker precedes external side effect. Crash here leaves status sending,
    # never selected again automatically. Reconcile with provider Sent folder.
    job.status='sending';job.attempts+=1;d.status='sending';db.commit()
    try:
        provider_id,thread_id=mail.send(db,box,d,contact,r,content,job.id)
    except mail.SendError as e:
        if e.transient and job.attempts<4:
            job.status='pending';d.status='approved';job.next_at=now()+timedelta(seconds=max(e.retry_after,60*2**job.attempts));job.error=str(e);db.commit()
        else: fail(str(e),'unknown' if e.uncertain else 'failed')
        return True
    except Exception:
        fail('Unexpected dispatch interruption; inspect provider Sent mail before retrying','unknown');return True
    db.add(Message(user_id=user.id,campaign_id=c.id,draft_id=d.id,company_key=op.company_key,recipient=contact.email,provider_id=provider_id,thread_id=thread_id))
    job.status='sent';job.error='';d.status='sent';db.add(Audit(user_id=user.id,action='provider_accepted',details={'draft_id':d.id,'provider_id':provider_id}));db.commit();return True

def research_tick(db):
    from .main import research_campaign
    s=db.scalar(select(ResearchSchedule).where(ResearchSchedule.enabled==True,ResearchSchedule.next_at<=now()).with_for_update(skip_locked=True).limit(1))
    if not s: return
    c=db.get(Campaign,s.campaign_id)
    if s.expires_at<=now(): s.enabled=False;db.commit();return
    if c.status=='paused': s.next_at=now()+timedelta(hours=s.interval_hours);db.commit();return
    s.next_at=now()+timedelta(hours=s.interval_hours);db.commit()
    try: research_campaign(db,c,db.get(User,c.user_id));s.last_error='';db.commit()
    except Exception as e:
        db.rollback();s=db.get(ResearchSchedule,c.id);s.last_error='Research failed; check source configuration and API budget';db.commit()

def main():
    from .config import validate_runtime
    validate_runtime()
    Base.metadata.create_all(engine)
    print('CareerOrbit durable worker running',flush=True)
    while True:
        try:
            with SessionLocal() as db: tick(db)
            with SessionLocal() as db: follow_up_tick(db)
            with SessionLocal() as db: research_tick(db)
        except Exception as e:
            print('Worker transaction failed:',type(e).__name__,flush=True)
        time.sleep(5)



def follow_up_tick(db):
    f=db.scalar(select(FollowUp).where(FollowUp.status=='pending',FollowUp.next_at<=now()).order_by(FollowUp.next_at).with_for_update(skip_locked=True).limit(1))
    if not f: return False
    user=db.scalar(select(User).where(User.id==f.user_id).with_for_update())
    m=db.get(Message,f.message_id);c=db.get(Campaign,m.campaign_id);d=db.get(Draft,m.draft_id)
    def stop(reason,status='cancelled'):
        f.status=status;f.error=reason;db.add(Audit(user_id=user.id,action='follow_up_'+status,details={'id':f.id,'reason':reason}));db.commit()
    if c.status=='paused': f.next_at=now()+timedelta(minutes=15);db.commit();return True
    if c.status!='active' or c.revision!=f.campaign_revision or c.preferences['mode']=='draft_only': stop('Campaign scope changed');return True
    if m.status!='sent' or db.scalar(select(Reply).where(Reply.message_id==m.id,Reply.category.not_in(['acknowledgment','out_of_office']))): stop('Meaningful reply received');return True
    if db.scalar(select(Suppression).where(Suppression.user_id==user.id,Suppression.email==m.recipient)): stop('Recipient suppressed');return True
    box=db.get(Mailbox,f.mailbox_id);r=db.get(Resume,d.resume_id);ct=db.get(Contact,d.contact_id);op=db.get(Opportunity,d.opportunity_id)
    if not op.eligible or op.classification in ('D','E') or (op.data.get('deadline') and op.data['deadline']<now().date().isoformat()): stop('Opportunity is no longer eligible or active');return True
    if not box or not r.approved or ct.verification!='valid': stop('Mailbox, attachment or contact is no longer approved');return True
    local=now().replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(c.preferences['timezone']))
    if c.preferences.get('end_date') and local.date().isoformat()>c.preferences['end_date']: stop('Campaign ended');return True
    if not c.preferences['send_start_hour']<=local.hour<c.preferences['send_end_hour']: f.next_at=now()+timedelta(minutes=15);db.commit();return True
    midnight=local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    initial_count=db.scalar(select(func.count()).select_from(Message).where(Message.user_id==user.id,Message.sent_at>=midnight))
    follow_count=db.scalar(select(func.count()).select_from(FollowUp).where(FollowUp.user_id==user.id,((FollowUp.status=='sent') & (FollowUp.sent_at>=midnight)) | FollowUp.status.in_(['sending','unknown'])))
    uncertain=db.scalar(select(func.count()).select_from(QueueJob).join(Draft).join(Campaign).where(Campaign.user_id==user.id,QueueJob.status.in_(['sending','unknown'])))
    if initial_count+follow_count+uncertain>=c.preferences['daily_limit']: f.next_at=now()+timedelta(hours=1);db.commit();return True
    try: mail.access_token(db,box);content=resume_bytes(r)
    except Exception: stop('Authentication or attachment unavailable','failed');return True
    f.status='sending';f.attempts+=1;db.commit()
    from types import SimpleNamespace
    original_job=db.scalar(select(QueueJob).where(QueueJob.draft_id==d.id))
    try:
        provider_id,_=mail.send(db,box,SimpleNamespace(subject=f.subject,body=f.body),ct,r,content,f.id,thread_id=m.thread_id,reply_message_id=original_job.id if original_job else '')
    except mail.SendError as e:
        if e.transient and f.attempts<4:
            f.status='pending';f.next_at=now()+timedelta(seconds=max(e.retry_after,60*2**f.attempts));f.error=str(e);db.commit()
        else: stop(str(e),'unknown' if e.uncertain else 'failed')
        return True
    except Exception: stop('Acceptance unknown; reconcile provider Sent mail','unknown');return True
    f.status='sent';f.provider_id=provider_id;f.sent_at=now();f.error='';db.add(Audit(user_id=user.id,action='follow_up_provider_accepted',details={'id':f.id}));db.commit();return True

if __name__=='__main__': main()
