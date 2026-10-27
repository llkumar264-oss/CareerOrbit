import base64, hashlib, json, secrets, time
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode
import httpx
from .config import settings
from .security import cipher
from .providers import ProviderError, client

ENDPOINTS = {
 'gmail': ('https://accounts.google.com/o/oauth2/v2/auth','https://oauth2.googleapis.com/token'),
 'outlook': ('https://login.microsoftonline.com/common/oauth2/v2.0/authorize','https://login.microsoftonline.com/common/oauth2/v2.0/token')}
def oauth_config(provider, read=False):
    if provider not in ENDPOINTS: raise ProviderError('Unsupported mailbox provider')
    cid=getattr(settings,f'{provider}_client_id'); secret=getattr(settings,f'{provider}_client_secret')
    if not cid or not secret: raise ProviderError(f'{provider.title()} OAuth credentials not configured')
    if provider=='gmail': scope='openid email https://www.googleapis.com/auth/gmail.send'+(' https://www.googleapis.com/auth/gmail.readonly' if read else '')
    else: scope='openid email offline_access User.Read Mail.Send'+(' Mail.Read' if read else '')
    return cid,secret,scope,f'{settings.api_url}/api/oauth/{provider}/callback'
def auth_url(provider,state,verifier,read):
    cid,_,scope,redirect=oauth_config(provider,read)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return ENDPOINTS[provider][0]+'?'+urlencode(dict(client_id=cid,redirect_uri=redirect,response_type='code',scope=scope,state=state,code_challenge=challenge,code_challenge_method='S256',access_type='offline',prompt='consent'))
def token_request(provider,data):
    cid,secret,_,redirect=oauth_config(provider)
    try:
        with client() as c: r=c.post(ENDPOINTS[provider][1],data={**data,'client_id':cid,'client_secret':secret,'redirect_uri':redirect})
        if r.status_code!=200: raise ProviderError(f'OAuth token exchange failed (HTTP {r.status_code})')
        t=r.json()
        if not t.get('access_token'): raise ProviderError('Provider omitted access token')
        t['expires_at']=time.time()+t.get('expires_in',3600)-90
        return t
    except (httpx.HTTPError,ValueError) as e: raise ProviderError('OAuth provider unavailable') from e

def access_token(db,mailbox):
    t=json.loads(cipher().decrypt(mailbox.tokens.encode()))
    if t.get('expires_at',0)<time.time():
        if not t.get('refresh_token'): raise ProviderError('Reconnect mailbox: refresh permission missing')
        new=token_request(mailbox.provider,{'grant_type':'refresh_token','refresh_token':t['refresh_token']})
        t={**t,**new}
        mailbox.tokens=cipher().encrypt(json.dumps(t).encode()).decode(); db.flush()
    return t['access_token']
def identity(provider,t):
    url='https://www.googleapis.com/oauth2/v2/userinfo' if provider=='gmail' else 'https://graph.microsoft.com/v1.0/me'
    with client() as c: r=c.get(url,headers={'Authorization':'Bearer '+t['access_token']})
    if r.status_code!=200: raise ProviderError('Could not verify mailbox identity')
    d=r.json(); address=d.get('email') or d.get('mail') or d.get('userPrincipalName')
    if not address: raise ProviderError('Provider did not return a mailbox address')
    return address

def build_mime(sender,recipient,subject,body,filename,mime,content,message_id):
    if any('\r' in s or '\n' in s for s in (sender,recipient,subject,filename)): raise ValueError('Invalid header')
    m=EmailMessage(); m['From']=sender; m['To']=recipient; m['Subject']=subject; m['Message-ID']=f'<{message_id}@careerorbit.local>'
    m.set_content(body)
    main,sub=mime.split('/',1)
    m.add_attachment(content,maintype=main,subtype=sub,filename=filename)
    if not any(p.get_payload(decode=True)==content for p in m.iter_attachments()): raise ValueError('Attachment encoding failed')
    return m
class SendError(Exception):
    def __init__(self,message,transient=False,uncertain=False,retry_after=0):
        super().__init__(message); self.transient=transient; self.uncertain=uncertain; self.retry_after=retry_after

