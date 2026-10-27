"""Conservative, local natural-language extraction. Always returns an editable draft."""
import re
from .schemas import Preferences
CITIES={'India':['Bangalore','Bengaluru','Hyderabad','Pune','Delhi','Mumbai'],'Germany':['Berlin','Munich'],'United Kingdom':['London','Manchester'],'United States':['New York','Boston','San Francisco'],'Canada':['Toronto','Vancouver'],'Singapore':['Singapore'],'Netherlands':['Amsterdam','Rotterdam'],'Australia':['Sydney','Melbourne'],'UAE':['Dubai','Abu Dhabi'],'Japan':['Tokyo','Osaka']}
def parse_campaign(text):
    t=text.lower();values={};warnings=['Draft only: review all extracted values. This parser never grants sending authorization.']
    roles=[word for word in ['python','data science','software engineering','machine learning','research','marketing','finance','sustainability','operations','product management','business','data analytics','java','javascript'] if re.search(r'\b'+re.escape(word)+r'\b',t)]
    values['query']=' '.join(roles) if roles else text.strip()[:200]
    values['locations']=[city for cities in CITIES.values() for city in cities if re.search(r'\b'+re.escape(city.lower())+r'\b',t)]
    values['countries']=[country for country in CITIES if country.lower() in t]
    kinds=[]
    if 'intern' in t:kinds.append('internship')
    for phrase,typ in [('research internship','research_internship'),('summer internship','summer_internship'),('winter internship','winter_internship'),('full-time','full_time'),('part-time','part_time'),('research assistant','research_assistant'),('fellowship','fellowship'),('apprenticeship','apprenticeship'),('graduate trainee','graduate_trainee'),('contract role','contract')]:
        if phrase in t:kinds.append(typ)
    values['types']=kinds or ['full_time' if 'job' in t else 'internship']
    target=re.search(r'(?:find|research|contact|target)\s+(\d+)\s+(?:unique\s+)?compan',t)
    if target:values['target_companies']=min(1000,max(1,int(target[1])));values['initial_emails']=values['target_companies']
    daily=re.search(r'(\d+)\s+(?:unique\s+)?(?:approved\s+)?(?:companies|emails|messages)(?:\s+per\s+day|\s+daily)',t)
    if daily:values['daily_limit']=min(50,max(1,int(daily[1])))
    salary=re.search(r'(₹|\$|€|£|inr|usd|eur|gbp|sgd)\s*([\d,]+)(?:\s*(?:per|a|/)\s*(hour|month|year|annum))?',t)
    if salary:
        values['currency']={'₹':'INR','$':'USD','€':'EUR','£':'GBP'}.get(salary[1],salary[1].upper());values['minimum']=float(salary[2].replace(',',''))
        if salary[3]:values['frequency']='year' if salary[3]=='annum' else salary[3]
        else:warnings.append('No salary period found; confirm the default monthly period.')
    if 'paid' in t and 'unpaid' not in t:values['paid_only']=True
    if 'fully remote' in t or 'remote only' in t:values['remote']='remote'
    if not roles:warnings.append('Role extraction was uncertain; original text retained as the query.')
    if not values['locations'] and not values['countries']:warnings.append('No recognized location; add locations manually.')
    return {'name':(' '.join(roles).title() or 'Career search')+' campaign','preferences':Preferences(**values).model_dump(mode='json'),'warnings':warnings}
