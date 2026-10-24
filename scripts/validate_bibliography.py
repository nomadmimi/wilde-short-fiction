"""Check bibliography.json, the enumerative bibliography as CSL-JSON.

Run from the repository root: python scripts/validate_bibliography.py
Exits with an error listing every broken or duplicated entry by its id, so a
bad entry is fixed at the source rather than silently dropped by the website.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / 'bibliography.json'

# The CSL item types the bibliography uses; extend when a new kind of work is added.
TYPES = {'article-journal', 'book', 'chapter', 'manuscript', 'motion_picture', 'review', 'thesis', 'webpage'}
DOI = re.compile(r'^10[./]\S+$')


def plain(text):
    return re.sub(r'\W+', ' ', re.sub(r'<[^>]+>', '', text or '')).strip().lower()


def main() -> int:
    items = json.loads(PATH.read_text(encoding='utf-8'))
    problems = []
    seen = defaultdict(list)

    for item in items:
        id = item.get('id', '?')
        if item.get('type') not in TYPES:
            problems.append(f"{id}: unknown type {item.get('type')!r}")
        if not item.get('title'):
            problems.append(f'{id}: no title')
        if 'DOI' in item and not DOI.match(item['DOI']):
            problems.append(f"{id}: DOI {item['DOI']!r} should start with 10. (no https://doi.org/)")
        if 'URL' in item and not item['URL'].startswith(('http://', 'https://')):
            problems.append(f"{id}: URL {item['URL']!r} is not a web address")

        who = (item.get('author') or item.get('editor') or [{}])[0]
        key = (plain(who.get('family') or who.get('literal')), plain(item.get('title')),
               plain(item.get('container-title')), item.get('DOI', ''), item.get('page', ''),
               str(item.get('issued', {}).get('date-parts')))
        seen['id', id].append(id)
        seen['work', key].append(id)

    for (kind, _), ids in seen.items():
        if len(ids) > 1:
            problems.append(f"{', '.join(ids)}: {'same id' if kind == 'id' else 'listed more than once'}")

    for problem in problems:
        print(problem)

    if problems:
        print(f'\n{len(problems)} problem(s) in {PATH.name}.')
        return 1

    print(f'{PATH.name}: {len(items)} entries, all valid.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
