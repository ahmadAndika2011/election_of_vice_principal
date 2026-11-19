import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pymongo import AsyncMongoClient

# Load .env from the project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(
        os.environ["MONGODB_URI"],
        serverSelectionTimeoutMS=5000,
    )

    try:
        # Verify that MongoDB is reachable
        await client.admin.command("ping")

        app.state.db = client[os.environ["MONGODB_DB"]]
        print("MongoDB connected")

        yield
    finally:
        await client.close()