"""Public, stateless calculator; no customer accounts or birth-data persistence.

SPDX-License-Identifier: AGPL-3.0-or-later
"""
import contextlib
import logging
import os
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from engine import BirthData, SOURCE, calculate_natal, calculate_synastry, calculate_transits

hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
hosts = ['localhost', 'localhost:*', '127.0.0.1', '127.0.0.1:*', 'testserver']
origins = ['http://localhost:*', 'http://127.0.0.1:*']
if hostname:
    hosts.append(hostname)
    origins.append('https://' + hostname)

mcp = FastMCP('Maya Chart Engine', stateless_http=True, json_response=True,
              instructions='Calculate tropical astrology charts from verified birth inputs. Never invent birth times or coordinates. Unknown birth times return sampled daily ranges, not a noon chart. No predictions or compatibility scores. All calculations are stateless.',
              transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins))


@mcp.tool(name='calculate_natal', structured_output=True, annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
def natal_tool(birth: BirthData) -> dict[str, Any]:
    """Calculate Sun through Pluto, major aspects, ASC/MC/DSC/IC and houses.

    Require verified latitude, east-positive longitude, IANA timezone and date.
    Omit birth_time when unknown; never substitute noon. Approximate time
    withholds houses/angles. Placidus is default; whole_sign/equal are explicit options.
    """
    return calculate_natal(birth)


@mcp.tool(name='calculate_synastry', structured_output=True, annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
def synastry_tool(person_a: BirthData, person_b: BirthData) -> dict[str, Any]:
    """Calculate two natal charts, cross-aspects including angles, and house overlays.

    No fate predictions, feelings inference or compatibility percentage. Both
    reliable birth times are required for house overlays.
    """
    return calculate_synastry(person_a, person_b)


@mcp.tool(name='calculate_transits', structured_output=True, annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
def transit_tool(birth: BirthData, transit_timestamp: datetime) -> dict[str, Any]:
    """Calculate transit planets and aspects to natal planets/angles (3-degree orb).

    Supply an explicit ISO timestamp including Z or UTC offset; never guess the
    target date. Birth data safeguards are identical to calculate_natal.
    """
    return calculate_transits(birth, transit_timestamp)


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title='Maya Chart Engine', version='1.0.0', lifespan=lifespan,
              description='Stateless tropical astrology calculations. No birth data is saved. Source and AGPL license available on the homepage.')


class SynastryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    person_a: BirthData
    person_b: BirthData


class TransitRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthData
    transit_timestamp: datetime


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not repeat customer input in error payloads.
    return JSONResponse(status_code=422, content={'errors': [{'field': list(e['loc']), 'message': e['msg']} for e in exc.errors()]})


@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse(status_code=422, content={'error': str(exc)})


class RequestGuards:
    """Bound request bodies and request rate before MCP parsing.

    Global per-process rate cap is deliberate: no IP addresses or request data
    are retained. Free single-instance deployment, no distributed rate claims.
    """
    def __init__(self, app):
        self.app = app
        self.window = 0
        self.count = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in scope.get('headers', [])}
        host = headers.get(b'host', b'').decode('latin1').split(':')[0]
        allowed = {'localhost', '127.0.0.1', 'testserver', hostname}
        if host not in allowed:
            return await JSONResponse({'error': 'Invalid Host'}, status_code=421)(scope, receive, send)
        if scope['method'] == 'POST':
            minute = int(time.monotonic() // 60)
            if minute != self.window:
                self.window, self.count = minute, 0
            self.count += 1
            if self.count > 120:
                return await JSONResponse({'error': 'Busy; retry in one minute'}, status_code=429, headers={'Retry-After': '60'})(scope, receive, send)
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > 65536:
                    return await JSONResponse({'error': 'Request too large'}, status_code=413)(scope, receive, send)
                if not message.get('more_body', False):
                    break
            consumed = False

            async def replay():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            await self.app(scope, replay, send)
        else:
            await self.app(scope, receive, send)


app.add_middleware(RequestGuards)


@app.get('/', response_class=HTMLResponse)
def home():
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('web.html').read_text(encoding='utf-8'),
                        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'no-referrer'})


from functools import lru_cache
from fastapi import Query


