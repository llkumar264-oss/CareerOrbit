import re
from datetime import date

def company_key(name): return re.sub(r'[^a-z0-9]', '', name.casefold())
def tokens(text): return set(re.findall(r'[a-z0-9+#.]+', text.lower()))
def match(op, prefs, profile):
    text = (op['title']+' '+op['description']).lower()
    skills = [s for s in profile.get('skills',[]) if s.lower() in text]
    query = tokens(prefs['query'])
    role = len(query & tokens(text))/max(len(query),1)
    location = op.get('location','').lower()
    locations = prefs.get('locations',[]) or prefs.get('countries',[])
    geo = not locations or any(l.lower() in location for l in locations) or ('remote' in location and prefs.get('remote') in ('remote','any'))
    data = op.get('data',{})
    reasons = []
    if not geo: reasons.append('Outside selected locations')
    if prefs.get('remote') != 'any' and prefs['remote'] not in location+' '+text: reasons.append('Work arrangement not verified as requested')
    if company_key(op['company']) in [company_key(c) for c in prefs.get('blacklist',[])]: reasons.append('Blacklisted company')
    if data.get('deadline') and data['deadline'] < date.today().isoformat(): reasons.append('Deadline passed')
    if op.get('classification') in ('D','E'): reasons.append('Closed or unverified opportunity')
    if op.get('classification') == 'C' and not prefs.get('allow_speculative'): reasons.append('Speculative outreach not authorized')
    typ = data.get('type','unknown')
    selected = prefs.get('types',[])
    internship_types = {'internship','research_internship','summer_internship','winter_internship','remote_internship','paid_internship'}
    # A broad internship result is not proof of seasonal, paid or research specialization.
    if typ != 'unknown' and typ not in selected:
        if not (typ in internship_types and 'internship' in selected): reasons.append('Opportunity category does not match')
    if typ == 'unknown': reasons.append('Opportunity category not verified')
    compensation = data.get('compensation')
    comp = 0.5
    if not compensation:
        if not prefs.get('allow_undisclosed',True): reasons.append('Compensation undisclosed')
    else:
        if prefs.get('paid_only') and compensation.get('min',0) <= 0: reasons.append('Paid compensation not verified')
        comparable=data.get('compensation_comparison') or compensation
        if comparable.get('currency') == prefs['currency'] and comparable.get('frequency') == prefs['frequency']:
            comp = float(comparable.get('min',0) >= prefs.get('minimum',0))
            if not comp: reasons.append('Below minimum compensation')
        else:
            comp = 0.5 # No guessed currency or frequency conversion.
    eligibility = data.get('eligibility',{})
    if eligibility.get('requires_citizenship') and eligibility['requires_citizenship'] not in profile.get('work_authorization',[]): reasons.append('Required citizenship not established')
    if eligibility.get('sponsorship') is False and profile.get('requires_sponsorship'): reasons.append('Sponsorship unavailable')
    components = {'skills': min(1,len(skills)/max(1,len(profile.get('skills',[])))), 'role':min(1,role), 'eligibility':1 if eligibility else .5,'geography':float(geo),'compensation':comp,'interests':float(any(s.lower() in text for s in profile.get('interests',[]))), 'evidence':1 if op.get('source') in ('greenhouse','lever') else .7}
    score = round(sum(components[k]*v for k,v in prefs['weights'].items()))
    return score, {'components':components,'matched_skills':skills,'exclusions':reasons,'eligibility':'verified fields only' if eligibility else 'not verified', 'compensation':'published' if compensation else 'undisclosed', 'currency_comparison':data.get('compensation_comparison') or 'No verified same-period FX comparison'}, not reasons
