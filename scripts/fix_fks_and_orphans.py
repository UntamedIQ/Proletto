#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text, inspect

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')
engine = create_engine(DATABASE_URL)

def rename_table(old, new):
    insp = inspect(engine)
    if old in insp.get_table_names() and new not in insp.get_table_names():
        print(f"Renaming table {old} → {new}")
        engine.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}";'))
    else:
        print(f"Skipping rename: {old} → {new} (exists? {new in insp.get_table_names()})")

def fix_fks():
    # Identify all foreign key constraints referencing user.id
    sql = """
    SELECT tc.constraint_name, tc.table_name, kcu.column_name
      FROM information_schema.table_constraints AS tc
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
     WHERE tc.constraint_type = 'FOREIGN KEY'
       AND tc.constraint_schema = 'public'
       AND kcu.referenced_table_name = 'user';
    """
    rows = engine.execute(text(sql)).fetchall()
    for constraint, tbl, col in rows:
        new_constraint = constraint.replace('user', 'users')
        print(f"Dropping FK {constraint} on {tbl}.{col}")
        engine.execute(text(f'ALTER TABLE "{tbl}" DROP CONSTRAINT "{constraint}";'))
        print(f"Adding   FK {new_constraint} on {tbl}.{col} → users.id")
        engine.execute(text(f'ALTER TABLE "{tbl}" ADD CONSTRAINT "{new_constraint}" '
                            f'FOREIGN KEY ("{col}") REFERENCES "users"(id);'))

def cleanup_orphans():
    # For each table with user_id FK, delete or null orphaned rows
    tables = ['digest_emails', 'payments', 'referrals', 'feedback', 
              'workspace_member', 'task', 'task_comment', 'project_file',
              'message', 'message_read_receipt']  # extend as needed
    for tbl in tables:
        print(f"Nulling orphaned user_id in {tbl}")
        engine.execute(text(f'''
          UPDATE "{tbl}"
             SET user_id = NULL
           WHERE user_id IS NOT NULL
             AND user_id NOT IN (SELECT id FROM users);
        '''))

if __name__ == "__main__":
    rename_table('user', 'users')
    fix_fks()
    cleanup_orphans()
    print("✅ FK migration complete.")