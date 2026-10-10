import json, secrets, re, shutil, asyncio, os
from pathlib import Path
from datetime import date
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright
from intake import parse,city_search_name
from engine import calculate
from reading import reading,card
import httpx

ROOT=Path(__file__).parent
EXPORTS=Path(os.environ.get('EXPORT_DIR',str(ROOT/'exports')));EXPORTS.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='Evelyn Brooks Astrology Studio')
app.mount('/exports',StaticFiles(directory=EXPORTS),name='exports')
LOCK=asyncio.Lock()
class Intake(BaseModel):text:str=Field(max_length=20000)
class Birth(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    birth_date:date
    birth_time:str|None=None
    time_accuracy:str='unknown'
    place:str=Field(min_length=2,max_length=200)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    timezone:str
    fold:int|None=Field(default=None,ge=0,le=1)
class Calc(BaseModel):people:list[Birth]=Field(min_length=1,max_length=2)
@app.middleware('http')
async def same_origin(request:Request,call_next):
    allowed={'127.0.0.1:8877','localhost:8877','testserver'}
    allowed.update(filter(None,os.environ.get('ALLOWED_HOSTS','').split(',')))
    render_host=os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if render_host:allowed.add(render_host)
    host=request.headers.get('host','')
    if host not in allowed:
        return JSONResponse({'detail':'Invalid host'},status_code=403)
    origin=request.headers.get('origin')
    if request.method=='POST' and origin and origin not in {'http://'+host,'https://'+host}:
        return JSONResponse({'detail':'Invalid origin'},status_code=403)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response
@app.get('/health')
def health():return {'status':'ok'}
@app.get('/source')
def source():
    archive=ROOT/'source.zip'
    if not archive.exists():raise HTTPException(503,'Source archive is not built')
    return FileResponse(archive,filename='Evelyn-Corresponding-Source.zip',media_type='application/zip')
@app.get('/',response_class=HTMLResponse)
def home():return (ROOT/'index.html').read_text(encoding='utf-8')
@app.post('/api/parse')
def intake(body:Intake):
    result=parse(body.text)
    for role,person in result['people'].items():
        pattern=r"(?i:my name is|I'm|I am)\s+([A-Z][a-z]+)" if role=='client' else r'(?i:boyfriend|girlfriend|husband|wife|partner)(?:\s+is named|\s+named|,)?\s+([A-Z][a-z]+)'
        match=re.search(pattern,body.text)
        person['name']={'value':match[1] if match else role.title(),'status':'extracted' if match else 'role_label','evidence':[match[0]] if match else []}
    return result
@app.get('/api/places')
async def places(q:str):
    if not 2<=len(q)<=120:raise HTTPException(422,'Enter a city')
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r=await client.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':city_search_name(q),'count':10,'language':'en','format':'json'});r.raise_for_status()
            return [{'place':', '.join(str(v) for v in [x['name'],x.get('admin1'),x.get('country')] if v),'latitude':x['latitude'],'longitude':x['longitude'],'timezone':x['timezone']} for x in r.json().get('results',[]) if x.get('timezone')]
        except Exception:raise HTTPException(503,'City lookup failed. Use verified coordinates and timezone in Advanced settings.')

async def rasterize(path,output,is_svg=False):
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(**({'headless':True} if os.environ.get('BROWSER_ENGINE')=='bundled' else {'channel':'chrome','headless':True}))
        page=await browser.new_page(viewport={'width':1200 if is_svg else 1080,'height':1400},device_scale_factor=2)
        if is_svg:
            svg=path.read_text(encoding='utf8');await page.set_content('<style>body{margin:0;background:white}svg{display:block;width:1200px;height:auto}</style>'+svg)
            target=page.locator('svg')
        else:
            await page.set_content(path.read_text(encoding='utf8'));target=page.locator('.card')
        await page.evaluate('document.fonts.ready');await target.screenshot(path=str(output));await browser.close()

@app.post('/api/calculate')
async def run(body:Calc):
    people=[p.model_dump(mode='json') for p in body.people]
    for p in people:
        if p['birth_date']>date.today().isoformat():raise HTTPException(422,'Birth date is in the future')
        if p['time_accuracy'] not in ('exact','unknown','approximate'):raise HTTPException(422,'Choose time accuracy')
        try:ZoneInfo(p['timezone'])
        except Exception:raise HTTPException(422,'Invalid IANA timezone')
        if p['time_accuracy']=='exact' and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',p['birth_time'] or ''):raise HTTPException(422,'Exact time requires HH:MM')
    async with LOCK:
        try:r,svgs=await asyncio.to_thread(calculate,people)
        except Exception as e:raise HTTPException(422,str(e))
        token=secrets.token_hex(12);folder=EXPORTS/token;folder.mkdir()
        sections=reading(r);r['interpretation']={'language':'en-US','method':'deterministic chart-grounded symbolic draft','sections':sections}
        (folder/'report.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf8')
        html='<!doctype html><meta charset="utf-8"><style>body{max-width:850px;margin:60px auto;padding:20px;background:#fcf8ef;color:#3e173b;font:19px/1.7 Georgia}h1{font-weight:400}</style><h1>Evelyn Brooks · Detailed Reading</h1>'
        from html import escape
        html+=''.join('<h2>'+escape(s['title'])+'</h2><p>'+escape(s['text'])+'</p>' for s in sections)
        (folder/'reading.html').write_text(html,encoding='utf8')
        try:
            for name,svg in svgs.items():
                path=folder/(name+'.svg');path.write_text(svg,encoding='utf8');await rasterize(path,folder/(name+'.png'),True)
            await generate_cards(folder,sections)
        except Exception as e:raise HTTPException(500,'Calculation saved, but export failed: '+str(e))
        shutil.make_archive(str(EXPORTS/token),'zip',folder)
        return {'id':token,'warnings':r['warnings'],'sections':sections,'files':[f'/exports/{token}/{p.name}' for p in folder.iterdir()],'bundle':f'/exports/{token}.zip'}
async def generate_cards(folder,sections):
    from datetime import datetime
    day=datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    for kind in ('love','daily'):
        path=folder/(kind+'-card.html');path.write_text(card(kind,sections,day),encoding='utf8');await rasterize(path,folder/(kind+'-card.png'))
@app.post('/api/daily')
async def daily():
    async with LOCK:
        token=secrets.token_hex(12);folder=EXPORTS/token;folder.mkdir()
        from datetime import datetime
        path=folder/'daily-card.html';path.write_text(card('daily',[],datetime.now(ZoneInfo('America/New_York')).date().isoformat()),encoding='utf8');await rasterize(path,folder/'daily-card.png')
        return {'files':[f'/exports/{token}/daily-card.png']}
