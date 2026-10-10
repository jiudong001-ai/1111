import os
from pathlib import Path
os.environ['KERYKEION_BACKEND']='libephemeris'
os.environ['LIBEPHEMERIS_DATA_DIR']=str(Path(__file__).parent/'ephemeris-data')
import json, math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from importlib.metadata import version
from kerykeion import AstrologicalSubjectFactory as Subject, ChartDataFactory as Data, CompositeSubjectFactory, ChartDrawer

POINTS=['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto']
ASPECTS=[{'name':n,'orb':o} for n,o in [('conjunction',6),('opposition',6),('trine',6),('square',5),('sextile',4)]]
OPTIONS=dict(active_aspects=ASPECTS,point_orb_adjustment_strategy='none')

def utc_instant(p):
    t=datetime.fromisoformat(p['birth_date']+'T'+p['birth_time'])
    z=ZoneInfo(p['timezone'])
    valid=[]
    for fold in (0,1):
        local=t.replace(tzinfo=z,fold=fold)
        if local.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)==t:
            valid.append(local)
    if not valid: raise ValueError('This local time does not exist during a daylight-saving transition. Correct it from records.')
    if len({v.utcoffset() for v in valid})>1 and p.get('fold') is None:
        raise ValueError('This local time occurs twice. Select first or second occurrence under Advanced settings.')
    return t.replace(tzinfo=z,fold=p.get('fold') or 0).astimezone(timezone.utc)

def make_subject(p,instant=None):
    instant=instant or utc_instant(p)
    nation={'UK':'GB','USA':'US','United States':'US','United Kingdom':'GB'}.get(p['place'].split(',')[-1].strip(),'Unspecified')
    return Subject.from_iso_utc_time(name=p.get('name','Client'),iso_utc_time=instant.isoformat(),city=p['place'],nation=nation,lng=p['longitude'],lat=p['latitude'],tz_str=p['timezone'],online=False,active_points=POINTS,calculate_lunar_phase=False)

def uncertain(p):
    # Sample UTC across the complete local civil day. No sample is a birth placement.
    z=ZoneInfo(p['timezone']); start=datetime.fromisoformat(p['birth_date']).replace(tzinfo=z).astimezone(timezone.utc)
    end=(datetime.fromisoformat(p['birth_date'])+timedelta(days=1)).replace(tzinfo=z).astimezone(timezone.utc)
    samples=[]; t=start
    while t<end:
        samples.append(make_subject(p,t));t+=timedelta(minutes=30)
    samples.append(make_subject(p,end-timedelta(seconds=1)))
    result={}
    for n in POINTS:
        values=[getattr(s,n.lower()).abs_pos for s in samples];base=values[0]
        unwrapped=[base+((v-base+180)%360-180) for v in values]
        result[n]={'sampled_longitude_min':min(unwrapped),'sampled_longitude_max':max(unwrapped),'possible_signs':sorted(set(getattr(s,n.lower()).sign for s in samples)),'exact_birth_degree':None,'house':None}
    return {'name':p['name'],'time_accuracy':p['time_accuracy'],'planet_daily_ranges':result,'ascendant':None,'houses':None,'aspects':[],'warning':'30-minute samples across the local birth day; ranges are not guaranteed bounds. No exact birth degrees, angles, houses or aspects are claimed.'}

def calculate(people):
    charts={}; subjects=[];natal=[];warnings=[]
    for i,p in enumerate(people):
        if p['time_accuracy']!='exact':
            natal.append(uncertain(p));subjects.append(None);warnings.append(f"{p['name']}: unknown or approximate time; full chart withheld.");continue
        if abs(p['latitude'])>=66:raise ValueError('Polar Placidus houses require an explicit house-system decision; this prototype withholds automatic substitution.')
        s=make_subject(p); subjects.append(s); d=Data.create_natal_chart_data(s,**OPTIONS)
        natal.append(d.model_dump(mode='json'));charts[f'natal-{i+1}']=d
    report={'schema':'evelyn-kerykeion-1','provenance':{'kerykeion':version('kerykeion'),'libephemeris':version('libephemeris'),'backend':'libephemeris','zodiac':'Tropical','perspective':'Apparent Geocentric','houses':'Placidus','major_aspects':ASPECTS,'orb_bonus':'none'},'birth_inputs':people,'natal':natal,'warnings':warnings}
    if len(subjects)==2 and all(subjects):
        syn=Data.create_synastry_chart_data(*subjects,include_relationship_score=False,include_house_comparison=True,**OPTIONS)
        comp=CompositeSubjectFactory(*subjects,chart_name='Relationship Midpoint Composite').get_midpoint_composite_subject_model()
        cd=Data.create_composite_chart_data(comp,**OPTIONS)
        report.update(synastry=syn.model_dump(mode='json'),composite=cd.model_dump(mode='json'));charts.update(synastry=syn,composite=cd)
    elif len(subjects)==2:report['warnings'].append('Synastry and midpoint composite withheld until both birth times are exact.')
    return report,{name:ChartDrawer(d,theme='classic').generate_svg_string() for name,d in charts.items()}
