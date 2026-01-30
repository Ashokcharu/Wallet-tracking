import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine

# Fix imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import Base

async def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./walletracker.db")
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print(f"📡 Initializing database at {DATABASE_URL}...")
        # This will create tables that don't exist
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_db())