def send(db,mailbox,draft,contact,resume,content,job_id,thread_id='',reply_message_id=''):
    token=access_token(db,mailbox)
    headers={'Authorization':'Bearer '+token}
    mime=build_mime(mailbox.address,contact.email,draft.subject,draft.body,resume.filename,resume.mime,content,job_id)
    if reply_message_id:
        mime['In-Reply-To']=f'<{reply_message_id}@careerorbit.local>';mime['References']=f'<{reply_message_id}@careerorbit.local>'
    if mailbox.provider=='gmail':
        url='https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        payload={'raw':base64.urlsafe_b64encode(mime.as_bytes()).decode()}
        if thread_id: payload['threadId']=thread_id
    else:
        url='https://graph.microsoft.com/v1.0/me/sendMail'
        payload={'message':{'subject':draft.subject,'body':{'contentType':'Text','content':draft.body},'toRecipients':[{'emailAddress':{'address':contact.email}}], 'internetMessageHeaders':[{'name':'x-careerorbit-id','value':job_id}], 'attachments':[{'@odata.type':'#microsoft.graph.fileAttachment','name':resume.filename,'contentType':resume.mime,'contentBytes':base64.b64encode(content).decode()}]},'saveToSentItems':True}
    try:
        with client() as c: r=c.post(url,headers=headers,json=payload)
    except httpx.HTTPError as e: raise SendError('Network interruption; acceptance unknown. Check Sent mail before resolving.',uncertain=True) from e
    if r.status_code==429:
        try: delay=min(86400,max(60,int(r.headers.get('Retry-After','60'))))
        except ValueError: delay=300
        raise SendError('Provider rate limit',transient=True,retry_after=delay)
    if r.status_code>=500: raise SendError(f'Provider HTTP {r.status_code}; acceptance unknown',uncertain=True)
    if r.status_code not in (200,202): raise SendError(f'Provider rejected request (HTTP {r.status_code})')
    if mailbox.provider=='gmail':
        data=r.json(); return data.get('id',job_id), data.get('threadId','')
    # Graph sendMail returns 202 without a message ID. Preserve correlation ID honestly.
    return 'accepted:'+job_id,''

def list_replies(db,mailbox):
    if not mailbox.read_enabled: raise ProviderError('Separate mailbox read consent required')
    token=access_token(db,mailbox); headers={'Authorization':'Bearer '+token}
    results=[]
    with client() as c:
        if mailbox.provider=='gmail':
            r=c.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',params={'q':'in:inbox newer_than:30d','maxResults':100},headers=headers)
            if r.status_code!=200: raise ProviderError(f'Reply sync failed (HTTP {r.status_code})')
            for item in r.json().get('messages',[]):
                d=c.get('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+item['id'],params={'format':'full'},headers=headers)
                if d.status_code!=200: continue
                data=d.json(); hs={h['name'].lower():h['value'] for h in data.get('payload',{}).get('headers',[])}
                results.append({'id':item['id'],'thread_id':data.get('threadId',''),'from':hs.get('from',''),'body':data.get('snippet',''),'in_reply_to':hs.get('in-reply-to','')})
        else:
            r=c.get('https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages',params={'$top':100,'$select':'id,conversationId,from,bodyPreview,internetMessageHeaders','$orderby':'receivedDateTime desc'},headers=headers)
            if r.status_code!=200: raise ProviderError(f'Reply sync failed (HTTP {r.status_code})')
            for d in r.json().get('value',[]):
                hs={h['name'].lower():h['value'] for h in d.get('internetMessageHeaders',[])}
                results.append({'id':d['id'],'thread_id':d.get('conversationId',''),'from':d.get('from',{}).get('emailAddress',{}).get('address',''),'body':d.get('bodyPreview',''),'in_reply_to':hs.get('in-reply-to','')})
    return results

def classify_reply(body):
    text=body.lower()
    for category,phrases in [('unsubscribe',['unsubscribe','stop contacting','remove me','do not contact']),('bounce',['undeliverable','delivery failed','address not found']),('out_of_office',['out of office','automatic reply']),('rejection',['not moving forward','unsuccessful','not selected']),('no_openings',['no openings','not hiring']),('interview',['interview','schedule a call']),('request_details',['send your resume','more information','additional details']),('acknowledgment',['received your application','thank you for applying']),('positive',['interested in your','discuss the role'])]:
        if any(p in text for p in phrases): return category
    return 'unclassified'
