import os
from fastapi.testclient import TestClient
from app import app

def test_online_host_and_origin(monkeypatch):
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME','evelyn-test.onrender.com')
    c=TestClient(app,base_url='https://evelyn-test.onrender.com')
    assert c.get('/health').json()=={'status':'ok'}
    assert c.get('/').status_code==200
    assert c.post('/api/parse',json={'text':'My name is Alice. I was born on June 15, 1990 at 2:30 PM in London, UK.'},headers={'Origin':'https://evelyn-test.onrender.com'}).status_code==200
    assert c.post('/api/parse',json={'text':'hi'},headers={'Origin':'https://other.example'}).status_code==403
    assert c.get('/health',headers={'Host':'other.example'}).status_code==403

def test_source_excludes_customer_data():
    import build_source
    from zipfile import ZipFile
    from pathlib import Path
    with ZipFile(Path(__file__).parent/'source.zip') as z:
        names=z.namelist()
        assert 'app.py' in names and 'LICENSE' in names and 'Dockerfile' in names
        assert not any('exports/' in p or 'ephemeris-data/' in p for p in names)
    assert TestClient(app).get('/source').status_code==200
