"""Bounded, server-side DeepSeek copy generation; no customer birth data is sent."""
import os,json,asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from daily_card_generator import DailyCardGenerator

FIELDS=('headline','message','love','style','affirmation')
SCHEMA={'type':'object','properties':{k:{'type':'string'} for k in FIELDS},'required':list(FIELDS),'additionalProperties':False}
AI_LOCK=asyncio.Lock()

async def generate(day,revision,ledger,client=None):
    key=os.environ.get('DEEPSEEK_API_KEY','').strip()
    if not key:raise ValueError('尚未配置 DeepSeek API 密钥，请由管理员在 Render 后台填写 DEEPSEEK_API_KEY。')
    g=DailyCardGenerator();draft=g.draft(day,revision)
    async with AI_LOCK:
        today=datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        state=json.loads(ledger.read_text()) if ledger.exists() else {}
        if state.get('date')!=today:state={'date':today,'calls':0,'recent':[]}
        limit=max(0,min(100,int(os.environ.get('DAILY_AI_CALL_LIMIT','20'))))
        if state['calls']>=limit:raise ValueError('今日 AI 试用次数已用完。仍可使用文案库或手动编辑。')
        state['calls']+=1
        ledger.write_text(json.dumps(state),encoding='utf8')
        prompt={k:draft[k] for k in ('date','theme','lucky_color')}
        prompt['variation']=revision
        prompt['avoid_recent']=state['recent'][-7:]
        body={'model':'deepseek-flash','thinking':{'type':'disabled'},'max_tokens':600,
              'messages':[{'role':'system','content':'Write natural American English daily spiritual reflection for adult women. General wellness, not personal astrology. Mature, warm, concrete and varied; avoid clichés. No names, logos, diagnoses, fear, manipulation, guarantees, predictions of reconciliation or wealth. Return headline 1-10 words; message 15-30 words; love 8-18 words; style 6-15 words including the EXACT supplied lucky_color name; affirmation 1-16 words. Match weekday theme. Suggest everyday American outfits. Avoid repeating recent messages. Use common correctly spelled English words. Return only JSON with five string keys. Example JSON: {"headline":"A quiet pause", "message":"Take a few quiet minutes to notice what feels steady today, and let that guide your next small step.", "love":"Ask a thoughtful question and leave room for an honest answer.", "style":"Wear a Soft Lavender sweater with cream jeans and simple flats.", "affirmation":"I can pause before choosing my next step."}'},{'role':'user','content':json.dumps(prompt)}],
              'response_format':{'type':'json_object'}}
        owned=client is None
        client=client or httpx.AsyncClient(timeout=45)
        try:
            response=await client.post('https://api.deepseek.com/chat/completions',headers={'Authorization':'Bearer '+key},json=body)
            if response.status_code!=200:raise ValueError('DeepSeek 调用失败，请检查密钥、余额及模型权限。没有自动重试扣费。')
            data=response.json()
            choice=data['choices'][0]
            if choice.get('finish_reason')!='stop':raise ValueError('AI 未完成生成，请保留原文或稍后再试。')
            text=choice['message']['content']
            copy=json.loads(text)
            if not isinstance(copy,dict) or set(copy)!=set(FIELDS) or not all(isinstance(v,str) for v in copy.values()):raise ValueError('AI 返回格式不完整。')
            draft.update(copy);g.validate(draft)
            for value in copy.values():
                if any(x in value.lower() for x in ('guaranteed','will return to you','destined to','buy now','evelyn brooks')):raise ValueError('AI 文案未通过内容检查，请手动编辑或重新生成。')
            if draft['message'] in state['recent']:raise ValueError('AI 文案与近期重复，请重新生成。')
            state['recent']=(state['recent']+[draft['message']])[-21:]
            ledger.write_text(json.dumps(state),encoding='utf8')
            draft['source']='DeepSeek deepseek-flash'
            return {'draft':draft,'remaining':max(0,limit-state['calls'])}
        except (httpx.HTTPError,json.JSONDecodeError,KeyError,TypeError,IndexError):
            raise ValueError('AI 连接或输出异常，原文保持不变。请稍后重试。') from None
        finally:
            if owned:await client.aclose()

