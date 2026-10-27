"""API-only discovery. External descriptions are untrusted data, never instructions."""
import re
import httpx
from .config import settings

class ProviderError(Exception): pass

def client(): return httpx.Client(timeout=settings.http_timeout, follow_redirects=False)
def fetch_json(url, params=None, headers=None):
    try:
        with client() as c: r = c.get(url,params=params,headers=headers)
        if r.status_code >= 400: raise ProviderError(f'Provider returned HTTP {r.status_code}')
        return r.json()
    except httpx.ProxyError as e: raise ProviderError('Network proxy denied the provider domain; add it in environment settings') from e
    except (httpx.HTTPError,ValueError) as e: raise ProviderError('Provider unavailable or returned invalid JSON') from e

def clean(s): return re.sub('<[^>]+>',' ',s or '')[:50000]
def classify(title, text=''):
    t=title.lower()
    for word,typ in [('research intern','research_internship'),('summer intern','summer_internship'),('winter intern','winter_internship'),('intern','internship'),('apprentice','apprenticeship'),('research assistant','research_assistant'),('fellow','fellowship'),('graduate trainee','graduate_trainee'),('part-time','part_time'),('contract','contract')]:
        if word in t: return typ
    return 'full_time' if title else 'unknown'
def slug(s):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',s): raise ProviderError('Board identifier must be a slug, not a URL')
    return s

def greenhouse(board):
    data=fetch_json(f'https://boards-api.greenhouse.io/v1/boards/{slug(board)}/jobs', {'content':'true'})
    return [dict(source='greenhouse',external_id=str(j['id']),company=board,title=j['title'],description=clean(j.get('content')),url=j['absolute_url'],location=j.get('location',{}).get('name',''),classification='A',data={'type':classify(j['title']),'board':board,'application_method':application_method(clean(j.get('content')))}) for j in data.get('jobs',[])]
def lever(board):
    data=fetch_json(f'https://api.lever.co/v0/postings/{slug(board)}', {'mode':'json'})
    return [dict(source='lever',external_id=j['id'],company=board,title=j['text'],description=clean(j.get('descriptionPlain') or j.get('description'))+' '+clean(' '.join(x.get('content','') for x in j.get('lists',[]))),url=j['hostedUrl'],location=j.get('categories',{}).get('location',''),classification='A',data={'type':classify(j['text']),'board':board,'application_method':application_method(clean(j.get('descriptionPlain') or j.get('description')))}) for j in data]
def adzuna(query,country,location):
    if not settings.adzuna_app_id or not settings.adzuna_app_key: raise ProviderError('Adzuna credentials are not configured')
    if not re.fullmatch('[a-z]{2}',country): raise ProviderError('Adzuna country must be a two-letter code')
    data=fetch_json(f'https://api.adzuna.com/v1/api/jobs/{country}/search/1',{'app_id':settings.adzuna_app_id,'app_key':settings.adzuna_app_key,'what':query,'where':location,'results_per_page':50})
    result=[]
    for j in data.get('results',[]):
        d={'type':classify(j['title']),'application_method':'portal'}
        # Adzuna salaries are annual; currency depends on market. Keep frequency explicit.
        currencies={'gb':'GBP','us':'USD','in':'INR','de':'EUR','ca':'CAD','au':'AUD','sg':'SGD'}
        if j.get('salary_min') and str(j.get('salary_is_predicted','0'))=='0' and country in currencies:
            d['compensation']={'min':j['salary_min'],'max':j.get('salary_max'),'currency':currencies[country],'frequency':'year'}
        result.append(dict(source='adzuna',external_id=j['id'],company=j['company']['display_name'],title=j['title'],description=clean(j['description']),url=j['redirect_url'],location=j['location']['display_name'],classification='A',data=d))
    return result

def serpapi(query,location):
    if not settings.serpapi_api_key: raise ProviderError('SerpApi credentials are not configured')
    data=fetch_json('https://serpapi.com/search.json',{'engine':'google_jobs','q':query,'location':location,'api_key':settings.serpapi_api_key})
    result=[]
    for j in data.get('jobs_results',[]):
        links=j.get('apply_options',[])
        if not links: continue
        result.append(dict(source='serpapi',external_id=j['job_id'],company=j['company_name'],title=j['title'],description=clean(j.get('description')),url=links[0]['link'],location=j.get('location',''),classification='E',data={'type':classify(j['title']),'application_method':'portal','note':'Search lead; active vacancy not independently verified'}))
    return result

def hunter_verify(email):
    if not settings.hunter_api_key: raise ProviderError('Hunter API key not configured')
    d=fetch_json('https://api.hunter.io/v2/email-verifier',{'email':email,'api_key':settings.hunter_api_key})['data']
    return {'status':d.get('status'),'score':d.get('score'), 'result':d.get('result')}
def hunter_search(domain):
    if not settings.hunter_api_key: raise ProviderError('Hunter API key not configured')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',domain): raise ProviderError('Invalid domain')
    return fetch_json('https://api.hunter.io/v2/domain-search',{'domain':domain,'department':'hr','api_key':settings.hunter_api_key})['data']


def application_method(description):
    # Do not infer permission from an incidental address. Require an application instruction.
    if re.search(r'(?:apply|application|resume|cv)[^.\n]{0,150}(?:email|send)[^.\n]{0,150}[\w.+-]+@[\w.-]+\.[a-z]{2,}',description,re.I): return 'email'
    return 'portal'
