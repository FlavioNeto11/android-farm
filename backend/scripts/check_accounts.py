"""Check Instagram accounts in database"""
from sqlalchemy import create_engine, text
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "farm.db")
engine = create_engine(f"sqlite:///{DB_PATH}")

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, handle, status, error_message FROM accounts WHERE platform = 'instagram'"))
    rows = result.fetchall()
    
    print(f"Total Instagram accounts: {len(rows)}")
    for row in rows:
        print(f"  ID: {row[0]}")
        print(f"  Handle: @{row[1]}")
        print(f"  Status: {row[2]}")
        print(f"  Error: {row[3]}")
        print()
