import hashlib, json, re
from pathlib import Path
from .security import cipher

def scope_hash(campaign,drafts):
    snapshot={'revision':campaign.revision,'preferences':campaign.preferences,'messages':sorted([{'id':d.id,'subject':d.subject,'body':d.body,'contact':d.contact_id,'resume':d.resume_id} for d in drafts],key=lambda d:d['id'])}
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()

def resume_bytes(resume):
    path=Path(resume.path)
    if not path.is_file(): raise ValueError('Resume attachment missing')
    data=cipher().decrypt(path.read_bytes())
    if hashlib.sha256(data).hexdigest()!=resume.sha256: raise ValueError('Resume integrity check failed')
    return data

def write_email(profile,op,resume):
    name=profile.get('full_name','')
    matched=[s for s in profile.get('skills',[]) if s.lower() in op.description.lower()+' '+op.title.lower() and s.lower() in resume.text.lower()]
    if not name or not matched: raise ValueError('Confirmed name and at least one resume-backed matching skill are required')
    # Grounded extractive writing is the default. No LLM-generated qualifications.
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n',op.description) if 35<len(s.strip())<260]
    if not sentences: raise ValueError('Opportunity needs a usable source excerpt for personalization')
    excerpt=next((s for s in sentences if any(k.lower() in s.lower() for k in matched)),sentences[0])
    from .llm import select_evidence
    selected=select_evidence(sentences,matched,op.title)
    if selected:
        excerpt=sentences[selected.sentence_index]
        matched=[matched[i] for i in dict.fromkeys(selected.skill_indexes)]
    subject=f'Application: {op.title} — {name}'
    body=f'Hello recruiting team,\n\nI’m {name}, and I’m applying for the {op.title} position at {op.company}. The listing notes: “{excerpt}”\n\nMy resume includes {", ".join(matched[:4])}, which connects with those requirements. I’d like to understand how that background could support the work described in your listing. I’ve attached my {resume.name} resume so you can review my experience and projects directly.\n\nWould you be the right person to discuss this opportunity, or should I apply through your careers portal? Thank you for considering my application.\n\nBest,\n{name}\n\nIf this inquiry is not relevant, reply “stop” and I won’t contact you again.'
    return subject,body

def validate_draft(draft,op,contact,resume,profile):
    issues=[]
    if op.classification not in ('A','B','C'): issues.append('Opportunity is closed or unverified')
    if not op.eligible: issues.append('Opportunity is ineligible')
    if contact.verification!='valid': issues.append('Contact email not verified')
    if contact.company_key!=op.company_key: issues.append('Contact belongs to another company')
    if not resume.approved: issues.append('Resume has not been approved')
    if not profile.get('confirmed'): issues.append('Profile has not been confirmed')
    if not draft.subject.strip(): issues.append('Subject missing')
    if op.company.lower() not in draft.body.lower() or op.title.lower() not in draft.body.lower(): issues.append('Company or position missing')
    if re.search(r'\{\{|\}\}|\[insert|\[company|\[name|<placeholder|ignore previous|system prompt',draft.body,re.I): issues.append('Placeholder or instruction injection detected')
    if not 60<=len(draft.body.split())<=220: issues.append('Email must be 60–220 words')
    try: resume_bytes(resume)
    except Exception: issues.append('Attachment unavailable or integrity failure')
    return issues
