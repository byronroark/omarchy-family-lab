"""Bounded read-only adapter; collection remains in upstream ActivityWatch watchers."""
import datetime as dt
import json
import math
import re
import urllib.parse
import urllib.request

MAX_EVENTS = 10000
MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('ActivityWatch redirects are not allowed')


def settings(config):
    if not isinstance(config, dict) or config.get('enabled') is not True:
        raise ValueError('ActivityWatch reporting is disabled')
    allowed = {'enabled', 'port', 'web_bucket', 'afk_bucket', 'window_bucket', 'browser_apps', 'acknowledge_raw_storage'}
    if set(config) - allowed or config.get('acknowledge_raw_storage') is not True:
        raise ValueError('Review ActivityWatch raw URL/title storage before enabling')
    port = config.get('port', 5600)
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Invalid local ActivityWatch port')
    for field in ('web_bucket', 'afk_bucket', 'window_bucket'):
        if not isinstance(config.get(field), str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', config[field]):
            raise ValueError('Choose explicit local ActivityWatch bucket IDs')
    apps = config.get('browser_apps')
    if not isinstance(apps, list) or not 1 <= len(apps) <= 16 or any(not isinstance(x, str) or not 1 <= len(x) <= 80 or not x.isprintable() for x in apps):
        raise ValueError('Choose exact browser app identifiers from the window watcher')
    return config


def get_json(path, port):
    # Fixed loopback host; never use an environment proxy, follow redirects or write.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open('http://127.0.0.1:' + str(port) + '/api/0/' + path, timeout=5) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('ActivityWatch response too large; choose a shorter period')
    return json.loads(raw)


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('ActivityWatch timestamps need timezones')
    return result.timestamp()


def intervals(events, lo, hi, kind):
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError('ActivityWatch event limit reached')
    result = []
    for event in events:
        duration = event['duration']
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 <= duration <= 31 * 86400:
            raise ValueError('Invalid ActivityWatch duration')
        start = timestamp(event['timestamp'])
        a, b = max(lo, start), min(hi, start + duration)
        if a >= b:
            continue
        data = event['data']
        if not isinstance(data, dict):
            raise ValueError('Invalid watcher data')
        if kind == 'afk':
            if data.get('status') not in ('afk', 'not-afk'):
                raise ValueError('Unsupported idle watcher schema')
            value = data['status']
        elif kind == 'window':
            value = data.get('app')
            if not isinstance(value, str) or not 1 <= len(value) <= 120 or not value.isprintable():
                raise ValueError('Unsupported window watcher app identifier')
        else:
            value = None
            # Missing private-mode metadata is unknown, not assumed public.
            if data.get('incognito') is False:
                url = data.get('url', '')
                if not isinstance(url, str) or len(url) > 16384:
                    raise ValueError('Invalid browser URL')
                parsed = urllib.parse.urlsplit(url)
                if parsed.scheme in ('http', 'https') and parsed.hostname and parsed.username is None and parsed.password is None:
                    host = parsed.hostname.rstrip('.').encode('idna').decode().lower()
                    if len(host) <= 253 and re.fullmatch(r'[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?', host):
                        value = host
        result.append((a, b, value))
    result.sort(key=lambda row: (row[0], row[1]))
    for before, after in zip(result, result[1:]):
        if after[0] < before[1]:
            raise ValueError('Overlapping watcher events: cannot safely allocate time')
    return result


def normalize(web, afk, windows, lo, hi, browser_apps):
    streams = [intervals(web, lo, hi, 'web'), intervals(afk, lo, hi, 'afk'), intervals(windows, lo, hi, 'window')]
    points = sorted({point for stream in streams for row in stream for point in row[:2]})
    cursors, rows = [0, 0, 0], []
    iso = lambda seconds: dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat()
    for a, b in zip(points, points[1:]):
        values = []
        for i, stream in enumerate(streams):
            while cursors[i] < len(stream) and stream[cursors[i]][1] <= a:
                cursors[i] += 1
            row = stream[cursors[i]] if cursors[i] < len(stream) else None
            values.append(row[2] if row and row[0] <= a and b <= row[1] else None)
        domain, active, app = values
        if active != 'not-afk' or not app:
            continue
        if app not in browser_apps:
            domain = None
        if rows and rows[-1]['end'] == iso(a) and rows[-1]['app'] == app and rows[-1]['domain'] == domain:
            rows[-1]['end'] = iso(b)
        else:
            rows.append({'start': iso(a), 'end': iso(b), 'app': app, 'domain': domain, 'category': 'Uncategorized'})
    if len(rows) > MAX_EVENTS:
        raise ValueError('Too many activity intervals for one report')
    return {'schema': 1, 'coverage': 'ActivityWatch active window + non-idle intersection; browser domains only; gaps unknown', 'observations': rows}


def collect(config, lo, hi, fetch=get_json):
    config = settings(config)
    port = config.get('port', 5600)
    if not 0 < hi - lo <= 31 * 86400:
        raise ValueError('Choose at most 31 UTC days')
    metadata = fetch('buckets/', port)
    if not isinstance(metadata, dict):
        raise ValueError('Invalid ActivityWatch buckets')
    streams = []
    for field, kind in [('web_bucket', 'web.tab.current'), ('afk_bucket', 'afkstatus'), ('window_bucket', 'currentwindow')]:
        bucket = config[field]
        if metadata.get(bucket, {}).get('type') != kind:
            raise ValueError('Selected ActivityWatch bucket has an unsupported type: ' + field)
        # Include events starting before midnight; very long events outside the
        # bounded lookback stay unknown rather than being fabricated.
        start = dt.datetime.fromtimestamp(lo - 86400, dt.timezone.utc).isoformat()
        end = dt.datetime.fromtimestamp(hi, dt.timezone.utc).isoformat()
        query = urllib.parse.urlencode({'start': start, 'end': end, 'limit': MAX_EVENTS + 1})
        events = fetch('buckets/' + urllib.parse.quote(bucket, safe='') + '/events?' + query, port)
        if not isinstance(events, list) or len(events) > MAX_EVENTS:
            raise ValueError('ActivityWatch event limit reached; use a shorter range')
        streams.append(events)
    return normalize(*streams, lo, hi, config['browser_apps'])
