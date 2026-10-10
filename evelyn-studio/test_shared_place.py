from intake import parse

def test_shared_place_with_informal_grammar():
    r=parse("Mine is January 3 1990. His is December 16 1992. His name is alex We was born in Dublin ga. I don't know the times")['people']
    assert r['client']['birth_date']['value']=='1990-01-03'
    assert r['partner']['birth_date']['value']=='1992-12-16'
    for p in r.values():
        assert p['place']['value']=='Dublin ga'
        assert p['birth_time']['value'] is None
        assert p['birth_time']['status']=='unknown'

def test_shared_place_does_not_overwrite_conflicting_location():
    r=parse('I was born in Boston. We were born in Dublin ga.')['people']
    assert r['client']['place']['status']=='conflict'
    assert r['client']['place']['value'] is None
    assert r['partner']['place']['value']=='Dublin ga'

def test_singular_place_stays_with_its_person():
    r=parse('I was born in London. He was born in Dublin ga.')['people']
    assert r['client']['place']['value']=='London'
    assert r['partner']['place']['value']=='Dublin ga'
