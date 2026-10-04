"""Build a new reference-only SQLite database; never overwrite an existing file."""
from pathlib import Path
import argparse
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]

def build(target):
    target = Path(target)
    if target.exists():
        raise FileExistsError(f'Refusing to overwrite {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.executescript((ROOT / 'db/schema.sql').read_text())
    records = json.loads((ROOT / 'fixtures/local-reference-data.json').read_text())['records']
    for r in records:
        conn.execute('INSERT INTO reference_records VALUES (?,?,?,?,?,?)', (r['source_id'],r['kind'],int(r['synthetic']),r['source_type'],r['as_of'],json.dumps(r['data'],ensure_ascii=False)))
        if r['kind'] == 'entity_profile':
            d = r['data']
            conn.execute('INSERT INTO entity_profiles VALUES (?,?,?,?,?,?,?,?)', (d['entity_id'],d['legal_name'],d['tax_id'],d['country'],d['verification_status'],r['source_id'],json.dumps(d,ensure_ascii=False),1))
    conn.commit()
    seed = '\n'.join(line for line in conn.iterdump() if line.startswith('INSERT INTO'))
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    conn.close()
    return seed

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--write-seed',action='store_true')
    args=parser.parse_args()
    seed=build(args.output)
    if args.write_seed:
        (ROOT / 'db/seed.sql').write_text('BEGIN;\n'+seed+'\nCOMMIT;\n')
    print(f'Created {args.output}: 2 entities, 6 synthetic reference sources; no assessed cases.')
