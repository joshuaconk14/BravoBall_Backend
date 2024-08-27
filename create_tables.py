"""
create_tables.py
This file is ran once to create tables for postgres db
"""

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import models
import asyncio

# Create an async engine
DATABASE_URL = "postgresql+asyncpg://jordinho:m44YMQsbrxpewhTJRzzX@localhost/tekkdb"
engine = create_async_engine(DATABASE_URL, echo=True)

# Define an async function to create tables
async def create_tables():
    # Connect to the database asynchronously
    async with engine.begin() as conn:
        # Run the synchronous create_all() method in an async context
        await conn.run_sync(models.Base.metadata.create_all)

# Run the async function using an event loop
asyncio.run(create_tables())
