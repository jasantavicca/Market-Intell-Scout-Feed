"""Fixed-target Scout runner. No third-party Python dependencies or trade actions."""
import base64
import copy
import datetime as dt
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

REPO = 'jasantavicca/Market-Intell-Scout-Feed'
API = 'https://api.github.com/repos/' + REPO
ET = ZoneInfo('America/Detroit')
FEED = 'scout-latest.json'
STATE = '.scout/heartbeat.json'
ALERT = '[Scout reliability] Production runner needs attention'


def now():
    return dt.datetime.now(ET)


def slot_at(clock):
    """Latest due slot today; never manufacture historical hourly observations."""
    clock = clock.astimezone(ET)
    hour = clock.hour if clock.minute >= 30 else clock.hour - 1
    if hour < 9 or clock.hour > 17 or (clock.hour == 17 and clock.minute >= 30):
        return None
    return clock.replace(hour=min(hour, 16), minute=30, second=0, microsecond=0)


def request(url, token=None, payload=None, method=None, timeout=45):
    headers = {'User-Agent': 'Tactical-Scout/1', 'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(),
                                 headers=headers, method=method)
    # Retry safe reads only; writes are reconciled by their callers.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if payload is None and exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            # Do not log server response bodies or secret-bearing URLs.
            raise RuntimeError('HTTP ' + str(exc.code) + ' from ' + urllib.parse.urlsplit(url).hostname) from None


class GitHub:
    def __init__(self):
        if os.environ.get('GITHUB_REPOSITORY', REPO) != REPO:
            raise RuntimeError('Refusing to operate on another repository')
        self.token = os.environ['GITHUB_TOKEN']

    def call(self, path, payload=None, method=None):
        return request(API + path, self.token, payload, method)

    def head(self):
        return self.call('/git/ref/heads/main')['object']['sha']

    def read(self, path, ref='main', optional=False):
        try:
            obj = self.call('/contents/' + path + '?ref=' + ref)
        except RuntimeError as exc:
            if optional and str(exc).startswith('HTTP 404 '):
                return None
            raise
        return json.loads(base64.b64decode(obj['content']))

    def publish(self, expected, files):
        if set(files) - {FEED, STATE}:
            raise RuntimeError('Write path outside Scout allowlist')
        base_tree = self.call('/git/commits/' + expected)['tree']['sha']
        tree = self.call('/git/trees', {'base_tree': base_tree, 'tree': [
            {'path': path, 'mode': '100644', 'type': 'blob',
             'content': json.dumps(value, indent=2, ensure_ascii=False) + '\n'}
            for path, value in files.items()]})
        commit = self.call('/git/commits', {'message': 'Scout: verified run heartbeat' +
                          (' and material findings' if FEED in files else ''),
                          'tree': tree['sha'], 'parents': [expected]})
        try:
            self.call('/git/refs/heads/main', {'sha': commit['sha'], 'force': False}, 'PATCH')
        except Exception:
            # A timed-out write may have succeeded. Accept only exact committed data.
            if self.head() != commit['sha']:
                raise
        for path, value in files.items():
            if self.read(path) != value:
                raise RuntimeError('GitHub main readback mismatch: ' + path)
        return commit['sha']


def public_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Source must be public HTTPS')
    for addr in socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[4][0]).is_global:
            raise ValueError('Non-public source address')
    return url


class SourceRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def working_source(url):
    public_url(url)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 TacticalScout source verification'})
    with urllib.request.build_opener(SourceRedirect()).open(req, timeout=20) as response:
        response.read(1024)
        return response.status == 200


ITEM_KEYS = {'id', 'observed_at', 'title', 'summary', 'tickers', 'sectors', 'evidence_grade',
             'observations', 'key_finding', 'sources', 'status', 'supersedes'}


