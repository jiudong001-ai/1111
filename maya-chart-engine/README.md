# Maya Chart Engine

A stateless, open-source tropical astrology calculation service. Provides
`calculate_natal`, `calculate_synastry`, and `calculate_transits` over Streamable
HTTP MCP at `/mcp`, plus REST endpoints and interactive documentation at `/docs`.

## Run

Python 3.11 or 3.12 recommended.

```sh
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --no-access-log
```

Run tests with `pip install -r requirements-dev.txt` then `pytest -q`.
Render build: `pip install -r maya-chart-engine/requirements.txt`.
Render start: `cd maya-chart-engine && uvicorn app:app --host 0.0.0.0 --port $PORT --no-access-log`.
Use `/health` for readiness. Render supplies `RENDER_EXTERNAL_HOSTNAME` for the
Host/Origin allowlist. No API keys, database, paid geocoding or storage required.

## Inputs

```json
{
  "name": "Example (synthetic)",
  "birth_date": "2000-01-01",
  "birth_time": "07:00:00",
  "time_accuracy": "exact",
  "place": "New York, NY, USA",
  "latitude": 40.7128,
  "longitude": -74.006,
  "timezone": "America/New_York",
  "house_system": "placidus"
}
```

The caller must verify coordinates and IANA timezone. City-only geocoding is
not implemented; ambiguous cities must be resolved before calculation. East
longitude is positive. Historical UTC conversion uses the IANA timezone database.
Nonexistent DST times are rejected. Repeated times require `fold: 0` (first) or
`fold: 1` (second), explicitly confirmed from records. Supported dates 1800–2399,
proleptic Gregorian; historical calendar changes and uncertain historical civil
time must be resolved by the caller. Fractional seconds are supported.

Omit `birth_time` when unknown. The result contains five-minute sampled daily
longitude ranges and sampled signs instead of a fabricated noon chart. These
are not rigorous interval bounds. No exact natal aspects, angles or houses are
returned for unknown times. Approximate times return provisional planetary
positions/aspects but no angles/houses. Polar Placidus failures are reported;
there is no silent fallback to another house system. Whole-sign and equal-house
systems are available only by explicit choice.

`POST /api/natal`: the birth object above.
`POST /api/synastry`: `{ "person_a": <birth>, "person_b": <birth> }`.
`POST /api/transits`: `{ "birth": <birth>, "transit_timestamp": "2026-09-29T12:00:00Z" }`.
Transit timestamp must include an offset. Returned synastry body_a is person A;
body_b is person B. Transit body_a is natal; body_b is transiting.

## Calculation conventions and limits

Uses pysweph 2.10.3.6 (the maintained pyswisseph community fork) and explicitly selects the **Moshier analytical backend**.
This distribution does not bundle the Swiss/JPL ephemeris files and does not
claim JPL-file precision. Tropical, geocentric apparent ecliptic coordinates
of date; ten bodies (Sun through Pluto). Retrograde flags use longitudinal speed.
House placement uses ecliptic longitude between cusps (not 3-D mundane position).
Major aspects: 0, 60, 90, 120, 180 degrees; fixed 6-degree natal/synastry orb,
3-degree transit orb. No applying/separating classifications or event predictions.
Synastry includes angular contacts and overlays when times support them.

Schema: `maya-chart-1.0`. Astronomy calculations and astrology interpretations
are separate; no compatibility percentages, predictions, or claims about feelings.

## Privacy and operation

Public calculator, no user database or persistence, no request-body logging.
Uvicorn access logging is disabled in the deployment command. Render and MCP
clients may process request/connection metadata. POST inputs are limited to 64
KiB. A per-process global limit of 120 POST requests/minute bounds usage without
retaining IP addresses. This is a small single-instance service, not a private
authenticated client portal. Free Render hosting can sleep and have cold starts.

## License and source

Copyright 2026 Maya Chart Engine contributors. AGPL-3.0-or-later; see LICENSE.
The full corresponding application source, tests, deployment scripts and
dependency pins are in this directory. `/` and `/health` link to the source.
Pysweph and bundled Swiss Ephemeris source/license:
https://github.com/sailorfe/pysweph (including its libswe submodule).
No proprietary Swiss Ephemeris license is claimed or purchased.

References:
- https://www.astro.com/swisseph/swephprg.htm
- https://github.com/astrorigin/pyswisseph
- https://github.com/modelcontextprotocol/python-sdk/tree/v1.x
