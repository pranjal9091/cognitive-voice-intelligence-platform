#!/usr/bin/env python3
# ==============================================================================
# Database Tables Initializer - Cognitive Voice Intelligence Platform
# ==============================================================================

import asyncio
import os
import sys

# Add root directory to python path to allow importing 'database'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from database.models import Base

# Try to load env file values if python-dotenv is present, otherwise fallback to OS variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Read database URL (default to localhost PG development setup)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres_password_here@localhost:5432/cognitive_voice_db"
)

async def init_db():
    print(f"📡 Connecting to database endpoint at: {DATABASE_URL.split('@')[-1]}")
    
    # Create asynchronous SQLAlchemy engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            print("🗄️  Instantiating database schemas and indices...")
            # run_sync executes sync creation methods inside async connection pools
            await conn.run_sync(Base.metadata.create_all)
        print("🎉 Relational tables initialized successfully!")
    except Exception as e:
        print(f"❌ Error occurred during schema setup: {e}", file=sys.stderr)
        print("   Make sure PostgreSQL is active and your DATABASE_URL in .env is correct.", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
