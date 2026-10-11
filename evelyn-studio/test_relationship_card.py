from relationship_card import relationship_card

def test_unknown_time_is_general_and_optional_signature_is_escaped():
    html=relationship_card({'synastry':None},'<Sarah>')
    assert 'General relationship reflection' in html
    assert 'prevents a specific synastry reading' in html
    assert '&lt;Sarah&gt;' in html and '<Sarah>' not in html
    assert 'With care' not in relationship_card({})
    assert html.count('class="row"')==4
    assert 'data:image/jpeg;base64,' in html

def test_aspects_are_attributed_and_copy_is_distinct():
    aspects=[{'p1_owner':'Alice','p2_owner':'Bob','p1_name':'Venus','p2_name':'Moon','aspect':'conjunction','orbit':1}, {'p1_owner':'Alice','p2_owner':'Bob','p1_name':'Moon','p2_name':'Mars','aspect':'square','orbit':2}, {'p1_owner':'Alice','p2_owner':'Bob','p1_name':'Moon','p2_name':'Venus','aspect':'opposition','orbit':3}]
    html=relationship_card({'synastry':{'aspects':aspects}})
    assert 'Alice’s Venus conjunction Bob’s Moon' in html
    assert html.count('Emotional needs may not always line up.')==1
    assert 'real potential to reconnect' not in html

