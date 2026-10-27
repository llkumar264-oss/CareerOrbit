"""No network, no email, no database writes. Exactly 100 labeled synthetic records."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.matching import match,company_key
from app.schemas import Preferences
p=Preferences(query='Python data',locations=['Bangalore'],types=['internship'],minimum=25000).model_dump(mode='json')
profile={'full_name':'Synthetic Applicant','skills':['Python','SQL'],'interests':['data']}
records=[]
for i in range(100):
    op={'source':'synthetic','company':f'SYNTHETIC Company {i:03}','title':'Python data internship','description':'Work on Python and SQL data pipelines in a supervised internship. This is a synthetic fixture, not a real vacancy.','location':'Bangalore' if i%5 else 'Berlin','url':f'https://example.invalid/synthetic/{i}','classification':'A','data':{'type':'internship','synthetic':True}}
    score,explanation,eligible=match(op,p,profile)
    records.append({**op,'company_key':company_key(op['company']),'score':score,'eligible':eligible,'explanation':explanation})
print(json.dumps({'mode':'SYNTHETIC DRY RUN — NO EMAIL SENT','records':len(records),'eligible':sum(r['eligible'] for r in records),'unique_companies':len({r['company_key'] for r in records}),'opportunities':records},indent=2))
