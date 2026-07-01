"""Run at image build time to pre-seed employees.db."""
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/app/employees.db")

conn = sqlite3.connect(DB_PATH)
with open(os.path.join(os.path.dirname(__file__), "seed.sql")) as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
print(f"Seeded {DB_PATH}")
