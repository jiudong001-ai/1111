"""Maya Chart Engine. Copyright 2026. SPDX-License-Identifier: AGPL-3.0-or-later."""
from datetime import date, datetime, time, timedelta, timezone
from itertools import combinations, product
from threading import RLock
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UTC = timezone.utc
LOCK = RLock()
SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
BODIES = {'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY, 'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER, 'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE, 'Pluto': swe.PLUTO}
ASPECTS = {'conjunction': 0, 'sextile': 60, 'square': 90, 'trine': 120, 'opposition': 180}
SOURCE = 'https://github.com/jiudong001-ai/1111/tree/maya-chart-engine/maya-chart-engine'


class BirthData(BaseModel):
    """Verified coordinates (east longitude positive) and IANA timezone required.

    Do not guess birth time. Omit birth_time if unknown. Resolve ambiguous city
    names with the client before supplying latitude/longitude/timezone.
    """
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    name: str = Field(default='', max_length=100)
    birth_date: date
    birth_time: time | None = None
    time_accuracy: Literal['exact', 'approximate', 'unknown'] = 'exact'
    place: str = Field(default='', max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(max_length=100, description='IANA name, e.g. America/New_York; not EST')
    fold: Literal[0, 1] | None = Field(default=None, description='Only for repeated DST time: 0 first occurrence, 1 second')
    house_system: Literal['placidus', 'whole_sign', 'equal'] = 'placidus'

    @field_validator('birth_date')
    @classmethod
    def date_range(cls, value):
        if not 1800 <= value.year <= 2399:
            raise ValueError('Supported years: 1800–2399')
        return value

    @field_validator('timezone')
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Use a valid IANA timezone such as America/New_York') from None
        return value

    @field_validator('birth_time')
    @classmethod
    def naive_time(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError('birth_time must be local wall time without an offset; use timezone and fold')
        return value

    @model_validator(mode='after')
    def time_consistency(self):
        if self.time_accuracy == 'unknown' and self.birth_time is not None:
            raise ValueError('Omit birth_time when time_accuracy is unknown')
        return self


def local_to_utc(wall: datetime, zone: str, fold: int | None = None) -> datetime:
    tz = ZoneInfo(zone)
    candidates = {}
    for f in (0, 1):
        local = wall.replace(tzinfo=tz, fold=f)
        utc = local.astimezone(UTC)
        if utc.astimezone(tz).replace(tzinfo=None) == wall:
            candidates[f] = utc
    if not candidates:
        raise ValueError('This local time did not exist due to a timezone/DST change; verify the birth time')
    if len(set(candidates.values())) > 1 and fold is None:
        raise ValueError('This local time occurred twice; specify fold=0 (first) or fold=1 (second)')
    return candidates[fold if fold is not None else min(candidates)]


def jd_ut(utc: datetime) -> float:
    utc = utc.astimezone(UTC)
    # UTC -> UT1 rather than silently treating UTC as UT1.
    return swe.utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute,
                         utc.second + utc.microsecond / 1e6, swe.GREG_CAL)[1]


def position(lon: float) -> dict:
    lon %= 360
    return {'longitude': round(lon, 8), 'sign': SIGNS[int(lon // 30)], 'degree_in_sign': round(lon % 30, 8)}


def planets_at(utc: datetime) -> dict:
    result = {}
    with LOCK:
        jd = jd_ut(utc)
        for name, body in BODIES.items():
            values, flags, warning = swe.calc_ut(jd, body, swe.FLG_MOSEPH | swe.FLG_SPEED)
            if not flags & swe.FLG_MOSEPH:
                raise RuntimeError('Unexpected ephemeris backend')
            if warning:
                raise ValueError('Ephemeris reported a calculation warning; verify supported inputs')
            result[name] = {**position(values[0]), 'latitude': round(values[1], 8),
                            'distance_au': round(values[2], 8),
                            'longitude_speed_deg_per_day': round(values[3], 8),
                            'retrograde': values[3] < 0}
    return result


def house_of(lon: float, cusps: list[float]) -> int:
    # Longitude-based zodiacal house placement, not 3-D mundane placement.
    for i, start in enumerate(cusps):
        width = (cusps[(i + 1) % 12] - start) % 360
        if (lon - start) % 360 < width:
            return i + 1
    raise ValueError('Could not determine house placement')


def aspects(left: dict, right: dict | None = None, orb: float = 6) -> list:
    pairs = combinations(left.items(), 2) if right is None else product(left.items(), right.items())
    result = []
    for (a, pa), (b, pb) in pairs:
        sep = abs((pa['longitude'] - pb['longitude'] + 180) % 360 - 180)
        for name, angle in ASPECTS.items():
            delta = abs(sep - angle)
            if delta <= orb:
                result.append({'body_a': a, 'body_b': b, 'aspect': name, 'angle': angle,
                               'separation': round(sep, 6), 'orb': round(delta, 6)})
    return sorted(result, key=lambda a: a['orb'])


def metadata(chart_type: str) -> dict:
    return {'schema_version': 'maya-chart-1.0', 'engine_version': '1.0.0', 'chart_type': chart_type,
            'calculation_status': 'calculated', 'provenance': {
                'library': 'pysweph 2.10.3.6 (pyswisseph community fork)', 'swiss_ephemeris_version': swe.version,
                'ephemeris': 'Moshier analytical ephemeris (explicit; no JPL/Swiss data files)',
                'zodiac': 'tropical', 'frame': 'geocentric apparent ecliptic of date',
                'calendar': 'proleptic Gregorian', 'source': SOURCE,
                'license': 'AGPL-3.0-or-later', 'house_placement': 'ecliptic longitude between cusps'},
            'interpretation_notice': 'Astronomical positions are calculated. Astrology is interpretive, not evidence of feelings or future events.'}


def day_samples(birth: BirthData) -> list[datetime]:
    # Include both folds and skip nonexistent wall times; no invented noon chart.
    tz = ZoneInfo(birth.timezone)
    start = datetime.combine(birth.birth_date, time.min)
    values = set()
    for i in range(24 * 12):
        wall = start + timedelta(minutes=5 * i)
        for f in (0, 1):
            utc = wall.replace(tzinfo=tz, fold=f).astimezone(UTC)
            if utc.astimezone(tz).replace(tzinfo=None) == wall:
                values.add(utc)
    last = start + timedelta(days=1) - timedelta(microseconds=1)
    for f in (0, 1):
        utc = last.replace(tzinfo=tz, fold=f).astimezone(UTC)
        if utc.astimezone(tz).replace(tzinfo=None) == last:
            values.add(utc)
    if not values:
        raise ValueError('This calendar date did not exist in the supplied timezone')
    return sorted(values)


def calculate_natal(birth: BirthData) -> dict:
    result = metadata('natal')
    unknown = birth.birth_time is None
    result.update({'input': birth.model_dump(mode='json'), 'time_accuracy': 'unknown' if unknown else birth.time_accuracy,
                   'planets': {}, 'angles': None, 'house_cusps': None, 'aspects': [], 'warnings': []})
    if unknown:
        samples = [planets_at(t) for t in day_samples(birth)]
        ranges = {}
        for name in BODIES:
            origin = samples[0][name]['longitude']
            offsets = [(row[name]['longitude'] - origin + 180) % 360 - 180 for row in samples]
            signs = list(dict.fromkeys(row[name]['sign'] for row in samples))
            ranges[name] = {'possible_signs_sampled': signs, 'reference_longitude': origin,
                            'offset_min_deg': min(offsets), 'offset_max_deg': max(offsets),
                            'retrograde_states_sampled': sorted(set(row[name]['retrograde'] for row in samples))}
        result['planet_daily_ranges'] = ranges
        result['warnings'] = ['Birth time unknown: no exact natal positions, angles, houses or aspects are supplied.',
                              'Daily ranges are sampled every five minutes, not rigorous mathematical bounds; brief sign/station transitions can be missed.']
        return result
    utc = local_to_utc(datetime.combine(birth.birth_date, birth.birth_time), birth.timezone, birth.fold)
    result['timestamp_utc'] = utc.isoformat()
    result['planets'] = planets_at(utc)
    if birth.time_accuracy == 'approximate':
        result['warnings'].append('Positions use an approximate birth time. Angles and houses are withheld; planetary positions/aspects remain provisional, especially the Moon.')
    else:
        code = {'placidus': b'P', 'whole_sign': b'W', 'equal': b'E'}[birth.house_system]
        try:
            with LOCK:
                cusps, axes = swe.houses_ex(jd_ut(utc), birth.latitude, birth.longitude, code)
            result['house_system'] = birth.house_system
            # pysweph preserves the C library's unused index 0 (unlike pyswisseph).
            result['house_cusps'] = [float(x) for x in cusps[1:]]
            result['angles'] = {'ASC': position(axes[0]), 'MC': position(axes[1]),
                                'DSC': position(axes[0] + 180), 'IC': position(axes[1] + 180)}
            for planet in result['planets'].values():
                planet['house'] = house_of(planet['longitude'], result['house_cusps'])
        except swe.Error:
            result['warnings'].append('Requested house system is undefined at this latitude/time. No substitute house system or angles were silently returned.')
    result['aspects'] = aspects(result['planets'])
    result['aspect_orb_degrees'] = 6
    return result


def chart_points(chart: dict) -> dict:
    return {**chart['planets'], **(chart['angles'] or {})}


def calculate_synastry(person_a: BirthData, person_b: BirthData) -> dict:
    a, b = calculate_natal(person_a), calculate_natal(person_b)
    result = {**metadata('synastry'), 'person_a': a, 'person_b': b,
              'cross_aspects': [], 'house_overlays': {}, 'warnings': [], 'aspect_orb_degrees': 6}
    if a['planets'] and b['planets']:
        result['cross_aspects'] = aspects(chart_points(a), chart_points(b))
    else:
        result['warnings'].append('Exact cross-aspects omitted because at least one birth time is unknown.')
    for key, source, target in [('a_in_b', a, b), ('b_in_a', b, a)]:
        if source['time_accuracy'] == target['time_accuracy'] == 'exact' and target['house_cusps']:
            result['house_overlays'][key] = {name: house_of(p['longitude'], target['house_cusps']) for name, p in source['planets'].items()}
    result['warnings'].extend(a['warnings'] + b['warnings'])
    return result


def calculate_transits(birth: BirthData, transit_timestamp: datetime) -> dict:
    if transit_timestamp.tzinfo is None or transit_timestamp.utcoffset() is None:
        raise ValueError('transit_timestamp must include a UTC offset or Z')
    utc = transit_timestamp.astimezone(UTC)
    if not 1800 <= utc.year <= 2399:
        raise ValueError('Supported transit years: 1800–2399')
    natal = calculate_natal(birth)
    planets = planets_at(utc)
    return {**metadata('transit'), 'natal': natal, 'transit_timestamp_utc': utc.isoformat(),
            'transit_planets': planets, 'natal_to_transit_aspects': aspects(chart_points(natal), planets, orb=3) if natal['planets'] else [],
            'aspect_orb_degrees': 3, 'warnings': natal['warnings']}
