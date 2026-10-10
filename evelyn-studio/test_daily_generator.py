from datetime import date,timedelta
import pytest
from daily_card_generator import DailyCardGenerator

def test_weekday_palette_and_unique_copy():
    g=DailyCardGenerator()
    for revision in range(3):
        drafts=[g.draft(date(2026,10,12)+timedelta(days=i),revision) for i in range(7)]
        assert len({d['message'] for d in drafts})==7
        assert len({d['love'] for d in drafts})==7
        assert len({d['affirmation'] for d in drafts})==7
        for i,d in enumerate(drafts):
            g.validate(d)
            assert d['theme']==g.config['days'][i]['theme']
            assert d['main']==g.config['days'][i]['main']
            html=g.html(d)
            assert 'Evelyn' not in html and 'With care' not in html
            assert '{{' not in html
    assert g.draft('2026-10-12',0)['message']!=g.draft('2026-10-12',1)['message']

def test_editing_is_escaped_and_invalid_copy_blocked():
    g=DailyCardGenerator();d=g.draft('2026-10-12')
    d['headline']='<script>care</script>'
    assert '&lt;script&gt;' in g.html(d)
    d['message']='too short'
    with pytest.raises(ValueError):g.html(d)

def test_untrusted_palette_cannot_change_template():
    g=DailyCardGenerator();d=g.draft('2026-10-12');d['main']='</style><script>'
    assert '</style><script>' not in g.html(d)
