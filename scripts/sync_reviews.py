"""Copy the published reviews (data.csv) into the "Reception reviews" collection of the Zotero group.

data.csv is the master copy; the Zotero collection is derived from it, so correct records at the
source, not in Zotero. Each review becomes a Newspaper Article whose URL is its page on the website
(siteUrl + id); that URL is how a record and its item are matched, so re-runs update items instead of
duplicating them, and a changed citekey updates the same item. A record that leaves data.csv
(merged, deleted or no longer published) is moved to the "Withdrawn" sub-collection and tagged,
never deleted; if it comes back, it moves back. Only the fields this script writes are overwritten:
notes, attachments, other tags and other collections stay. Settings: "reviews" in
bibliography.config.json. Run from the repository root with ZOTERO_API_KEY set:

    python scripts/sync_reviews.py [--apply] [--only ID ...] [--allow-shrink]

Without --apply nothing is written: the script lists what it would add, change, withdraw and
restore. --only limits the run to the given ids (to try a change on one item first).
--allow-shrink lets one run withdraw more than reviews.maxWithdraw of the items.
"""
import argparse
import csv
import os
import re
import sys

from bibliography_lib import ROOT, ZoteroError, fail, load_config, notice, zotero_from_config

CHAIN = re.compile(r'^[WLQ]\d{2}$')
# Fields this script owns on every item; anything else on the item is left alone.
FIELDS = ('title', 'creators', 'publicationTitle', 'place', 'date', 'volume', 'issue', 'pages', 'url',
          'archive', 'archiveLocation', 'citationKey')


def title_of(row, settings):
    collections = row['collection'].split(', ')
    collection = collections[0] if len(collections) == 1 else settings['severalCollections']
    template = settings['titles'].get(row['publication_type'], settings['defaultTitle'])
    return template.format(collection=collection)


def creators_of(name):
    if not name:
        return []
    parts = name.split()
    if ' and ' in name or len(parts) < 2:  # several people, or a single name/pseudonym
        return [{'creatorType': 'author', 'name': name}]
    return [{'creatorType': 'author', 'firstName': ' '.join(parts[:-1]), 'lastName': parts[-1]}]


def date_of(row):
    parts = [row['publication_year'], row['publication_month'], row['publication_day']]
    parts = [p for p in parts if p]
    return '-'.join([parts[0]] + [p.zfill(2) for p in parts[1:]]) if parts else ''


def wanted(row, settings):
    """The managed fields of the item for one data.csv row."""
    return {
        'title': title_of(row, settings),
        'creators': creators_of(row['publication_reviewer']),
        'publicationTitle': row['publication_name'],
        'place': row['publication_place'],
        'date': date_of(row),
        'volume': row['publication_volume'],
        'issue': row['publication_number'],
        'pages': row['publication_pages'].replace('–', '-'),
        'url': settings['siteUrl'] + row['id'],
        'archive': row['archive_name'],
        'archiveLocation': row['archive_url'],
        'citationKey': row.get('citekey', ''),
    }


def managed_tags(item, chain, settings, withdrawn):
    keep = [t for t in item.get('tags', []) if t['tag'] not in (settings['tag'], settings['withdrawnTag'])
            and not CHAIN.match(t['tag'])]
    tags = [{'tag': settings['tag']}] + ([{'tag': chain}] if chain else [])
    return keep + tags + ([{'tag': settings['withdrawnTag']}] if withdrawn else [])


