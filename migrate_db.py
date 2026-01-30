import sqlite3
import os

def migrate():
    db_path = "walletracker.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns_to_add = [
        ("narrative", "TEXT"),
        ("twitter_url", "TEXT"),
        ("website_url", "TEXT"),
        ("narrative_status", "TEXT DEFAULT 'NEW'"),
        ("last_updated_at", "DATETIME")
    ]

    print(f"📡 Migrating database {db_path}...")
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE tokens ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added column {col_name} to tokens table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ Column {col_name} already exists.")
            else:
                print(f"❌ Error adding column {col_name}: {e}")

    conn.commit()
    conn.close()
    print("✨ Migration complete.")

if __name__ == "__main__":
    migrate()
