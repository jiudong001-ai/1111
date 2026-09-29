from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from contextlib import nullcontext

from app import app
from engine import BirthData, calculate_natal, calculate_synastry, calculate_transits, local_to_utc, planets_at, house_of

EXAMPLE = {'birth_date': '2000-01-01', 'birth_time': '12:00', 'latitude': 51.4779,
           'longitude': 0, 'timezone': 'Europe/London', 'place': 'Greenwich (synthetic fixture)'}


def birth(**overrides):
    return BirthData(**{**EXAMPLE, **overrides})


@pytest.fixture(scope='module')
def running_client():
    with TestClient(app, base_url='http://localhost') as client:
        yield client


def test_j2000_known_positions_and_greenwich_angles():
    chart = calculate_natal(birth())
    # Independent rounded J2000 astronomical check: Sun ~280.37, Moon ~223.32.
    assert chart['planets']['Sun']['longitude'] == pytest.approx(280.37, abs=0.02)
    assert chart['planets']['Moon']['longitude'] == pytest.approx(223.32, abs=0.03)
    assert chart['planets']['Sun']['sign'] == 'Capricorn'
    assert chart['angles']['ASC']['longitude'] == pytest.approx(24.27, abs=0.15)
    assert len(chart['house_cusps']) == 12
    assert all(1 <= p['house'] <= 12 for p in chart['planets'].values())


def test_equinox_sun_near_zero():
    sun = planets_at(datetime(2024, 3, 20, 3, 6, tzinfo=timezone.utc))['Sun']['longitude']
    assert min(sun, 360 - sun) < 0.01


def test_mercury_retrograde_and_skipped_civil_date():
    planets = planets_at(datetime(2024, 4, 10, 12, tzinfo=timezone.utc))
    assert planets['Mercury']['retrograde'] is True
    assert planets['Sun']['retrograde'] is False
    with pytest.raises(ValueError, match='date did not exist'):
        calculate_natal(birth(birth_date='2011-12-30', birth_time=None, timezone='Pacific/Apia'))


def test_equivalent_instants_and_timezone_date_rollover():
    london = calculate_natal(birth())
    ny = calculate_natal(birth(birth_time='07:00', timezone='America/New_York'))
    assert london['planets'] == ny['planets']
    assert local_to_utc(datetime(2000, 1, 1, 1), 'Asia/Tokyo').isoformat() == '1999-12-31T16:00:00+00:00'


def test_dst_nonexistent_rejected_and_repeated_requires_fold():
    with pytest.raises(ValueError, match='did not exist'):
        calculate_natal(birth(birth_date='2024-03-10', birth_time='02:30', timezone='America/New_York'))
    with pytest.raises(ValueError, match='occurred twice'):
        calculate_natal(birth(birth_date='2024-11-03', birth_time='01:30', timezone='America/New_York'))
    a = local_to_utc(datetime(2024, 11, 3, 1, 30), 'America/New_York', 0)
    b = local_to_utc(datetime(2024, 11, 3, 1, 30), 'America/New_York', 1)
    assert (b-a).total_seconds() == 3600


def test_unknown_time_has_no_fabricated_chart():
    chart = calculate_natal(birth(birth_time=None))
    assert not chart['planets'] and not chart['aspects']
    assert chart['angles'] is None and chart['house_cusps'] is None
    assert 'timestamp_utc' not in chart
    moon = chart['planet_daily_ranges']['Moon']
    assert moon['offset_max_deg'] - moon['offset_min_deg'] > 10


def test_approximate_time_withholds_angles_and_houses():
    chart = calculate_natal(birth(time_accuracy='approximate'))
    assert chart['angles'] is None and chart['house_cusps'] is None
    assert all('house' not in p for p in chart['planets'].values())


def test_polar_placidus_does_not_silently_fallback():
    chart = calculate_natal(birth(latitude=80))
    assert chart['house_cusps'] is None and chart['angles'] is None and chart['warnings']


def test_whole_sign_and_house_wrap():
    chart = calculate_natal(birth(house_system='whole_sign'))
    assert all(c % 30 == 0 for c in chart['house_cusps'])
    cusps = [(350 + 30 * i) % 360 for i in range(12)]
    assert house_of(0, cusps) == 1
    assert house_of(20, cusps) == 2
    assert house_of(349.999, cusps) == 12


def test_synastry_identity_and_unknown_time_restrictions():
    result = calculate_synastry(birth(), birth())
    same = [a for a in result['cross_aspects'] if a['body_a'] == a['body_b']]
    assert len(same) == 14
    assert all(a['orb'] == 0 and a['aspect'] == 'conjunction' for a in same)
    assert len(result['house_overlays']['a_in_b']) == 10
    unknown = calculate_synastry(birth(), birth(birth_time=None))
    assert unknown['cross_aspects'] == [] and unknown['house_overlays'] == {}


def test_transit_offset_required_and_identity():
    with pytest.raises(ValueError, match='offset'):
        calculate_transits(birth(), datetime(2000, 1, 1, 12))
    result = calculate_transits(birth(), datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
    same = [a for a in result['natal_to_transit_aspects'] if a['body_a'] == a['body_b']]
    assert len(same) == 10 and all(a['orb'] == 0 for a in same)


@pytest.mark.parametrize('change', [{'latitude': 91}, {'longitude': float('nan')}, {'birth_date': '1700-01-01'}, {'timezone': 'Invalid/Zone'}, {'birth_time': '12:00+03:00'}, {'time_accuracy': 'unknown'}])
def test_invalid_inputs(change):
    with pytest.raises(ValidationError):
        birth(**change)


def test_rest_health_calculation_errors_and_body_limit(running_client):
    with nullcontext(running_client) as client:
        assert client.get('/health').json()['status'] == 'ok'
        assert client.get('/').status_code == 200
        assert client.post('/api/natal', json=EXAMPLE).json()['chart_type'] == 'natal'
        assert client.post('/api/synastry', json={'person_a': EXAMPLE, 'person_b': EXAMPLE}).json()['chart_type'] == 'synastry'
        assert client.post('/api/transits', json={'birth': EXAMPLE, 'transit_timestamp': '2026-09-29T12:00:00Z'}).json()['chart_type'] == 'transit'
        error = client.post('/api/natal', json={**EXAMPLE, 'latitude': 100, 'name': 'PRIVATE-NAME'})
        assert error.status_code == 422 and 'PRIVATE-NAME' not in error.text
        assert client.post('/api/natal', content='x' * 65537).status_code == 413
        assert client.get('/health', headers={'Host': 'evil.example'}).status_code == 421


def test_mcp_initialize_discover_and_call_all_three_tools(running_client):
    headers = {'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json'}
    with nullcontext(running_client) as client:
        def rpc(method, params, reqid=1):
            response = client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': reqid, 'method': method, 'params': params})
            assert response.status_code == 200, response.text
            return response.json()
        init = rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
        assert 'serverInfo' in init['result']
        headers['MCP-Protocol-Version'] = init['result']['protocolVersion']
        names = {t['name'] for t in rpc('tools/list', {})['result']['tools']}
        assert names == {'calculate_natal', 'calculate_synastry', 'calculate_transits'}
        for name, args in [('calculate_natal', {'birth': EXAMPLE}), ('calculate_synastry', {'person_a': EXAMPLE, 'person_b': EXAMPLE}), ('calculate_transits', {'birth': EXAMPLE, 'transit_timestamp': '2026-09-29T12:00:00Z'})]:
            result = rpc('tools/call', {'name': name, 'arguments': args})['result']
            assert not result.get('isError'), result
            assert result['structuredContent']['schema_version'] == 'maya-chart-1.0'
