#!/usr/bin/env python3
"""Read GitHub metadata; publish to PRIVATE Cloudflare KV, never Git or artifacts."""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

STAGES = {'Live', 'Staging', 'Development', 'Not operational', 'Unknown', 'Archived'}


def https_url(value):
    if not isinstance(value, str):
        return ''
    try:
        u = urllib.parse.urlsplit(value)
        return value if u.scheme == 'https' and u.hostname and not u.username and not u.password else ''
    except ValueError:
        return ''


def request(url, token, data=None, missing_ok=False):
    headers = {'Authorization': 'Bearer ' + token, 'User-Agent': 'calitoy-admin-inventory', 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method='PUT' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        raise RuntimeError(f'Inventory service returned HTTP {exc.code}; previous snapshot preserved') from None


def collect(token, owners, get=request):
    rows = []
    for page in range(1, 1001):
        url = 'https://api.github.com/user/repos?' + urllib.parse.urlencode({'affiliation': 'owner,collaborator,organization_member', 'per_page': 100, 'page': page, 'sort': 'full_name'})
        part = get(url, token)
        if not isinstance(part, list):
            raise RuntimeError('Repository listing was not a list')
        rows.extend(r for r in part if not owners or r['owner']['login'].lower() in owners)
        if len(part) < 100:
            return rows
    raise RuntimeError('Repository pagination did not finish; previous snapshot preserved')


def build(rows, overrides, old, allow_shrink=False):
    if not rows:
        raise RuntimeError('Refusing to replace inventory with an empty list')
    seen = {r['full_name'] for r in rows}
    previous = {r['repo'] for r in (old or {}).get('repos', [])}
    if previous - seen and not allow_shrink:
        raise RuntimeError('Repository access shrank; explicit review required before replacing snapshot')
    items = []
    for r in rows:
        name = r['full_name']
        meta = overrides.get(name, {})
        verified = meta.get('verified') is True
        stage = meta.get('stage', 'Unknown') if verified else 'Unknown'
        if stage not in STAGES:
            stage = 'Unknown'
        if r.get('archived'):
            stage = 'Archived'
        items.append({'name': r['name'], 'repo': name, 'repo_url': 'https://github.com/' + name,
                      'visibility': 'private' if r.get('private') else 'public', 'stage': stage,
                      'site': https_url(meta.get('site')) if verified else '',
                      'admin': https_url(meta.get('admin')) if verified else '',
                      'host': https_url(meta.get('host')) if verified else '',
                      'note': str(meta.get('note') or 'Deployment and admin URL have not been confirmed.')[:1200],
                      'updated_at': r.get('pushed_at'), 'verified': verified,
                      'repo_homepage_unverified': https_url(r.get('homepage')) if not (verified and meta.get('site')) else ''})
    return {'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope': 'Repositories visible to the configured token and owner filter; not proof of every app or deployment',
            'repos': sorted(items, key=lambda x: x['name'].lower())}


def main():
    names = ['INVENTORY_GITHUB_TOKEN', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'ADMIN_KV_NAMESPACE_ID']
    missing = [k for k in names if not os.getenv(k)]
    if missing:
        raise RuntimeError('Missing configuration names: ' + ', '.join(missing))
    account, namespace = os.environ['CLOUDFLARE_ACCOUNT_ID'], os.environ['ADMIN_KV_NAMESPACE_ID']
    if not all(len(v) == 32 and all(c in '0123456789abcdefABCDEF' for c in v) for v in [account, namespace]):
        raise RuntimeError('Cloudflare account and namespace IDs must be 32 hexadecimal characters')
    cf = os.environ['CLOUDFLARE_API_TOKEN']
    base = f'https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{namespace}/values/'
    old = request(base + 'inventory%3Alatest', cf, missing_ok=True)
    overrides = request(base + 'catalog%3Aoverrides', cf, missing_ok=True) or {}
    if not isinstance(overrides, dict):
        raise RuntimeError('Private catalog must be an object')
    owners = {s.strip().lower() for s in os.getenv('INVENTORY_OWNERS', 'JoS727').split(',') if s.strip()}
    payload = build(collect(os.environ['INVENTORY_GITHUB_TOKEN'], owners), overrides, old,
                    allow_shrink=os.getenv('ALLOW_INVENTORY_SHRINK') == 'true')
    # One replace after all reads and checks succeed. Never write private data to checkout.
    result = request(base + 'inventory%3Alatest', cf, json.dumps(payload).encode('utf-8'))
    if result.get('success') is not True:
        raise RuntimeError('Private inventory update was not confirmed')
    print('Private inventory updated; no repository names or URLs are logged.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid logging response bodies, tokens, URLs or repository records.
        print('Inventory refresh failed: ' + (str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
