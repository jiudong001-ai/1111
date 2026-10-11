"""English relationship recap with chart-grounded copy and an angel editorial layout."""
from html import escape
from pathlib import Path
import base64

STYLE = """*{box-sizing:border-box}body{margin:0;background:#faf4ec;color:#41213f}.card{width:1080px;min-height:1350px;padding:14px 22px 24px;border:2px solid #c3a06b;border-radius:28px;background:radial-gradient(ellipse at 15% 55%,#f7e8e280,transparent 65%),#fcf7ef;font-family:Georgia,'Times New Roman',serif}.hero{display:block;width:100%;height:265px;object-fit:cover;border-radius:20px}.heading{text-align:center;padding:23px 0 20px}.eyebrow{font:15px Arial,sans-serif;letter-spacing:3px;text-transform:uppercase;color:#79576f}h1{font-size:53px;font-weight:400;margin:10px 0;line-height:1.1}.subtitle{font-size:23px;font-style:italic;margin:0;color:#79576f}.divider{width:360px;border-top:1px solid #c3a06b;margin:15px auto}.row{display:grid;grid-template-columns:88px minmax(0,1fr) 104px;gap:22px;align-items:center;padding:21px 20px;border:1px solid #d6b591;border-radius:20px;margin-bottom:10px;min-height:172px}.number{align-self:start;display:flex;align-items:center;justify-content:center;width:74px;height:74px;border-radius:50%;border:1px solid #d6b591;background:linear-gradient(135deg,#f7e5da,#edced4);font-size:35px}.copy{min-width:0}h2{font-size:29px;margin:0 0 9px;font-weight:600}.copy p{font-size:24px;line-height:1.34;margin:0;text-wrap:pretty}.basis{font:14px/1.4 Arial,sans-serif;color:#806878;margin-top:9px}.vignette{height:112px;border-radius:60px 60px 5px 5px;background-image:var(--art);background-size:auto 130px;background-position:left center}.row:nth-child(2) .vignette{background-position:center}.row:nth-child(3) .vignette{background-position:right}.row:nth-child(4) .vignette{background-position:20% center}.closing{text-align:center;border:1px solid #d6b591;border-radius:18px;padding:18px 30px;margin-top:14px}.closing p{font-size:20px;line-height:1.4;margin:0}.signature{margin-top:12px;font-size:18px}.signature span{display:block;font-size:30px;font-style:italic;overflow-wrap:anywhere;margin-top:4px}footer{font:14px/1.45 Arial,sans-serif;text-align:center;color:#806878;margin:15px 25px 0}"""

def relationship_card(report, staff_name=''):
    aspects=(report.get('synastry') or {}).get('aspects',[])
    planets={'Sun','Moon','Venus','Mars','Mercury','Saturn'}
    relevant=[a for a in aspects if a.get('p1_name') in planets and a.get('p2_name') in planets and a.get('aspect') in {'conjunction','trine','sextile','square','opposition'}]
    relevant.sort(key=lambda a:abs(a['orbit']))
    ease=next((a for a in relevant if a['aspect'] in {'trine','sextile'}),None) or next((a for a in relevant if a['aspect']=='conjunction'),None)
    tension=next((a for a in relevant if a['aspect'] in {'square','opposition'}),None)
    emotional=next((a for a in relevant if 'Moon' in {a['p1_name'],a['p2_name']} and a not in [ease,tension]),None)
    blocks=[
      ('Your Connection',meaning(ease) if ease else 'Begin with your own experience of this connection. Notice whether care, interest, and effort feel mutual, rather than assuming that attraction tells you how the other person feels.',ease),
      ('Where You May Struggle',meaning(tension) if tension else 'When something feels unclear, ask what the other person means before drawing a conclusion. Different expectations are easier to discuss when each of you can speak without pressure.',tension),
      ('Emotional Needs',emotional_meaning(emotional) if emotional else 'Ask what helps each of you feel supported: a thoughtful check-in, time together, or a little space. Let their answer guide you instead of expecting the same kind of reassurance.',emotional),
      ('Your Next Step','Choose one small conversation rather than trying to resolve everything at once. Share a need, ask an open question, and notice whether both of you are willing to listen.',None)]
    art='data:image/jpeg;base64,'+base64.b64encode((Path(__file__).parent/'relationship_assets/angel-lake.jpg').read_bytes()).decode()
    rows=[]
    for i,(heading,text,a) in enumerate(blocks,1):
        evidence=('<div class="basis">Chart focus: '+escape(a.get('p1_owner','Person 1')+'’s '+a['p1_name']+' '+a['aspect']+' '+a.get('p2_owner','Person 2')+'’s '+a['p2_name'])+'</div>') if a else ''
        rows.append('<section class="row"><div class="number">'+str(i).zfill(2)+'</div><div class="copy"><h2>'+escape(heading)+'</h2><p>'+escape(text)+'</p>'+evidence+'</div><div class="vignette" aria-hidden="true"></div></section>')
    signature=('<div class="signature">With care,<span>'+escape(staff_name.strip())+'</span></div>') if staff_name.strip() else ''
    label='A personal astrology reflection' if relevant else 'General relationship reflection'
    limitation=('Based on selected synastry aspects. ' if relevant else 'Birth-time uncertainty or limited chart evidence prevents a specific synastry reading. ')+"Astrology cannot establish another person’s feelings or promise reconciliation."
    return '<!doctype html><html lang="en-US"><meta charset="utf-8"><title>Relationship Insights</title><style>'+STYLE+'</style><main class="card" style="--art:url('+art+')"><img class="hero" src="'+art+'" alt="Angel sculpture, roses and a sunset lake"><header class="heading"><div class="eyebrow">'+label+'</div><h1>Relationship Insights</h1><div class="divider"></div><p class="subtitle">Understanding your connection, one conversation at a time.</p></header>'+''.join(rows)+'<div class="closing"><p>Take what resonates, and give yourself room to reflect.</p>'+signature+'</div><footer>'+escape(limitation)+'</footer></main></html>'

