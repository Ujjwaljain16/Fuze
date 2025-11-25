#!/usr/bin/env python3
"""
One-off script to add provider columns to `users` table.
Run this from the repository root (in your virtualenv):

    python backend/scripts/add_provider_columns.py

This uses DATABASE_URL from environment or .env.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print('DATABASE_URL is not set in environment. Aborting.')
    raise SystemExit(1)

engine = create_engine(DATABASE_URL)

stmts = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_name VARCHAR(50);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_user_id VARCHAR(200);",
]

with engine.connect() as conn:
    trans = conn.begin()
    try:
        for s in stmts:
            print('Executing:', s)
            conn.execute(text(s))
        trans.commit()
        print('Provider columns ensured successfully.')
    except Exception as e:
        trans.rollback()
        print('Failed to apply statements:', e)
        raise
