import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, Config
from passlib.context import CryptContext
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./walletracker.db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def migrate():
    print("🚀 Starting Database Migration...")
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🛠️ Creating all tables if they don't exist...")
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        from sqlalchemy import select
        # Initialize default password if not set
        result = await session.execute(select(Config).where(Config.key == "upload_password_hash"))
        if not result.scalar_one_or_none():
            print("🔐 Initializing default upload password...")
            default_pw = "eDJwdE4Lf2ZT"
            hashed_pw = pwd_context.hash(default_pw)
            config = Config(key="upload_password_hash", value=hashed_pw)
            session.add(config)
            await session.commit()
            print("✅ Default password initialized.")
        else:
            print("ℹ️ Password already initialized.")
            
    print("✨ Migration complete!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
