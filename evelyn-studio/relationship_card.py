"""English client card. Uses verified synastry only; never guesses context."""
from html import escape

STYLE = '''body{margin:0;background:#fcf8ef;color:#40223d}.card{box-sizing:border-box;width:1080px;min-height:1350px;padding:76px 82px;background:radial-gradient(ellipse at 100% 0%,#efd9dc,transparent 48%),#fcf8ef;border:12px solid #e9ddc8;font-family:Georgia,serif}.eyebrow{font:18px Arial,sans-serif;letter-spacing:4px;color:#806571;text-transform:uppercase}.line{height:1px;background:#b89c68;margin:28px 0 36px}h1{font-weight:400;font-size:68px;line-height:1.1;margin:0 0 24px}.intro{font-size:27px;line-height:1.5;margin-bottom:38px}h2{font:600 18px Arial,sans-serif;letter-spacing:2px;text-transform:uppercase;color:#80586c;margin:30px 0 14px}p{font-size:27px;line-height:1.5;margin:0 0 16px}.basis{font:18px/1.5 Arial,sans-serif;color:#786875}.prompt{background:#f1e4e1;border-left:4px solid #b89c68;padding:20px 26px;margin-top:34px}.prompt p{font-size:29px}footer{font:17px/1.5 Arial,sans-serif;color:#786875;margin-top:38px}'''

def relationship_card(report):
    aspects = (report.get('synastry') or {}).get('aspects', [])
    relevant = [a for a in aspects if a.get('p1_name') in {'Sun','Moon','Venus','Mars','Mercury','Saturn'} and a.get('p2_name') in {'Sun','Moon','Venus','Mars','Mercury','Saturn'} and a.get('aspect') in {'conjunction','trine','sextile','square','opposition'}]
    relevant.sort(key=lambda a: abs(a['orbit']))
    ease = next((a for a in relevant if a['aspect'] in {'trine','sextile'}), None)
    tension = next((a for a in relevant if a['aspect'] in {'square','opposition'}), None)
    blocks = []
    for heading, a in [('A place to connect', ease), ('Something to work through', tension)]:
        if a:
            blocks.append((heading, meaning(a), basis(a)))
    if not blocks:
        conjunction = next((a for a in relevant if a['aspect']=='conjunction'), None)
        if conjunction:
            blocks.append(('A shared focus', meaning(conjunction), basis(conjunction)))
    if not blocks:
        intro = 'Start with what you know about each other: how you communicate, what feels caring, and whether your actions match your words.'
        blocks = [('What matters now', 'Notice whether both of you make room for honest conversations and respect each other’s boundaries.', '')]
        limitation = 'Birth-time uncertainty or limited chart evidence prevents a specific relationship reading. This card offers general reflection.'
    else:
        intro = 'Your charts offer a starting point for a conversation. What matters most is how you show up for each other in everyday life.'
        limitation = 'Based on selected synastry aspects. Astrology offers reflection; it cannot tell you someone’s private feelings or promise an outcome.'
    body = ''.join('<h2>'+escape(h)+'</h2><p>'+escape(t)+'</p>'+('<div class="basis">'+escape(b)+'</div>' if b else '') for h,t,b in blocks)
    return '<!doctype html><html lang="en-US"><meta charset="utf-8"><style>'+STYLE+'</style><main class="card"><div class="eyebrow">Relationship insights</div><div class="line"></div><h1>Make room for<br>a real conversation.</h1><p class="intro">'+escape(intro)+'</p>'+body+'<h2>One small next step</h2><p>Share one thing that helps you feel cared for, then ask what that looks like for the other person.</p><div class="prompt"><h2>A question for you</h2><p>Which feels closer to your experience right now: finding connection, or working through different needs?</p></div><footer>'+escape(limitation)+'</footer></main></html>'

def basis(a):
    # Owners come from the v6 aspect model, not the order of the planet names.
    return f"Chart note · {a['p1_owner']}’s {a['p1_name']} {a['aspect']} {a['p2_owner']}’s {a['p2_name']} · {abs(a['orbit']):.1f}° orb"

def meaning(a):
    planets = {a['p1_name'],a['p2_name']}
    smooth = a['aspect'] in {'trine','sextile'}
    joined = a['aspect']=='conjunction'
    if 'Saturn' in planets:
        return ('Steady follow-through may help you build trust. Talk about which commitments feel realistic for both of you.' if smooth else 'Commitment and boundaries may need extra care. Discuss expectations without making either person feel judged or responsible for everything.')
    if 'Mercury' in planets:
        return ('Conversation may be a useful way to find common ground. Make room for each other’s perspective, especially when you disagree.' if smooth else 'You may approach a conversation differently. Slow down, check what the other person means, and avoid assuming that silence or a short reply tells the whole story.')
    if 'Moon' in planets:
        return ('Small signs of care may help you feel more at ease together. Ask what kind of reassurance each of you actually appreciates.' if smooth else 'Emotional needs may not always line up. One person’s way of showing care might not be what the other needs; naming that difference can help.')
    if 'Venus' in planets or 'Mars' in planets:
        return ('Affection and initiative may work well together. Notice which gestures feel welcome, and let the pace be comfortable for both of you.' if smooth else ('Affection and desire are closely linked in this chart pattern. Explore what feels good to both of you without assuming that attraction means agreement.' if joined else 'Affection, desire, or timing may differ. Be clear about what each of you wants, and give each other room to say yes, no, or not yet.'))
    return ('You may find room to support each other’s sense of self. Stay curious about the interests and values that make each of you feel most like yourself.' if smooth else 'Your priorities may sometimes pull in different directions. Try naming the difference without treating either person’s perspective as wrong.')
