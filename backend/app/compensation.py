from datetime import date
from functools import lru_cache
import re
from .providers import fetch_json,ProviderError

@lru_cache(maxsize=256)
def daily_rate(source,target,day):
    if not all(re.fullmatch('[A-Z]{3}',x) for x in (source,target)):return None
    try:
        d=fetch_json('https://api.frankfurter.dev/v1/latest',{'base':source,'symbols':target})
        rate=float(d['rates'][target])
        if rate<=0:return None
        return {'rate':rate,'date':d['date'],'source':'https://api.frankfurter.dev/v1/latest','from':source,'to':target}
    except (ProviderError,KeyError,ValueError,TypeError):return None

def compare_compensation(compensation,prefs):
    """Preserve original units. Never turn a monthly stipend into an annual salary."""
    if not compensation or compensation.get('frequency')!=prefs['frequency']:return None
    if compensation.get('currency')==prefs['currency']:return None
    rate=daily_rate(compensation.get('currency',''),prefs['currency'],date.today().isoformat())
    if not rate:return None
    return {'min':compensation['min']*rate['rate'],'currency':prefs['currency'],'frequency':compensation['frequency'],'fx':rate}