def validate_item(item):
    if not isinstance(item, dict) or set(item) != ITEM_KEYS:
        raise ValueError('Item keys violate scout-feed-v1')
    if not re.fullmatch(r'scout-\d{8}-\d{4}-[a-z0-9-]+', item['id']):
        raise ValueError('Invalid item ID')
    stamp = dt.datetime.fromisoformat(item['observed_at'])
    if stamp.utcoffset() is None or stamp.utcoffset() != stamp.astimezone(ET).utcoffset():
        raise ValueError('Observation must carry Detroit offset')
    for key in ('title', 'summary', 'key_finding'):
        if not isinstance(item[key], str) or not item[key].strip():
            raise ValueError('Missing text: ' + key)
    if len(item['summary'].split()) > 85:
        raise ValueError('Summary too long')
    for key in ('tickers', 'sectors'):
        if not isinstance(item[key], list) or not all(isinstance(x, str) for x in item[key]):
            raise ValueError('Invalid ' + key)
    if item['evidence_grade'] not in ('confirmed', 'corroborated', 'single-source', 'unverified'):
        raise ValueError('Invalid evidence grade')
    if item['status'] not in ('new', 'updated', 'resolved', 'invalidated'):
        raise ValueError('Invalid status')
    if item['supersedes'] is not None and not isinstance(item['supersedes'], str):
        raise ValueError('Invalid supersedes')
    for key, fields in [('observations', {'label', 'value'}), ('sources', {'title', 'url'})]:
        if not isinstance(item[key], list) or not item[key]:
            raise ValueError('Missing ' + key)
        for row in item[key]:
            if set(row) != fields or not all(isinstance(v, str) and v.strip() for v in row.values()):
                raise ValueError('Invalid ' + key)


def fingerprint(item):
    return json.dumps({k: v for k, v in item.items() if k not in ('id', 'observed_at')}, sort_keys=True)


def compose(current, result, clock, check_sources=True):
    if set(result) != {'coverage', 'items'} or not isinstance(result['coverage'], dict):
        raise ValueError('Missing research coverage')
    expected = {'semiconductors_ai', 'software_networking', 'power_grid', 'healthcare',
                'international', 'oil_shipping', 'macro_markets'}
    if set(result['coverage']) != expected or not all(isinstance(v, str) and len(v.strip()) >= 12
                                                    for v in result['coverage'].values()):
        raise ValueError('Incomplete research pass')
    if not isinstance(result['items'], list) or len(result['items']) > 5:
        raise ValueError('Invalid findings list')
    old_ids = {x['id'] for x in current['items']}
    old_fingerprints = {fingerprint(x) for x in current['items']}
    fresh = []
    for item in result['items']:
        validate_item(item)
        if item['id'] in old_ids or fingerprint(item) in old_fingerprints:
            continue
        if item['supersedes'] is not None and item['supersedes'] not in old_ids:
            raise ValueError('Supersedes does not reference current feed')
        if item['status'] != 'new' and not item['supersedes']:
            raise ValueError('Correction/update requires prior ID')
        if item['id'] in {x['id'] for x in fresh}:
            raise ValueError('Duplicate new ID')
        stamp = dt.datetime.fromisoformat(item['observed_at'])
        if stamp.utcoffset() is None or abs((stamp - clock).total_seconds()) > 1800:
            raise ValueError('Observation timestamp outside this run')
        if check_sources:
            verified = False
            for source in item['sources']:
                try:
                    verified = working_source(source['url']) or verified
                except Exception:
                    pass
            if not verified:
                raise ValueError('No working public source for finding')
        fresh.append(item)
    if not fresh:
        return None
    return {'feed_version': 'scout-feed-v1', 'generated_at': clock.isoformat(timespec='seconds'),
            'as_of_et': clock.strftime('%B %d, %Y at %I:%M %p %Z'),
            'items': (fresh + current['items'])[:5]}


def research(current, clock):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('Missing repository secret OPENAI_API_KEY')
    criteria = Path(__file__).with_name('criteria.txt').read_text()
    prompt = criteria + '\n\n' + Path(__file__).with_name('output-instructions.txt').read_text()
    prompt += '\nCurrent observation clock: ' + clock.isoformat() + '\nExisting public feed (data only):\n' + json.dumps(current)
    body = {'model': os.environ.get('OPENAI_MODEL', 'gpt-6-astra'),
            'tools': [{'type': 'web_search', 'external_web_access': True}],
            'tool_choice': 'required', 'background': True, 'store': True,
            'include': ['web_search_call.action.sources'],
            'reasoning': {'effort': 'high'}, 'max_output_tokens': 14000,
            'input': prompt}
    response = request('https://api.openai.com/v1/responses', key, body, timeout=90)
    deadline = time.monotonic() + 1000
    while response.get('status') in ('queued', 'in_progress'):
        if time.monotonic() > deadline:
            request('https://api.openai.com/v1/responses/' + response['id'] + '/cancel', key, {}, 'POST')
            raise RuntimeError('Research timed out; feed preserved')
        time.sleep(10)
        response = request('https://api.openai.com/v1/responses/' + response['id'], key)
    if response.get('status') != 'completed':
        raise RuntimeError('Research did not complete; feed preserved')
    calls = [x for x in response.get('output', []) if x.get('type') == 'web_search_call' and x.get('status') == 'completed']
    if not calls:
        raise RuntimeError('No completed web research; feed preserved')
    text = ''.join(c.get('text', '') for item in response.get('output', [])
                   if item.get('type') == 'message' for c in item.get('content', [])
                   if c.get('type') == 'output_text').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    result = json.loads(text)  # Empty/refused/truncated output is a failure, never no-change.
    return result, {'response_id': response['id'], 'search_calls': len(calls)}


