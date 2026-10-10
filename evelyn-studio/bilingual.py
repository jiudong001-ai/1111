"""Paired translations of the deterministic reading templates; no chart inference."""
import re
from html import escape
PLANETS={'Sun':'太阳','Moon':'月亮','Mercury':'水星','Venus':'金星','Mars':'火星','Saturn':'土星','Jupiter':'木星','Uranus':'天王星','Neptune':'海王星','Pluto':'冥王星'}
SIGNS=dict(zip('Ari Tau Gem Can Leo Vir Lib Sco Sag Cap Aqu Pis'.split(),'白羊座 金牛座 双子座 巨蟹座 狮子座 处女座 天秤座 天蝎座 射手座 摩羯座 水瓶座 双鱼座'.split()))
ROLES_ZH=['自我认同和希望践行的价值观','情绪安全感和接受关爱的方式','沟通及理解分歧的方式','表达爱意、吸引力和愿意投入的事物','欲望、主动性和应对挫折的方式','承诺、边界和认真承担的责任']
SIGN_ZH=['直接表达和独立行动的空间','稳定、身体舒适感和从容的节奏','好奇心、交流和灵活性','归属感、温柔和情感的延续','温暖、认可和真诚表达','细致关心、实际支持和明确期待','相互体谅、公平和对话','深度、隐私和逐渐建立的信任','诚实、探索和成长空间','可靠性、长期努力和实际承诺','友谊、独立性和不同观点的空间','同理心、想象力和对氛围的敏感']
HOUSE_ZH=['自我表达','价值观和物质安全','日常沟通','家庭和归属感','浪漫和创造性乐趣','日常照顾和习惯','伴侣间的约定','亲密、脆弱感和共同资源','信念和成长','对外责任','友谊和未来愿望','隐私和内在反思']
ASPECT_ZH={'conjunction':'合相','trine':'三分相','sextile':'六分相','square':'四分相','opposition':'对分相'}
MEANING_ZH=['主题紧密交织；需要说明亲近何时有帮助、何时需要空间','这些需要可能容易协调；把这种顺畅转化为可见的关心','合作可能通过有意识的小步努力逐渐形成','不同需要可能产生摩擦；在冲突升级前约定修复方式','相反的需要邀请双方寻求平衡；避免把一种视角当成唯一正确的视角']

def translate(text):
    from reading import ROLES,SIGNS as themes,HOUSE
    rules=[
      ('30-minute samples across the local birth day; ranges are not guaranteed bounds. No exact birth degrees, angles, houses or aspects are claimed.','按出生地当地全天每30分钟采样；范围不保证覆盖所有极值。不提供精确出生度数、轴点、宫位或相位。'),
      ('A grounded next step','立足现实的下一步'),('House overlays','宫位叠加'),
      ('The JSON retains both directions of the calculated house comparison. Pay particular attention to 5th-house romance, 7th-house agreements and 8th-house trust. An overlay suggests a topic to discuss; it cannot prove mutual attraction or consent.','JSON保留了双向宫位比较结果。可关注第五宫的浪漫、第七宫的约定和第八宫的信任。宫位叠加提示可讨论的主题，不能证明相互吸引或同意。'),
      ('Ask each other: What makes you feel cared for, how do you want to repair tension, and what commitment can you realistically sustain? Look for reciprocity in consistent actions. Astrology is a symbolic reflection practice; it cannot confirm private feelings or guarantee a relationship outcome.','可以互相询问：怎样才会感到被关爱？希望如何修复紧张？能够实际维持什么承诺？从持续行动中观察是否相互回应。占星是象征性的反思实践，不能确认私人感情或保证关系结局。'),
      (' — birth time uncertainty',' — 出生时间不确定'),(' · natal',' · 本命相位'),('Between you','双方比较'),('Relationship midpoint composite','关系中点组合盘'),
      ('The day samples include ','当天采样包含'),('. A precise birth placement is withheld; treat this as a limited reflection, not an individualized conclusion.','。不提供精确出生位置；这仅用于有限的反思，不应视为个体结论。'),
      (' symbolizes ','象征'),('. Your ', '。你的'),('Your ','你的'),(' in ','位于'),(' at ','，度数为'),(' is read symbolically through ','，可从象征角度联系'),
      ('. This placement may emphasize ','。这个位置可能突出'),('. In relationships, name this need openly instead of expecting a partner to infer it.','。在关系中，请直接表达这种需要，而不是期待对方自行猜到。'),
      (' Its ',' 其'),(' placement brings this theme into ','位置将该主题带入'),('. Compare this with your experience; a chart does not establish anyone\'s motives.','。请结合你的实际经历核对；星盘无法确认任何人的动机。'),
      ('The calculated midpoint ','计算得到的中点'),(' is in ','位于'),('. As a symbolic relationship pattern, this invites attention to ','。作为象征性的关系模式，它邀请你关注'),(' and ','以及'),('. It is a mathematical midpoint chart, not a prediction or an actual birth event.','。这是数学中点盘，不是预测，也不是实际出生事件。'),
      ('The calculated orb is ','计算得到的容许度为'),('°, within the configured major-aspect limit. Symbolically, ','°，处于设定的主要相位范围内。从象征角度，'),('. This is an interpretive theme to check against lived experience, not evidence of destiny or a private intention.','。这是需要结合实际经历核对的解读主题，不能作为命运或私人意图的证据。')]
    meanings=['themes become closely linked; clarify where closeness helps and where space is needed','these needs may cooperate readily; put that ease into visible care','cooperation may develop through deliberate small efforts','different needs can create friction; agree on a repair process before conflict escalates','contrasting needs invite balance; avoid treating one perspective as the only valid one']
    rules+=list(zip(meanings,MEANING_ZH))+list(zip(ROLES.values(),ROLES_ZH))+list(zip(themes.values(),SIGN_ZH))+list(zip(HOUSE.values(),HOUSE_ZH))
    # Longest phrases first, so subphrases cannot damage an exact translation.
    for en,zh in sorted(rules,key=lambda pair:len(pair[0]),reverse=True):text=text.replace(en,zh)
    for en,zh in {**PLANETS,**SIGNS,**ASPECT_ZH}.items():text=re.sub(r'(?<![A-Za-z])'+en+r'(?![A-Za-z])',zh,text)
    for i,h in enumerate(HOUSE):text=text.replace(h.replace('_',' '),f'第{i+1}宫')
    return text

