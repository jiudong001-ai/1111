"""Editorial daily reflection, deliberately independent of astrology calculations."""
import json,re,os,hashlib,shutil
from datetime import date,timedelta
from pathlib import Path
from html import escape
from playwright.async_api import async_playwright
from spellchecker import SpellChecker

ROOT=Path(__file__).parent
SPELLING=SpellChecker(language='en')
SPELLING.word_frequency.load_words(['overshirt','openhearted','loafers','cardigan','plum'])
class DailyCardGenerator:
    def __init__(self):
        self.config=json.loads((ROOT/'daily_themes.json').read_text(encoding='utf8'))
        self.template=(ROOT/'daily_card_template.html').read_text(encoding='utf8')
        self.spelling=SPELLING
    def draft(self,day=None,revision=0):
        day=date.fromisoformat(day) if isinstance(day,str) else day or date.today()
        t=self.config['days'][day.weekday()];v=(day.toordinal()//7+revision)%3
        headlines=['A little room for clarity','Care that goes both ways','Honor your capacity','Speak kindly to yourself','Choose one steady step','A moment that is yours','Listen, then stay curious']
        return dict(date=day.isoformat(),weekday=t['weekday'],theme=t['theme'],main=t['main'],background=t['background'],art=t['art'],headline=headlines[day.weekday()],message=t['messages'][v],love=t['love'][v],lucky_color=t['lucky_color'],lucky_number=1+(int(hashlib.sha256((day.isoformat()+str(revision)).encode()).hexdigest()[:6],16)%9),style=t['style'],affirmation=t['affirmations'][v],revision=revision)
    def validate(self,d):
        limits={'message':(15,30),'love':(8,18),'style':(6,15),'affirmation':(1,16),'headline':(1,10)}
        for key,(low,high) in limits.items():
            value=d.get(key,'');count=len(value.split())
            if not low<=count<=high:raise ValueError(f'{key}: use {low}–{high} words (received {count})')
            if len(value)>400 or re.search(r'[\u3400-\u9fff]',value):raise ValueError('Client cards require short English text')
            words=re.findall(r"[a-z]+(?:'[a-z]+)?",value.lower().replace('’',"'"))
            unknown=sorted(self.spelling.unknown(words))
            if unknown:raise ValueError('Check English spelling: '+', '.join(unknown))
        if not 1<=int(d['lucky_number'])<=9:raise ValueError('Choose a playful number from 1 to 9')
        if len(d['lucky_color'])>40:raise ValueError('Color name is too long')
        if d['lucky_color'].lower() not in d['style'].lower():raise ValueError('Style advice must include the lucky color name')
        return d
    def html(self,d,story=False,asset_source=None):
        self.validate(d)
        # Theme/palette/illustration come exclusively from the trusted weekday config.
        t=self.config['days'][date.fromisoformat(d['date']).weekday()]
        values={'FORMAT':'story' if story else '', 'MAIN':t['main'],'BACKGROUND':t['background'],'THEME':t['theme'],'DATE':date.fromisoformat(d['date']).strftime('%A · %B %d, %Y'),'HEADLINE':d['headline'],'MESSAGE':d['message'],'LOVE':d['love'],'COLOR':d['lucky_color'],'NUMBER':str(d['lucky_number']),'STYLE':d['style'],'AFFIRMATION':d['affirmation']}
        html=self.template
        for key,value in values.items():html=html.replace('{{'+key+'}}',escape(str(value)))
        return html.replace('{{ART}}',escape(asset_source or self.illustration(t),quote=True))
    def illustration(self,t):
        # Generated photographic assets are local; all visible lettering remains HTML.
        return '/daily-assets/'+t['weekday'].lower()+'.png'
    async def export(self,drafts,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);checks=[]
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(args=['--disable-dev-shm-usage','--disable-gpu'],**({'headless':True} if os.environ.get('BROWSER_ENGINE')=='bundled' else {'channel':'chrome','headless':True}))
            try:
                for d in drafts:
                    asset=date.fromisoformat(d['date']).strftime('%A').lower()+'.png'
                    shutil.copyfile(ROOT/'daily_assets'/asset,folder/asset)
                    context=await browser.new_context(viewport={'width':1080,'height':1920},device_scale_factor=1)
                    page=await context.new_page()
                    for story in (False,True):
                        stem=d['date']+('-story' if story else '-feed');html=self.html(d,story,asset)
                        path=folder/(stem+'.html');path.write_text(html,encoding='utf8')
                        await page.goto(path.resolve().as_uri());await page.evaluate('document.fonts.ready')
                        await page.evaluate('''async () => {await document.querySelector('.backdrop').decode()}''')
                        issues=await page.evaluate('''() => {const card=document.querySelector('.card'),c=card.getBoundingClientRect();return [...document.querySelectorAll('.section,.section p,header,.theme,.foot')].filter(e=>{const r=e.getBoundingClientRect();return e.scrollHeight>e.clientHeight+1||e.scrollWidth>e.clientWidth+1||r.bottom>c.bottom-25||r.right>c.right-15}).map(e=>e.className||e.tagName)}''')
                        if issues:raise ValueError('Layout overflow: '+', '.join(issues))
                        await page.locator('.card').screenshot(path=str(folder/(stem+'.png')))
                        checks.append({'file':stem+'.png','width':1080,'height':1920 if story else 1350,'overflow':False})
                    await context.close()
                (folder/'drafts.json').write_text(json.dumps(drafts,indent=2,ensure_ascii=False),encoding='utf8')
                (folder/'layout-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
            finally:await browser.close()
        return checks
