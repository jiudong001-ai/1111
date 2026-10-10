from html import escape
ROLES={'Sun':'identity and the values you want to live by','Moon':'emotional safety and the way you receive care','Mercury':'communication and the way you make sense of a disagreement','Venus':'affection, attraction and what feels worth investing in','Mars':'desire, initiative and the way you handle frustration','Saturn':'commitment, boundaries and the responsibilities you take seriously'}
SIGNS={'Ari':'directness and room to act independently','Tau':'consistency, physical comfort and a steady pace','Gem':'curiosity, conversation and flexibility','Can':'belonging, tenderness and emotional continuity','Leo':'warmth, recognition and wholehearted expression','Vir':'thoughtful details, useful support and clear expectations','Lib':'mutual consideration, fairness and dialogue','Sco':'depth, privacy and carefully earned trust','Sag':'honesty, exploration and room to grow','Cap':'dependability, long-term effort and practical commitments','Aqu':'friendship, individuality and room for different perspectives','Pis':'compassion, imagination and sensitivity to atmosphere'}
HOUSE={'First_House':'self-expression','Second_House':'values and material security','Third_House':'everyday communication','Fourth_House':'home and belonging','Fifth_House':'romance and creative pleasure','Sixth_House':'daily care and routines','Seventh_House':'partnership agreements','Eighth_House':'intimacy, vulnerability and shared resources','Ninth_House':'beliefs and growth','Tenth_House':'public responsibilities','Eleventh_House':'friendship and future hopes','Twelfth_House':'privacy and inner reflection'}
def reading(r):
    sections=[]
    for i,n in enumerate(r['natal']):
        name=r['birth_inputs'][i]['name']
        s=n.get('subject')
        if not s:
            sections.append({'title':name+' — birth time uncertainty','text':n['warning']})
            for planet,pr in n['planet_daily_ranges'].items():
                if planet in ROLES:sections.append({'title':name+' · '+planet,'text':f"The day samples include {', '.join(pr['possible_signs'])}. {planet} symbolizes {ROLES[planet]}. A precise birth placement is withheld; treat this as a limited reflection, not an individualized conclusion."})
            continue
        for planet,role in ROLES.items():
            p=s[planet.lower()];sign=p['sign'];house=p.get('house')
            text=f"Your {planet} in {sign} at {p['position']:.2f}° is read symbolically through {role}. This placement may emphasize {SIGNS[sign]}. In relationships, name this need openly instead of expecting a partner to infer it."
            if house:text+=f" Its {house.replace('_',' ')} placement brings this theme into {HOUSE.get(house,'that area of life')}. Compare this with your experience; a chart does not establish anyone's motives."
            sections.append({'title':name+' · '+planet,'text':text})
        for a in n.get('aspects',[])[:12]:sections.append(aspect(a,name+' · natal'))
    for key,label in [('synastry','Between you'),('composite','Relationship midpoint composite')]:
        d=r.get(key)
        if not d:continue
        if key=='composite':
            s=d['subject']
            for planet,role in ROLES.items():
                p=s[planet.lower()];sections.append({'title':label+' · '+planet,'text':f"The calculated midpoint {planet} is in {p['sign']} at {p['position']:.2f}°. As a symbolic relationship pattern, this invites attention to {role} and {SIGNS[p['sign']]}. It is a mathematical midpoint chart, not a prediction or an actual birth event."})
        for a in sorted(d.get('aspects',[]),key=lambda a:abs(a.get('orbit',99)))[:20]:sections.append(aspect(a,label))
        if key=='synastry' and d.get('house_comparison'):sections.append({'title':'House overlays','text':'The JSON retains both directions of the calculated house comparison. Pay particular attention to 5th-house romance, 7th-house agreements and 8th-house trust. An overlay suggests a topic to discuss; it cannot prove mutual attraction or consent.'})
    sections.append({'title':'A grounded next step','text':'Ask each other: What makes you feel cared for, how do you want to repair tension, and what commitment can you realistically sustain? Look for reciprocity in consistent actions. Astrology is a symbolic reflection practice; it cannot confirm private feelings or guarantee a relationship outcome.'})
    return sections
def aspect(a,label):
    x,y,n=a['p1_name'],a['p2_name'],a['aspect'];orb=abs(a['orbit'])
    meaning={'conjunction':'themes become closely linked; clarify where closeness helps and where space is needed','trine':'these needs may cooperate readily; put that ease into visible care','sextile':'cooperation may develop through deliberate small efforts','square':'different needs can create friction; agree on a repair process before conflict escalates','opposition':'contrasting needs invite balance; avoid treating one perspective as the only valid one'}[n]
    return {'title':f'{label} · {x} {n} {y}','text':f'The calculated orb is {orb:.2f}°, within the configured major-aspect limit. Symbolically, {meaning}. This is an interpretive theme to check against lived experience, not evidence of destiny or a private intention.'}
CSS='''body{margin:0;background:#f7f1e8;color:#3e173b;font-family:Georgia,serif}.card{box-sizing:border-box;width:1080px;min-height:1350px;padding:100px 90px;border:20px solid #e7d4b3;background:radial-gradient(circle at 90% 5%,#eed4d5,transparent 45%),#fcf8ef}.brand{letter-spacing:6px;font:20px Arial;color:#845e70}.rule{height:1px;background:#b99a60;margin:45px 0}h1{font-size:76px;font-weight:400;line-height:1.05}h2{font-size:32px;font-weight:400}p{font-size:27px;line-height:1.6}footer{font:17px Arial;color:#806674;margin-top:65px}.star{font-size:70px;color:#b99a60}'''
def card(kind,sections,day,staff_name=''):
    if kind=='daily':
        from datetime import date
        themes=[('Return to your center','Let care be something you practice, not something you have to earn.'),('Make room for tenderness','You can soften your tone while keeping your boundary.'),('Listen beneath the noise','Give yourself a moment to hear what you need before you answer.'),('Choose steady care','One small promise kept can matter more than a grand declaration.'),('Let your pace be honest','You do not have to rush intimacy to prove that you care.'),('Notice what nourishes you','Make room for the people and practices that help you feel at home.'),('Begin again, gently','A thoughtful repair starts with listening and one realistic next step.')]
        title,opening=themes[date.fromisoformat(day).toordinal()%len(themes)];subtitle=day
        paras=[opening,'Pause before responding. Ask what feels honest, kind and sustainable today.','A gentle practice: take three slow breaths, name one boundary, and offer one small act of care.'];note='Daily spiritual reflection · General inspiration; not a personal transit forecast.'
    else:title='The art of loving well';subtitle='A reflection for your connection';chosen=[s for s in sections if s['title'].startswith('Between you')][:2];paras=[s['title']+' — '+s['text'] for s in chosen] or [sections[0]['text']];paras+=['Choose one conversation about care, one clear boundary, and one promise you can keep.'];note='Chart-informed symbolic draft · Review against the full report and lived experience.'
    signature = '<p style="margin-top:38px;font-size:23px">With care,<br><span style="font-size:34px;font-style:italic;overflow-wrap:anywhere">'+escape(staff_name.strip())+'</span></p>' if staff_name.strip() else ''
    return '<!doctype html><meta charset="utf-8"><style>'+CSS+'</style><main class="card"><div class="rule"></div><div class="star">✧</div><h1>'+title+'</h1><h2>'+escape(subtitle)+'</h2>'+''.join('<p>'+escape(p)+'</p>' for p in paras)+signature+'<footer>'+note+'</footer></main>'
