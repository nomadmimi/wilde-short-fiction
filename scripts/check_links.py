"""List archive_url links in data.csv that no longer resolve.

Run from the repository root: python scripts/check_links.py
Subscription archives (British Newspaper Archive, Newspapers.com) often
refuse automated requests with 401/403/429; those count as reachable.
Only links that are gone (404/410), failing (5xx) or unreachable are
reported, and the script exits with an error if there are any.
"""
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from frictionless import Package

from validate import ROOT

BLOCKED = {401, 403, 429}
HEADERS = {'User-Agent': 'Mozilla/5.0 (wildeshortfiction.com link check)'}


def status(url: str) -> str | None:
    """Return a description of the problem, or None if the link resolves."""
    for method in ('HEAD', 'GET'):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS, method=method), timeout=30):
                return None
        except urllib.error.HTTPError as error:
            if error.code in BLOCKED:
                return None
            if method == 'HEAD' and error.code in (405, 501):
                continue
            return f'HTTP {error.code}'
        except Exception as error:
            return type(error).__name__
    return None


def main() -> int:
    rows = Package(ROOT / 'datapackage.json').get_resource('reviews').read_rows()
    links = [(row['id'], row['archive_url']) for row in rows if row['archive_url']]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda link: status(link[1]), links))

    dead = [(id, url, problem) for (id, url), problem in zip(links, results) if problem]
    lines = [f'Checked {len(links)} archive links: {len(dead)} broken.']
    if dead:
        lines += ['', '| id | problem | archive_url |', '| --- | --- | --- |']
        lines += [f'| {id} | {problem} | {url} |' for id, url, problem in dead]

    print('\n'.join(lines))
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a') as file:
            file.write('\n'.join(lines) + '\n')

    return 1 if dead else 0


if __name__ == '__main__':
    sys.exit(main())
