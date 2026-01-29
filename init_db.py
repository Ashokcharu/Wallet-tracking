import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base

DATABASE_URL = "sqlite+aiosqlite:///./walletracker.db"

async def init_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
