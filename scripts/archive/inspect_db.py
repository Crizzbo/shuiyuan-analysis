import sqlite3
import json

def inspect():
    con = sqlite3.connect('data/financial/reports.sqlite3')
    print("--- reports.sqlite3: reports table schema ---")
    for col in con.execute("PRAGMA table_info(reports)").fetchall():
        print(col)
    rows = con.execute("SELECT * FROM reports").fetchall()
    print(f"Total rows in reports: {len(rows)}")
    for r in rows[:5]:
        print("Row:", r[0], r[1] if len(r) > 1 else "")
    con.close()

    print("\n--- catalog.sqlite3 ---")
    cat = sqlite3.connect('data/catalog/catalog.sqlite3')
    cat.row_factory = sqlite3.Row
    tables = cat.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for (t,) in tables:
        cnt = cat.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  Table {t}: {cnt} rows")
    cat.close()

if __name__ == '__main__':
    inspect()
