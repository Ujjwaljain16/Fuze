import sys
import os

sys.path.insert(0, 'backend')

from models import db
from run_production import create_app

app = create_app()
with app.app_context():
    def inspect_table(table_name):
        print(f"\n==================================================")
        print(f"📋 TABLE: {table_name.upper()}")
        print(f"==================================================")
        
        # Columns
        cols_query = db.text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = :tbl
            ORDER BY ordinal_position;
        """)
        cols = db.session.execute(cols_query, {"tbl": table_name}).fetchall()
        print("📊 COLUMNS:")
        for c in cols:
            print(f"  • {c[0]}: {c[1]} (Nullable: {c[2]}, Default: {c[3]})")
            
        # Indexes
        idx_query = db.text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = :tbl
            ORDER BY indexname;
        """)
        idxs = db.session.execute(idx_query, {"tbl": table_name}).fetchall()
        print("\n📈 INDEXES:")
        for i in idxs:
            print(f"  • {i[0]}: {i[1]}")
            
        # Constraints
        con_query = db.text("""
            SELECT c.conname, c.contype, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = :tbl
            ORDER BY c.conname;
        """)
        cons = db.session.execute(con_query, {"tbl": table_name}).fetchall()
        print("\n🔒 CONSTRAINTS:")
        for c in cons:
            type_map = {'p': 'PRIMARY KEY', 'u': 'UNIQUE', 'f': 'FOREIGN KEY', 'c': 'CHECK'}
            ctype = type_map.get(c[1], c[1])
            print(f"  • {c[0]} [{ctype}]: {c[2]}")

    for t in ['users', 'token_families', 'saved_content']:
        inspect_table(t)
        
    print(f"\n==================================================")
    print("🏷️ ALEMBIC VERSION")
    print(f"==================================================")
    ver_query = db.text("SELECT * FROM alembic_version;")
    versions = db.session.execute(ver_query).fetchall()
    for v in versions:
        print(f"  • Version: {v[0]}")
