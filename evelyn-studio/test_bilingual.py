from bilingual import enrich,report_html,translate
from reading import reading

def test_unknown_time_bilingual_and_interaction():
    r={'birth_inputs':[{'name':'Example'}],'natal':[{'warning':'30-minute samples across the local birth day; ranges are not guaranteed bounds. No exact birth degrees, angles, houses or aspects are claimed.','planet_daily_ranges':{'Moon':{'possible_signs':['Ari','Tau']}}}]}
    original=reading(r);paired=enrich(reading(r),True)
    assert [(x['title'],x['text']) for x in paired if not x.get('kind')]==[(x['title'],x['text']) for x in original]
    assert all(x['text_zh'] and x['title_zh'] for x in paired)
    assert '未知' in paired[1]['text_zh']
    assert '白羊座' in paired[-2]['text_zh']
    assert paired[-2]['question_en'] and paired[-2]['question_zh']
    html=report_html(paired);assert '复制英文正文' in html and '中英对照' in html

def test_exact_placement_translation_preserves_degrees():
    r={'birth_inputs':[{'name':'Example'}],'natal':[{'subject':{p:{'sign':'Ari','position':12.34,'house':'First_House'} for p in ['sun','moon','mercury','venus','mars','saturn']}}]}
    paired=enrich(reading(r))
    for s in paired[5:-1]:
        assert '12.34°' in s['text_zh'] and '第一宫' not in s['text_zh'] and '第1宫' in s['text_zh']
        assert '白羊座' in s['text_zh']
    assert '精确位置' not in paired[1]['text_zh']

def test_aspect_translation():
    from reading import aspect
    a=aspect({'p1_name':'Sun','p2_name':'Moon','aspect':'square','orbit':2.1},'Between you')
    assert '太阳 四分相 月亮' in translate(a['title'])
    assert '2.10°' in translate(a['text'])
    assert '修复方式' in translate(a['text'])