STATE_NAMES_ZH = {
    'AL': '阿拉巴马州', 'AK': '阿拉斯加州', 'AZ': '亚利桑那州', 'AR': '阿肯色州',
    'CA': '加利福尼亚州', 'CO': '科罗拉多州', 'CT': '康涅狄格州', 'DE': '特拉华州',
    'DC': '哥伦比亚特区', 'FL': '佛罗里达州', 'GA': '佐治亚州', 'HI': '夏威夷州',
    'ID': '爱达荷州', 'IL': '伊利诺伊州', 'IN': '印第安纳州', 'IA': '爱荷华州',
    'KS': '堪萨斯州', 'KY': '肯塔基州', 'LA': '路易斯安那州', 'ME': '缅因州',
    'MD': '马里兰州', 'MA': '马萨诸塞州', 'MI': '密歇根州', 'MN': '明尼苏达州',
    'MS': '密西西比州', 'MO': '密苏里州', 'MT': '蒙大拿州', 'NE': '内布拉斯加州',
    'NV': '内华达州', 'NH': '新罕布什尔州', 'NJ': '新泽西州', 'NM': '新墨西哥州',
    'NY': '纽约州', 'NC': '北卡罗来纳州', 'ND': '北达科他州', 'OH': '俄亥俄州',
    'OK': '俄克拉何马州', 'OR': '俄勒冈州', 'PA': '宾夕法尼亚州', 'RI': '罗得岛州',
    'SC': '南卡罗来纳州', 'SD': '南达科他州', 'TN': '田纳西州', 'TX': '得克萨斯州',
    'UT': '犹他州', 'VT': '佛蒙特州', 'VA': '弗吉尼亚州', 'WA': '华盛顿州',
    'WV': '西弗吉尼亚州', 'WI': '威斯康星州', 'WY': '怀俄明州',
}

PREFERRED_CITY_NAMES_ZH = {
    'New York City': '纽约市', 'Los Angeles': '洛杉矶', 'Chicago': '芝加哥',
    'Houston': '休斯敦', 'Phoenix': '菲尼克斯', 'Philadelphia': '费城',
    'San Antonio': '圣安东尼奥', 'San Diego': '圣迭戈', 'Dallas': '达拉斯',
    'San Jose': '圣何塞', 'Austin': '奥斯汀', 'Jacksonville': '杰克逊维尔',
    'San Francisco': '旧金山', 'Seattle': '西雅图', 'Boston': '波士顿',
    'Washington': '华盛顿', 'Las Vegas': '拉斯维加斯', 'Miami': '迈阿密',
    'Atlanta': '亚特兰大', 'Denver': '丹佛', 'Detroit': '底特律',
    'Portland': '波特兰', 'Orlando': '奥兰多', 'New Orleans': '新奥尔良',
}


def chinese_city_name(city):
    preferred = PREFERRED_CITY_NAMES_ZH.get(city['name'])
    if preferred:
        return preferred
    names = [name for name in city.get('alternatenames', [])
             if any('\u3400' <= char <= '\u9fff' for char in name)]
    return min(names, key=len) if names else ''


@lru_cache(maxsize=1)
def city_catalog():
    import geonamescache
    gc = geonamescache.GeonamesCache(min_city_population=1000)
    states = gc.get_us_states()
    rows = []
    for c in gc.get_cities().values():
        if c['countrycode'] != 'US' or not c.get('timezone'):
            continue
        state = c['admin1code']
        name_zh = chinese_city_name(c)
        rows.append({'id': str(c['geonameid']), 'name': c['name'],
                     'name_zh': name_zh, 'state': state,
                     'state_name': states.get(state, {}).get('name', state),
                     'state_name_zh': STATE_NAMES_ZH.get(state, ''),
                     'place': f"{c['name']}, {state}, USA", 'latitude': c['latitude'],
                     'longitude': c['longitude'], 'timezone': c['timezone'],
                     '_search': ' '.join([c['name'], name_zh,
                                          *c.get('alternatenames', [])]).casefold()})
    return sorted(rows, key=lambda c: (c['state_name'], c['name']))


@app.get('/api/states')
def states():
    return [{'code': code, 'name': name, 'name_zh': STATE_NAMES_ZH.get(code, '')}
            for code, name in
            sorted({(c['state'], c['state_name']) for c in city_catalog()}, key=lambda x: x[1])]


@app.get('/api/cities')
def cities(q: str = Query(default='', max_length=80), state: str = Query(default='', max_length=2)):
    query = q.strip().casefold()
    if not state and len(query) < 2:
        return []
    matches = [c for c in city_catalog() if (not state or c['state'] == state.upper())
               and (not query or query in c['_search'])]
    return [{k: v for k, v in c.items() if not k.startswith('_')} for c in matches]


@app.get('/health')
def health():
    # Exercise the actual backend rather than returning a constant readiness flag.
    from engine import planets_at, UTC
    planets_at(datetime(2000, 1, 1, 12, tzinfo=UTC))
    return {'status': 'ok', 'engine': 'Maya Chart Engine', 'version': '1.0.0',
            'schema_version': 'maya-chart-1.0', 'ephemeris': 'Moshier', 'source': SOURCE}


@app.post('/api/natal')
async def natal(birth: BirthData):
    return await run_in_threadpool(calculate_natal, birth)


@app.post('/api/synastry')
async def synastry(data: SynastryRequest):
    return await run_in_threadpool(calculate_synastry, data.person_a, data.person_b)


@app.post('/api/transits')
async def transits(data: TransitRequest):
    return await run_in_threadpool(calculate_transits, data.birth, data.transit_timestamp)


# Build the subapp before lifespan accesses its session manager.
app.mount('/', mcp.streamable_http_app())
logging.getLogger('mcp').setLevel(logging.WARNING)
