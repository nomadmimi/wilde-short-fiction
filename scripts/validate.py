"""Check data.csv against the schema in datapackage.json.

Run from the repository root: python scripts/validate.py
Exits with an error listing every broken row by its id, so a bad row is
fixed at the source rather than silently dropped by the website.
"""
import sys
from pathlib import Path

from frictionless import Package

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    package = Package(ROOT / 'datapackage.json')
    resource = package.get_resource('reviews')
    report = package.validate()

    ids = {row.row_number: row['id'] for row in resource.read_rows()}

    problems = [error for task in report.tasks for error in task.errors]
    for error in problems:
        row = getattr(error, 'row_number', None)
        where = f"id {ids.get(row, '?')} (row {row})" if row else 'file'
        field = getattr(error, 'field_name', None)
        print(f"{where}: {field + ': ' if field else ''}{error.note or error.message}")

    if problems:
        print(f'\n{len(problems)} problem(s) in {resource.path}.')
        return 1

    print(f'{resource.path}: {len(ids)} rows, all valid.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