def enrich(sections,uncertain=False):
    for s in sections:
        s['title_zh']=translate(s['title']);s['text_zh']=translate(s['text'])
        planet=next((p for p in PLANETS if ' · '+p in s['title']),None)
        qs={'Sun':('When do you feel most able to be yourself with your partner?','和伴侣相处时，什么时候最能自在做自己？'),'Moon':('What helps you feel emotionally safe after a difficult conversation?','一次困难的对话后，什么能帮你恢复情绪安全感？'),'Venus':('Which small gestures help you feel loved?','哪些小举动让你感到被爱？'),'Mars':('How do you prefer to express frustration without hurting each other?','你希望怎样表达挫折，才能减少对彼此的伤害？'),'Mercury':('Can you share a recent moment when you felt understood or misunderstood?','能分享一次最近感到被理解或被误解的经历吗？'),'Saturn':('What commitment feels realistic and mutual right now?','现在什么承诺是实际可行、并得到双方认可的？')}
        s['question_en'],s['question_zh']=qs.get(planet,('Does this feel familiar? What recent experience comes to mind?','这与你的经历相符吗？你想到了最近的哪件事？'))
    intro='Thank you for sharing your birth details. '+('Since the birth information includes an unknown or approximate time, this reading leaves out rising signs, houses and exact placements that cannot be confirmed. ' if uncertain else 'Please check that the birth dates, local times and birthplaces are accurate. ')+"Use this reading as a starting point for reflection. It cannot tell us what someone privately feels or guarantee where the relationship will go. What would you most like clarity on—communication, emotional closeness, or where you stand with each other?"
    intro_zh='谢谢你分享出生资料。'+('由于出生资料含未知或约略时间，本报告省略无法确认的上升、宫位和精确位置。' if uncertain else '请确认出生日期、当地时间和出生地点准确。')+'请把解读作为反思的起点；它无法确认他人的私人感情，也不能保证关系走向。你现在最希望厘清的是沟通、情感亲近，还是彼此的关系定位？'
    messages=[('Start the conversation','英文开场',intro,intro_zh),('If it feels accurate','客户觉得符合时',"Thank you for sharing that. Which part feels most relevant, and what would you like to change in that situation?",'谢谢你分享。哪一部分最贴近你的情况？在那个情境中，你最希望改变什么？'),('If it does not fit','客户觉得不符合时',"Thank you for telling me. We do not need to force the reading to fit. What feels different in your experience?",'谢谢你告诉我。我们不需要勉强让解读套上你的经历。你的实际体验有哪些不同？'),('Close with a practical step','咨询收尾',"What is one small conversation or action you feel ready to try? We can use your experience to decide what to explore next.",'你准备尝试哪一个小对话或行动？我们可以根据你的实际体验，决定接下来探索什么。')]
    guides=[{'title':a,'title_zh':b,'text':c,'text_zh':d,'kind':'conversation'} for a,b,c,d in messages]
    guides.insert(0,{'title':'How to use this reading','title_zh':'员工使用说明','text':'Verify the birth facts. Share two or three relevant points first. Ask one question and listen before continuing. Use the full report for reference, then send the love card as a recap. If the client disagrees, explore their experience without forcing a match. Follow-up suggestions are prepared prompts, not an AI assessment of the client reply.','text_zh':'先核对出生资料；先发与客户问题相关的两三点，再问一个问题，听取回应后继续。完整报告用于核对，爱情卡用于咨询回顾。客户觉得不符合时，先了解真实经历，不强行套用。后续话术是预先准备的提示，并非AI对客户回复的判断。','kind':'staff'})
    return guides+sections

def report_html(sections):
    blocks=[]
    for s in sections:
        q='<p><b>Follow-up question / 互动问题</b><br>'+escape(s['question_en'])+'<br>'+escape(s['question_zh'])+'</p>' if 'question_en' in s else ''
        blocks.append('<section><h2>'+escape(s['title'])+'<br>'+escape(s['title_zh'])+'</h2><p>'+escape(s['text'])+'</p><p class="zh">'+escape(s['text_zh'])+'</p>'+q+'<button data-copy="'+escape(s['text'],quote=True)+'">复制英文正文</button></section>')
    return '<!doctype html><meta charset="utf-8"><title>Evelyn Brooks · 中英对照解读</title><style>body{max-width:850px;margin:40px auto;padding:20px;background:#fcf8ef;color:#3e173b;font:19px/1.7 Georgia}section{border-bottom:1px solid #dbcbb5;padding:24px 0}.zh{font-family:Arial;color:#685866}button{padding:10px;background:#41213f;color:white;border:0;border-radius:5px}</style><h1>Evelyn Brooks · Detailed Reading<br>中英对照解读与咨询话术</h1>'+''.join(blocks)+'''<script>document.onclick=async e=>{if(e.target.dataset.copy){try{await navigator.clipboard.writeText(e.target.dataset.copy);e.target.textContent='已复制英文'}catch{e.target.textContent='请选中英文正文复制'}}}</script>'''
