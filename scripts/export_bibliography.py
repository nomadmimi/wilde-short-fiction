"""Export the main Zotero collection to bibliography.json (CSL-JSON).

Zotero is the master copy; bibliography.json is generated from it, so edit entries
in Zotero. Run from the repository root with ZOTERO_API_KEY set:

    python scripts/export_bibliography.py

Options:
  --allow-shrink            write the file even if it would lose more entries than
                            export.maxShrink allows (see bibliography.config.json)
  --for-zotero-import OUT   no network: write a copy of bibliography.json to OUT that
                            carries each entry's id in Zotero's Extra field
                            ("Citation Key: ..."), so the one-time import keeps the ids

An entry's id is, in this order: the "Citation Key: ..." line in its Extra field; the id
the same work already has in bibliography.json (matched by DOI, or first author + year +
title), so existing ids survive the move to Zotero; otherwise one generated from the first
author, year and first title word.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from bibliography_lib import (ZoteroError, base_id, bibliography_path, dump_bibliography, fail, load_config, notice,
                              plain, work_key, zotero_from_config)

CITATION_KEY = re.compile(r'^Citation Key:\s*(\S+)\s*$', re.M | re.I)
# Fields Zotero adds that the website does not use.
DROP = {'id', 'citation-key', 'abstract', 'keyword'}


def pinned_id(item):
    """An id fixed by the entry itself: a CSL citation-key or a "Citation Key:" line in its note (Extra)."""
    if item.get('citation-key'):
        return item['citation-key']
    found = CITATION_KEY.search(item.get('note') or '')
    return found.group(1) if found else None


def name_lists(item):
    """The lists of people in an item (author, editor, director, ...)."""
    return [v for v in item.values() if isinstance(v, list) and v and all(isinstance(n, dict) for n in v)]


def suffixes_in(items):
    """(family, given) -> suffix for every name in the current bibliography that has one ("Smith", "Philip E." -> "II")."""
    return {(n.get('family'), n.get('given')): n['suffix'] for item in items for names in name_lists(item)
            for n in names if n.get('suffix')}


def tidy(item, suffixes=None):
    """Undo what the trip through Zotero changes without meaning to, so a re-export gives the same file."""
    out = {k: v for k, v in item.items() if k not in DROP and v not in (None, '', [], {})}
    if 'note' in out:
        note = CITATION_KEY.sub('', out['note']).strip()
        if note:
            out['note'] = note
        else:
            del out['note']
    # Zotero writes a film's director as its author; MLA wants the director.
    if out.get('type') == 'motion_picture' and 'author' in out and 'director' not in out:
        out['director'] = out.pop('author')
    # Years are numbers in CSL-JSON; Zotero sometimes writes them as text.
    for date in (v for v in out.values() if isinstance(v, dict) and 'date-parts' in v):
        date['date-parts'] = [[int(p) if str(p).isdigit() else p for p in parts] for parts in date['date-parts']]
    for names in name_lists(out):
        for name in names:
            if not name.get('given') and name.get('family'):  # a one-field name ("Google Books Ngram Viewer")
                name.pop('given', None)
                name['literal'] = name.pop('family')
            elif suffixes and not name.get('suffix') and (name.get('family'), name.get('given')) in suffixes:
                name['suffix'] = suffixes[name['family'], name['given']]  # Zotero has no field for "II"
    return out


def build_items(raw, previous=()):
    """CSL-JSON from Zotero -> the entries to store: untitled records dropped, ids assigned, sorted by id.

    `previous` is the current bibliography; a work found there keeps the id it has."""
    items, skipped, suffixes = [], 0, suffixes_in(previous)
    for record in raw:
        if not record.get('title'):  # a standalone note, not a work
            skipped += 1
            continue
        items.append((pinned_id(record), tidy(record, suffixes)))
    if skipped:
        notice(f'Skipped {skipped} record(s) without a title (notes?).')

    taken = [pin for pin, _ in items if pin]
    duplicates = sorted({pin for pin in taken if taken.count(pin) > 1})
    if duplicates:
        raise ValueError(f'These Citation Key values are used by more than one entry: {", ".join(duplicates)}')

    used = set(taken)
    carried = defaultdict(list)  # work -> ids it already has, in file order
    for old in previous:
        carried[work_key(old)].append(old['id'])
    unpinned = sorted((i for pin, i in items if not pin), key=lambda i: (plain(i['title']), i.get('DOI', '')))
    for item in unpinned:
        ids = carried[work_key(item)]
        while ids and ids[0] in used:
            ids.pop(0)
        if ids:
            item['_id'] = ids.pop(0)
            used.add(item['_id'])

    # New works get a generated id: the same base gets b, c, ... in a fixed order so reruns agree.
    groups = defaultdict(list)
    for item in unpinned:
        if '_id' not in item:
            groups[base_id(item)].append(item)
    for base, group in groups.items():
        for n, item in enumerate(group):
            candidate = base if n == 0 else base + chr(ord('a') + n)
            while candidate in used:
                candidate += 'x'
            used.add(candidate)
            item['_id'] = candidate
    out = []
    for pin, item in items:
        identity = pin or item.pop('_id')
        out.append({'id': identity, **dict(sorted(item.items()))})
    return sorted(out, key=lambda i: i['id'])


def for_zotero_import(source, target):
    items = json.loads(source.read_text(encoding='utf-8'))
    for item in items:
        note = f'Citation Key: {item["id"]}'
        item['note'] = f'{note}\n{item["note"]}' if item.get('note') else note
    target.write_text(dump_bibliography(items), encoding='utf-8')
    print(f'Wrote {len(items)} entries to {target}. Import that file into Zotero (File > Import).')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--allow-shrink', action='store_true')
    parser.add_argument('--for-zotero-import', metavar='OUT')
    args = parser.parse_args()

    config = load_config()
    path = bibliography_path(config)
    if args.for_zotero_import:
        for_zotero_import(path, Path(args.for_zotero_import))
        return 0

    zotero = zotero_from_config(config)
    if zotero is None:
        return 0
    name = config['zotero']['collection']
    try:
        key = zotero.find_collection(name)
        if key is None:
            fail(f'No top-level Zotero collection named {name!r}. Fix zotero.collection in bibliography.config.json.')
        previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        items = build_items(zotero.csl_items(key), previous)
    except (ZoteroError, ValueError) as error:
        fail(str(error))

    before = len(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else 0
    floor = before * (1 - config['export']['maxShrink'])
    if len(items) < floor and not args.allow_shrink:
        fail(f'Zotero returned {len(items)} entries but {path.name} has {before}; refusing to drop more than '
             f'{config["export"]["maxShrink"]:.0%}. If that is intended, rerun with --allow-shrink.')

    path.write_text(dump_bibliography(items), encoding='utf-8')
    print(f'{path.name}: {len(items)} entries exported from the {name!r} collection (was {before}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
