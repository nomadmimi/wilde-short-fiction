"""Look for new publications about Wilde's short fiction and file them in Zotero for review.

Searches OpenAlex and Crossref with the queries in bibliography.config.json and adds
what is new to the "To review" sub-collection of the main Zotero collection. Nothing
reaches bibliography.json until a person moves an item into the main collection.
To reject an item, move it to the "Rejected" sub-collection (deleting it would let it
come back); the script never proposes anything already in the main, review or rejected
collection. Run from the repository root with ZOTERO_API_KEY set (OPENALEX_API_KEY is
optional):

    python scripts/discover_publications.py [--since YYYY-MM-DD] [--dry-run]

--since overrides discovery.lookbackDays (use 1888-01-01 once to search all years).
--dry-run lists what would be added and changes nothing.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from bibliography_lib import ZoteroError, clean_doi, fail, load_config, notice, work_key, zotero_from_config

# kind -> (Zotero item type, field for the container title, whether the type has a native DOI field)
ZOTERO_TYPES = {
    'article': ('journalArticle', 'publicationTitle', True),
    'chapter': ('bookSection', 'bookTitle', False),
    'book': ('book', None, False),
    'thesis': ('thesis', None, False),
    'conference': ('conferencePaper', 'proceedingsTitle', True),
}
OPENALEX_KINDS = {'article': 'article', 'review': 'article', 'book-chapter': 'chapter', 'book': 'book',
                  'dissertation': 'thesis'}
CROSSREF_KINDS = {'journal-article': 'article', 'book-chapter': 'chapter', 'book': 'book', 'monograph': 'book',
                  'edited-book': 'book', 'reference-book': 'book', 'proceedings-article': 'conference',
                  'dissertation': 'thesis'}


def get_json(url, params):
    request = urllib.request.Request(f'{url}?{urllib.parse.urlencode(params)}',
                                     headers={'User-Agent': 'wilde-short-fiction-bibliography/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def split_name(full):
    parts = full.split()
    return (' '.join(parts[:-1]), parts[-1]) if len(parts) > 1 else ('', full)


def candidate(kind, source, source_id, title, creators, year, doi=None, container=None, volume=None, issue=None,
              pages=None, publisher=None, url=None, abstract=None):
    return {'kind': kind, 'source': source, 'source_id': source_id, 'title': re.sub(r'\s+', ' ', title or '').strip(),
            'creators': creators, 'year': year, 'DOI': clean_doi(doi), 'container': container, 'volume': volume,
            'issue': issue, 'pages': pages, 'publisher': publisher, 'url': url, 'abstract': abstract}


def abstract_from_index(index):
    if not index:
        return None
    words = sorted((position, word) for word, positions in index.items() for position in positions)
    return ' '.join(word for _, word in words)


def search_openalex(query, since, limit):
    params = {'filter': f'title_and_abstract.search:{query.replace(",", " ")},from_publication_date:{since}',
              'per-page': min(limit, 200),
              'select': 'id,doi,title,publication_year,type,authorships,primary_location,biblio,'
                        'abstract_inverted_index'}
    if os.environ.get('OPENALEX_API_KEY'):
        params['api_key'] = os.environ['OPENALEX_API_KEY']
    for work in get_json('https://api.openalex.org/works', params).get('results', []):
        kind = OPENALEX_KINDS.get(work.get('type'))
        if not kind or not work.get('title'):
            continue
        biblio, location = work.get('biblio') or {}, work.get('primary_location') or {}
        first, last = biblio.get('first_page'), biblio.get('last_page')
        yield candidate(
            kind, 'OpenAlex', work['id'], work['title'],
            [split_name(a['author']['display_name']) for a in work.get('authorships', [])],
            work.get('publication_year'), work.get('doi'), (location.get('source') or {}).get('display_name'),
            biblio.get('volume'), biblio.get('issue'), f'{first}-{last}' if first and last else first,
            None, location.get('landing_page_url'), abstract_from_index(work.get('abstract_inverted_index')))


def search_crossref(query, since, limit, mailto):
    params = {'query.bibliographic': query.replace('"', ''), 'filter': f'from-pub-date:{since}', 'rows': min(limit, 100),
              'select': 'DOI,title,author,issued,type,container-title,volume,issue,page,publisher,URL,abstract'}
    if mailto:
        params['mailto'] = mailto
    for work in get_json('https://api.crossref.org/works', params)['message'].get('items', []):
        kind = CROSSREF_KINDS.get(work.get('type'))
        if not kind or not work.get('title'):
            continue
        parts = (work.get('issued') or {}).get('date-parts') or [[None]]
        yield candidate(
            kind, 'Crossref', work['DOI'], work['title'][0],
            [(a.get('given', ''), a.get('family') or a.get('name', '')) for a in work.get('author', [])],
            parts[0][0], work['DOI'], (work.get('container-title') or [None])[0], work.get('volume'), work.get('issue'),
            work.get('page'), work.get('publisher'), work.get('URL'),
            re.sub(r'<[^>]+>', '', work.get('abstract') or '') or None)


def as_csl(found):
    """The few CSL fields work_key() needs, so a candidate can be compared with what Zotero already holds."""
    return {'DOI': found['DOI'], 'title': found['title'], 'issued': {'date-parts': [[found['year']]]},
            'author': [{'family': found['creators'][0][1]}] if found['creators'] else []}


def to_zotero(found, review_key, tag):
    item_type, container_field, has_doi = ZOTERO_TYPES[found['kind']]
    item = {'itemType': item_type, 'title': found['title'], 'date': str(found['year'] or ''),
            'creators': [{'creatorType': 'author', 'firstName': given, 'lastName': family}
                         for given, family in found['creators']],
            'url': found['url'] or '', 'pages': found['pages'] or '', 'abstractNote': found['abstract'] or '',
            'collections': [review_key], 'tags': [{'tag': tag}]}
    if container_field:
        item[container_field] = found['container'] or ''
    if item_type != 'thesis':
        item['volume'] = found['volume'] or ''
    if item_type == 'journalArticle':
        item['issue'] = found['issue'] or ''
    if item_type in ('book', 'bookSection', 'conferencePaper', 'thesis'):
        item['publisher' if item_type != 'thesis' else 'university'] = found['publisher'] or ''
    if found['DOI']:
        if has_doi:
            item['DOI'] = found['DOI']
        else:
            item['extra'] = f'DOI: {found["DOI"]}'
    return {k: v for k, v in item.items() if v not in ('', None)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--since', metavar='YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    config = load_config()
    settings = config['discovery']
    zotero = zotero_from_config(config)
    if zotero is None:
        return 0

    since = args.since or (datetime.date.today() - datetime.timedelta(days=settings['lookbackDays'])).isoformat()
    names = config['zotero']
    try:
        main_key = zotero.find_collection(names['collection'])
        if main_key is None:
            fail(f'No top-level Zotero collection named {names["collection"]!r}. '
                 'Fix zotero.collection in bibliography.config.json.')
        # A dry run must not change Zotero, so it only looks for the sub-collections and never creates them.
        sub = zotero.find_collection if args.dry_run else zotero.ensure_subcollection
        review_key = sub(names['reviewSubcollection'], main_key)
        rejected_key = sub(names['rejectedSubcollection'], main_key)
        known = {work_key(i) for key in (main_key, review_key, rejected_key) if key for i in zotero.csl_items(key)}
    except ZoteroError as error:
        fail(str(error))

    mention = [re.compile(p, re.I) for p in settings['mustMention']]
    mailto = config.get('contactEmail')
    searches = [('OpenAlex', q, lambda q=q: search_openalex(q, since, settings['perQueryLimit']))
                for q in settings['queries']]
    searches += [('Crossref', q, lambda q=q: search_crossref(q, since, settings['perQueryLimit'], mailto))
                 for q in settings['queries']]

    fresh, failed = [], {'OpenAlex': 0, 'Crossref': 0}
    for source, query, run in searches:
        try:
            for found in run():
                text = ' '.join(filter(None, [found['title'], found['container'], found['abstract']]))
                key = work_key(as_csl(found))
                if key in known or not all(p.search(text) for p in mention):
                    continue
                known.add(key)
                fresh.append(found)
        except (urllib.error.URLError, ValueError, KeyError) as error:
            failed[source] += 1
            print(f'warning: {source} "{query}" failed: {error}', file=sys.stderr)
    # Fail the job only when a whole source was unreachable; one flaky query is not worth a red run.
    outage = any(n == len(settings['queries']) for n in failed.values())

    if len(fresh) > settings['maxNewPerRun']:
        notice(f'{len(fresh)} new candidates; adding the first {settings["maxNewPerRun"]}, the rest next run.')
        fresh = fresh[:settings['maxNewPerRun']]

    lines = [f'- {f["title"]} ({f["year"]}) [{f["source"]}] {f["DOI"] or f["url"] or ""}'.rstrip() for f in fresh]
    print(f'{len(fresh)} new candidate(s) since {since}:' + ('\n' + '\n'.join(lines) if lines else ''))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            heading = (f'{len(fresh)} candidate(s) found (dry run: nothing was added to Zotero)' if args.dry_run
                       else f'{len(fresh)} new candidate(s) added to "{names["reviewSubcollection"]}"')
            summary.write(f'### {heading}\n\n' + '\n'.join(lines) + '\n')

    if fresh and not args.dry_run:
        try:
            zotero.create_items([to_zotero(f, review_key, settings['tag']) for f in fresh])
        except ZoteroError as error:
            fail(str(error))
    return 1 if outage else 0


if __name__ == '__main__':
    sys.exit(main())
