"""US city selection must carry valid coordinates and historical timezone rules."""
from fastapi.testclient import TestClient
from app import app


def test_us_city_selection_calculates_without_manual_coordinates():
    client = TestClient(app)
    states = client.get('/api/states').json()
    assert len(states) == 51
    assert {'code': 'NY', 'name': 'New York'} in states
    rows = client.get('/api/cities?state=NY').json()
    assert all(row['state'] == 'NY' and row['place'].endswith('USA') for row in rows)
    city = next(row for row in rows if row['name'] == 'New York City')
    assert city['timezone'] == 'America/New_York'
    birth = {key: city[key] for key in ['latitude', 'longitude', 'timezone', 'place']}
    birth.update(birth_date='2000-01-01', birth_time='12:00')
    result = client.post('/api/natal', json=birth)
    assert result.status_code == 200
    assert result.json()['timestamp_utc'].startswith('2000-01-01T17:00:00')


def test_invalid_state_and_blank_query_do_not_return_unrelated_cities():
    client = TestClient(app)
    assert client.get('/api/cities?state=ZZ').json() == []
    assert client.get('/api/cities').json() == []
    rows = client.get('/api/cities?state=CA&q=Los%20Angeles').json()
    assert rows and all(row['state'] == 'CA' for row in rows)
