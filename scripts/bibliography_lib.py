"""Shared code for the bibliography pipeline (export and discovery).

Every setting lives in bibliography.config.json at the repository root; nothing
below hard-codes a collection name, a path or a query. The only secrets are the
environment variables ZOTERO_API_KEY (required) and OPENALEX_API_KEY (optional).
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'bibliography.config.json'
ZOTERO_API = 'https://api.zotero.org'
PAGE = 100  # largest page the Zotero API serves for csljson
STOP_WORDS = {'a', 'an', 'the', 'of', 'on', 'in', 'and', 'to', 'for', 'de', 'la', 'le', 'les', 'el', 'der', 'die', 'das'}


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def bibliography_path(config):
    return ROOT / config['bibliography']


def dump_bibliography(items):
    """Serialise exactly as the file is stored (2-space indent, no trailing newline), so diffs stay small."""
    return json.dumps(items, indent=2, ensure_ascii=False)


def notice(message):
    print(f'::notice::{message}' if os.environ.get('GITHUB_ACTIONS') else message)


def fail(message):
    print(f'::error::{message}' if os.environ.get('GITHUB_ACTIONS') else f'error: {message}', file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Matching and ids
# ---------------------------------------------------------------------------

def plain(text):
    """Lower-case words with markup, accents and punctuation removed (any script is kept)."""
    text = unicodedata.normalize('NFKD', re.sub(r'<[^>]+>', '', text or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[\W_]+', ' ', text.lower()).strip()


def clean_doi(doi):
    return re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', (doi or '').strip(), flags=re.I).lower()


def first_creator(item):
    who = (item.get('author') or item.get('editor') or [{}])[0]
    return who.get('family') or who.get('literal') or ''


def year_of(item):
    parts = (item.get('issued') or {}).get('date-parts') or [[]]
    return str(parts[0][0]) if parts[0] and parts[0][0] else ''


def work_key(item):
    """Two records of the same work share this key: the DOI, else first creator + year + title."""
    doi = clean_doi(item.get('DOI'))
    if doi:
        return 'doi:' + doi
    return '|'.join((plain(first_creator(item)), year_of(item), plain(item.get('title'))))


def base_id(item):
    words = [w for w in plain(item.get('title')).split() if w not in STOP_WORDS]
    return plain(first_creator(item)).replace(' ', '') + year_of(item) + (words[0] if words else '')


# ---------------------------------------------------------------------------
# Zotero API
# ---------------------------------------------------------------------------

class ZoteroError(RuntimeError):
    pass


class Zotero:
    def __init__(self, library_type, library_id, api_key):
        self.base = f'{ZOTERO_API}/{library_type}/{library_id}'
        self.api_key = api_key

    def _call(self, method, path, params=None, body=None):
        url = self.base + path + ('?' + urllib.parse.urlencode(params) if params else '')
        headers = {'Zotero-API-Key': self.api_key, 'Zotero-API-Version': '3'}
        data = None
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
            headers['Zotero-Write-Token'] = uuid.uuid4().hex  # makes a retried POST safe
        for attempt in range(5):
            request = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = response.read()
                    time.sleep(int(response.headers.get('Backoff', 0)))
                    return (json.loads(payload) if payload else None), response.headers
            except urllib.error.HTTPError as error:
                if error.code in (429, 503) and attempt < 4:
                    time.sleep(int(error.headers.get('Retry-After', 5)))
                    continue
                # The key is only ever sent as a header, so it cannot leak through this message.
                raise ZoteroError(f'{method} {path}: HTTP {error.code} {error.read()[:200]!r}') from None

    def _paged(self, path, params):
        results, start = [], 0
        while True:
            payload, headers = self._call('GET', path, {**params, 'limit': PAGE, 'start': start})
            batch = payload.get('items', []) if isinstance(payload, dict) else payload
            results.extend(batch)
            start += PAGE
            if not batch or start >= int(headers.get('Total-Results', 0)):
                return results

    def find_collection(self, name, parent=None):
        for c in self._paged('/collections', {}):
            data = c['data']
            if data['name'] == name and (data.get('parentCollection') or None) == parent:
                return c['key']
        return None

    def ensure_subcollection(self, name, parent):
        key = self.find_collection(name, parent)
        if key:
            return key
        result, _ = self._call('POST', '/collections', body=[{'name': name, 'parentCollection': parent}])
        if result.get('failed'):
            raise ZoteroError(f'could not create collection {name!r}: {result["failed"]}')
        return result['successful']['0']['key']

    def csl_items(self, collection_key):
        """CSL-JSON for the items directly in a collection (sub-collections are not included)."""
        return self._paged(f'/collections/{collection_key}/items/top',
                           {'format': 'csljson', 'itemType': '-attachment', 'sort': 'dateAdded'})

    def create_items(self, items):
        for start in range(0, len(items), 50):  # the API accepts 50 items per request
            result, _ = self._call('POST', '/items', body=items[start:start + 50])
            if result.get('failed'):
                raise ZoteroError(f'Zotero rejected items: {result["failed"]}')


def zotero_from_config(config):
    """The Zotero client, or None when zotero.libraryId has not been filled in yet."""
    settings = config['zotero']
    if not settings.get('libraryId'):
        notice('zotero.libraryId is empty in bibliography.config.json, so there is nothing to sync yet.')
        return None
    api_key = os.environ.get('ZOTERO_API_KEY')
    if not api_key:
        fail('ZOTERO_API_KEY is not set. Add it as a repository secret (Settings > Secrets and variables > Actions).')
    return Zotero(settings['libraryType'], settings['libraryId'], api_key)