def tag_names(tags):
    return sorted(t['tag'] for t in tags)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--only', nargs='+', metavar='ID')
    parser.add_argument('--allow-shrink', action='store_true')
    args = parser.parse_args()

    config = load_config()
    settings = config['reviews']
    with open(ROOT / settings['data'], encoding='utf-8', newline='') as f:
        rows = {r['id']: r for r in csv.DictReader(f, delimiter=';')}
    zotero = zotero_from_config(config)
    if zotero is None:
        return 0

    site = re.compile(re.escape(settings['siteUrl']) + r'(\d+)$')
    try:
        # A dry run must not change Zotero, so it only looks for the collections and never creates them.
        find = zotero.find_collection
        main_key = find(settings['collection']) or (None if not args.apply else zotero.ensure_subcollection(
            settings['collection'], None))
        sub = (zotero.ensure_subcollection if args.apply else find)
        gone_key = sub(settings['withdrawnSubcollection'], main_key) if main_key else None
        existing = {}
        for key, withdrawn in ((main_key, False), (gone_key, True)):
            for item in (zotero.items(key) if key else []):
                found = site.match(item.get('url', ''))
                if not found:
                    continue
                if found.group(1) in existing:
                    fail(f'Two Zotero items have the URL {item["url"]} ({existing[found.group(1)][0]["key"]}, '
                         f'{item["key"]}). Merge them in Zotero, then re-run.')
                existing[found.group(1)] = (item, withdrawn)
    except ZoteroError as error:
        fail(str(error))

    ids = set(rows) | set(existing)
    if args.only:
        ids &= set(args.only)

    writes, report = [], {'added': [], 'changed': [], 'withdrawn': [], 'restored': []}
    for id_ in sorted(ids, key=int):
        row = rows.get(id_)
        item, was_withdrawn = existing.get(id_, (None, False))
        if row and item is None:
            new = {'itemType': 'newspaperArticle', **wanted(row, settings),
                   'tags': managed_tags({}, row.get('chain_id', ''), settings, False),
                   'collections': [main_key] if main_key else []}
            writes.append({k: v for k, v in new.items() if v not in ('', [])})
            report['added'].append(f'{id_} {new["title"]} ({row["publication_name"]}, {date_of(row)})')
            continue
        if row:
            target = wanted(row, settings)
            changed = [f for f in FIELDS if (item.get(f) or '') != (target[f] or '')]
            tags = managed_tags(item, row.get('chain_id', ''), settings, False)
            if tag_names(tags) != tag_names(item.get('tags', [])):
                changed.append('tags')
            collections = [c for c in item.get('collections', []) if c != gone_key]
            collections += [main_key] if main_key not in collections else []
            if not changed and not was_withdrawn:
                continue
            update = {'key': item['key'], 'version': item['version'], 'tags': tags, 'collections': collections,
                      **{f: target[f] for f in FIELDS}}
            writes.append(update)
            report['restored' if was_withdrawn else 'changed'].append(f'{id_}: {", ".join(changed) or "collection"}')
        elif not was_withdrawn:
            collections = [c for c in item.get('collections', []) if c != main_key] + [gone_key]
            chain = next((t['tag'] for t in item.get('tags', []) if CHAIN.match(t['tag'])), None)
            writes.append({'key': item['key'], 'version': item['version'], 'collections': collections,
                           'tags': managed_tags(item, chain, settings, True)})
            report['withdrawn'].append(f'{id_} {item.get("title", "")}')

    active = sum(1 for _, withdrawn in existing.values() if not withdrawn)
    if active and len(report['withdrawn']) > settings['maxWithdraw'] * active and not args.allow_shrink:
        fail(f'{len(report["withdrawn"])} of {active} items would be withdrawn, more than reviews.maxWithdraw '
             f'allows. If data.csv is right, re-run with --allow-shrink.')

    lines = []
    for name, entries in report.items():
        lines.append(f'**{len(entries)} {name}**' + ''.join(f'\n- {e}' for e in entries))
    heading = ('Zotero sync' if args.apply else 'Zotero sync (dry run: nothing written)') + \
        (f', ids {" ".join(args.only)}' if args.only else '')
    text = f'### {heading}\n\n' + '\n\n'.join(lines) + '\n'
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(text)

    if args.apply and writes:
        try:
            zotero.create_items(writes)
        except ZoteroError as error:
            fail(str(error))
        notice(f'{len(writes)} item(s) written to Zotero.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