def emotional_meaning(a):
    if a['aspect'] in {'trine','sextile'}:
        return 'A familiar rhythm of care may feel supportive. Ask which gestures matter most, and remember that understanding each other still takes attention and conversation.'
    if a['aspect']=='conjunction':
        return 'Feelings may be closely involved in this connection. Make room to name what you need, while allowing the other person to describe their experience in their own words.'
    return 'You may need different kinds of reassurance or different amounts of space. Agree on a simple way to check in, without asking either person to ignore their own needs.'

def basis(a):
    # Owners come from the v6 aspect model, not the order of the planet names.
    return f"Chart note · {a['p1_owner']}’s {a['p1_name']} {a['aspect']} {a['p2_owner']}’s {a['p2_name']} · {abs(a['orbit']):.1f}° orb"

def meaning(a):
    planets = {a['p1_name'],a['p2_name']}
    smooth = a['aspect'] in {'trine','sextile'}
    joined = a['aspect']=='conjunction'
    if joined:
        return 'This planetary pairing highlights a shared area of attention. Explore how affection, feelings, communication, or commitment show up between you, without assuming that similarity guarantees an easy relationship.'
    if 'Saturn' in planets:
        return ('Steady follow-through may help you build trust. Talk about which commitments feel realistic for both of you.' if smooth else 'Commitment and boundaries may need extra care. Discuss expectations without making either person feel judged or responsible for everything.')
    if 'Mercury' in planets:
        return ('Conversation may be a useful way to find common ground. Make room for each other’s perspective, especially when you disagree.' if smooth else 'You may approach a conversation differently. Slow down, check what the other person means, and avoid assuming that silence or a short reply tells the whole story.')
    if 'Moon' in planets:
        return ('Small signs of care may help you feel more at ease together. Ask what kind of reassurance each of you actually appreciates.' if smooth else 'Emotional needs may not always line up. One person’s way of showing care might not be what the other needs; naming that difference can help.')
    if 'Venus' in planets or 'Mars' in planets:
        return ('Affection and initiative may work well together. Notice which gestures feel welcome, and let the pace be comfortable for both of you.' if smooth else ('Affection and desire are closely linked in this chart pattern. Explore what feels good to both of you without assuming that attraction means agreement.' if joined else 'Affection, desire, or timing may differ. Be clear about what each of you wants, and give each other room to say yes, no, or not yet.'))
    return ('You may find room to support each other’s sense of self. Stay curious about the interests and values that make each of you feel most like yourself.' if smooth else 'Your priorities may sometimes pull in different directions. Try naming the difference without treating either person’s perspective as wrong.')

