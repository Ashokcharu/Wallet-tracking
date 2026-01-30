import sqlite3
import os

db_path = "walletracker.db"

if not os.path.exists(db_path):
    print(f"❌ Database {db_path} not found.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🛠️ Adding missing columns to news_articles...")
        
        # Add category
        try:
            cursor.execute("ALTER TABLE news_articles ADD COLUMN category TEXT DEFAULT 'Market'")
            print("✅ Added 'category' column.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ 'category' column already exists.")
            else:
                raise e
                
        # Add importance_score
        try:
            cursor.execute("ALTER TABLE news_articles ADD COLUMN importance_score INTEGER DEFAULT 50")
            print("✅ Added 'importance_score' column.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ 'importance_score' column already exists.")
            else:
                raise e

        # Add source_url
        try:
            cursor.execute("ALTER TABLE news_articles ADD COLUMN source_url TEXT")
            print("✅ Added 'source_url' column.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ 'source_url' column already exists.")
            else:
                raise e
        
        conn.commit()
        conn.close()
        print("✨ Migration complete!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
