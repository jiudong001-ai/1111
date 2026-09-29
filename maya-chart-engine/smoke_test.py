"""Exercise a running server using synthetic fixtures, never customer records.

Usage: python smoke_test.py http://127.0.0.1:8765
       python smoke_test.py https://<verified-render-hostname>
"""
import json
import sys
import urllib.request

base = sys.argv[1].rstrip('/')
sample = {'birth_date': '2000-01-01', 'birth_time': '12:00:00',
          'latitude': 51.4779, 'longitude': 0, 'timezone': 'Europe/London'}


def request(path, data=None, headers=None):
    payload = None if data is None else json.dumps(data).encode()
    headers = {'Content-Type': 'application/json', **(headers or {})}
    with urllib.request.urlopen(urllib.request.Request(base + path, data=payload, headers=headers), timeout=90) as response:
        assert response.status == 200
        return json.load(response)


assert request('/health')['status'] == 'ok'
for path, data, expected in [('/api/natal', sample, 'natal'),
                             ('/api/synastry', {'person_a': sample, 'person_b': sample}, 'synastry'),
                             ('/api/transits', {'birth': sample, 'transit_timestamp': '2026-09-29T12:00:00Z'}, 'transit')]:
    assert request(path, data)['chart_type'] == expected
headers = {'Accept': 'application/json, text/event-stream'}
init = request('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                      'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                                 'clientInfo': {'name': 'maya-smoke-test', 'version': '1'}}}, headers)
headers['MCP-Protocol-Version'] = init['result']['protocolVersion']
tools = request('/mcp', {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}, headers)
assert {tool['name'] for tool in tools['result']['tools']} == {'calculate_natal', 'calculate_synastry', 'calculate_transits'}
for i, (name, arguments) in enumerate([
    ('calculate_natal', {'birth': sample}),
    ('calculate_synastry', {'person_a': sample, 'person_b': sample}),
    ('calculate_transits', {'birth': sample, 'transit_timestamp': '2026-09-29T12:00:00Z'})
], 3):
    result = request('/mcp', {'jsonrpc': '2.0', 'id': i, 'method': 'tools/call',
                            'params': {'name': name, 'arguments': arguments}}, headers)['result']
    assert not result.get('isError'), result
    assert result['structuredContent']['schema_version'] == 'maya-chart-1.0'
print(json.dumps({'base_url': base, 'health': 'passed', 'rest_calculations': 3,
                  'mcp_initialize': 'passed', 'mcp_tools_discovered': 3, 'mcp_calculations': 3}))
