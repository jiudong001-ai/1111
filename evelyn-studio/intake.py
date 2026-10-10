"""Conservative evidence-preserving intake. No persistence or inferred birth times."""
import re
from datetime import datetime

MONTHS = 'January February March April May June July August September October November December'.split()
DATE = r'(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}|(?:' + '|'.join(m[:3] + r'(?:' + m[3:] + ')?' for m in MONTHS) + r')\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}\s+(?:' + '|'.join(MONTHS) + r')\s+\d{4})'

def date_value(raw):
    clean = re.sub(r'(\d)(st|nd|rd|th)', r'\1', raw, flags=re.I).replace(',', '')
    if re.fullmatch(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', clean):
        a,b,y = map(int,re.split('[/-]',clean))
        if a <= 12 and b <= 12 and a != b:
            return None, 'ambiguous'
        clean = f'{y}-{b if a > 12 else a}-{a if a > 12 else b}'
    for fmt in ('%Y-%m-%d','%B %d %Y','%b %d %Y','%d %B %Y'):
        try:
            d=datetime.strptime(clean,fmt).date()
            if d > datetime.now().date(): return None,'invalid'
            return d.isoformat(),'extracted'
        except ValueError: pass
    return None,'invalid'

def parse(text, previous=None):
    people = previous or {p:{} for p in ('client','partner')}
    issues=[]
    def add(p,k,v,e,status='extracted'):
        old=people[p].get(k)
        if old and old.get('confirmed') and e in old.get('evidence',[]):
            return  # Re-pasted evidence cannot undo an operator correction.
        if old and old['value'] != v:
            people[p][k]={'value':None,'status':'conflict','evidence':old['evidence']+[e], 'candidates':[old['value'],v]}
        else: people[p][k]={**(old or {}),'value':v,'status':old['status'] if old and old.get('confirmed') else status,'evidence':list(dict.fromkeys((old or {}).get('evidence',[])+[e]))}
    person='client'
    for clause in re.split(r'(?<=[.!?\n])\s*|\s+and\s+|;',text):
        if not clause.strip(): continue
        if re.search(r'\b(he|his|him|she|her|partner|boyfriend|girlfriend|husband|wife|ex)\b',clause,re.I): person='partner'
        elif re.search(r'\b(I|my|mine|me)\b',clause,re.I): person='client'
        both=bool(re.search(r'\b(?:both|we\s+(?:were|was|are)\s+born|our\s+birthplace)\b',clause,re.I))
        targets=['client','partner'] if both else [person]
        for match in re.finditer(DATE,clause,re.I):
            v,s=date_value(match.group())
            for p in targets: add(p,'birth_date',v,clause,s)
        unknown=bool(re.search(r"(?:don't|do not|doesn't|does not) know.*(?:time)|(?:time.*unknown)|(?:unknown.*time)",clause,re.I))
        if unknown and re.search(r'\b(?:the|our)\s+(?:birth\s+)?times\b',clause,re.I):
            targets=['client','partner']
        tm=re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b|\b(\d{1,2}):(\d{2})\b',clause,re.I)
        if unknown:
            for p in targets: add(p,'birth_time',None,clause,'unknown')
        elif tm:
            if tm[1]:
                h=int(tm[1]); mi=int(tm[2] or 0); ap=tm[3].lower()[0]
                valid=1<=h<=12 and mi<60; h=h%12+(12 if ap=='p' else 0)
            else: h=int(tm[4]);mi=int(tm[5]);valid=h<24 and mi<60
            s='approximate' if re.search(r'about|around|roughly|approximately',clause,re.I) else 'extracted'
            for p in targets: add(p,'birth_time',f'{h:02}:{mi:02}' if valid else None,clause,s if valid else 'invalid')
        loc=re.search(r'\b(?:born\s+(?:in|at)|birthplace\s*(?:is|:))\s+(.+)',clause,re.I)
        if not loc and re.search(r'\bborn\b',clause,re.I):
            loc=re.search(r'\bin\s+([A-Za-z][A-Za-z ,\-]+)',clause)
        if loc:
            value=re.split(r'\s+at\s+\d|\s+on\s+|[.!?]',loc[1])[0].strip(' ,')
            for p in targets: add(p,'place',value,clause,'needs_confirmation')
        if re.search(r'\b(they|their)\b',clause,re.I) and re.search(DATE,clause,re.I):
            for p in targets:
                if 'birth_date' in people[p]:
                    f=people[p]['birth_date']
                    if not f.get('confirmed'):
                        f['status']='ambiguous_person'
                        f['confirmed']=False
    for p,fields in people.items():
        for k,f in fields.items():
            if f['status'] in ('conflict','ambiguous','invalid','ambiguous_person','needs_confirmation'):
                issues.append({'person':p,'field':k,'status':f['status']})
    relation=next((x for x in ('ex','husband','wife','boyfriend','girlfriend','partner') if re.search(r'\b'+x+r'\b',text,re.I)), 'unspecified')
    questions=[s.strip() for s in re.split(r'(?<=[?])|\n',text) if '?' in s]
    return {'people':people,'issues':issues,'relationship_type':relation,'question': ' '.join(questions)[:1200], 'notice':'Extracted facts require human review; unresolved fields are withheld.'}