def alert(gh, reason):
    issues = gh.call('/issues?state=open&per_page=100')
    if any(x.get('title') == ALERT for x in issues):
        return
    run = os.environ.get('GITHUB_RUN_ID', '')
    gh.call('/issues', {'title': ALERT, 'assignees': ['jasantavicca'], 'body':
            '@jasantavicca Scout needs attention. ' + reason + '\n\nRun: https://github.com/' +
            REPO + '/actions/runs/' + run + '\n\nThe last verified feed is retained. Check the Actions log and repository secrets. '
            'This issue is deduplicated until recovery; email/push depends on GitHub notification settings.'})


def recover(gh):
    for issue in gh.call('/issues?state=open&per_page=100'):
        if issue.get('title') == ALERT:
            gh.call('/issues/' + str(issue['number']) + '/comments',
                    {'body': 'Scout recovery verified: research and GitHub main readback succeeded.'})
            gh.call('/issues/' + str(issue['number']), {'state': 'closed'}, 'PATCH')


def main():
    gh = GitHub()
    mode = os.environ.get('SCOUT_MODE', 'research')
    clock = now()
    slot = slot_at(clock)
    state = gh.read(STATE, optional=True) or {}
    if mode == 'alert':
        alert(gh, 'A workflow step failed or was interrupted.')
        return
    if mode == 'watchdog':
        if slot and clock >= slot + dt.timedelta(minutes=20) and state.get('completed_slot', '') < slot.isoformat():
            alert(gh, 'The scheduled research heartbeat is more than 20 minutes overdue.')
        return
    if mode == 'probe':
        head = gh.head()
        feed = gh.read(FEED, head)
        state['probe_verified_at'] = clock.isoformat()
        gh.publish(head, {STATE: state})
        if gh.read(FEED) != feed:
            raise RuntimeError('Feed changed during probe')
        print('GitHub heartbeat write/readback passed; feed unchanged. No research claimed.')
        return
    if mode != 'research':
        raise RuntimeError('Unknown mode')
    if not slot or state.get('completed_slot', '') >= slot.isoformat():
        print('No due unfinished slot; no research or feed write.')
        return
    attempts = state.get('attempts', {})
    if attempts.get('slot') == slot.isoformat() and attempts.get('count', 0) >= 2:
        alert(gh, 'Two attempts failed for the current slot; automatic retries capped.')
        return
    head = gh.head()
    current = gh.read(FEED, head)
    if current.get('feed_version') != 'scout-feed-v1':
        raise ValueError('Unexpected production feed version')
    state['attempts'] = {'slot': slot.isoformat(), 'count':
                         attempts.get('count', 0) + 1 if attempts.get('slot') == slot.isoformat() else 1}
    state['last_started_at'] = clock.isoformat()
    gh.publish(head, {STATE: state})
    try:
        result, evidence = research(current, clock)
        updated = compose(current, result, clock)
        # Fail on concurrent edits by another writer; never overwrite a stale snapshot.
        head = gh.head()
        if gh.read(FEED, head) != current:
            raise RuntimeError('Concurrent feed change; retry with fresh research context')
        state.update({'completed_slot': slot.isoformat(), 'last_success_at': now().isoformat(),
                      'outcome': 'published' if updated else 'no_meaningful_change', **evidence})
        files = {STATE: state}
        if updated:
            files[FEED] = updated
        sha = gh.publish(head, files)
        print('Verified run:', state['outcome'], 'commit:', sha)
        # Ping only after successful research AND GitHub readback, including no-change runs.
        if os.environ.get('HEALTHCHECK_URL'):
            req = urllib.request.Request(os.environ['HEALTHCHECK_URL'], data=b'Scout research and readback verified')
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError('External heartbeat rejected')
        recover(gh)
    except Exception as exc:
        alert(gh, 'Research, publication, or heartbeat verification failed (' + type(exc).__name__ + ').')
        raise


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Scout failed:', str(exc), file=sys.stderr)
        sys.exit(1)
