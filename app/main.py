from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.auth_setup import install_auth
from app.auth_service import init_auth_indexes
from app.voting_service import init_voting_indexes
from app.database import lifespan as database_lifespan
from app.routes.home import router as home_router
from app.routes.pilih import router as pilih_router
from app.api.data import router as data_router
from app.api.add_candidate import router as add_candidate_router
from app.api.choose_candidate import router as choose_candidate_router
from app.api.ranking import router as ranking_api_router
from app.routes.ranking import router as ranking_page_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pertahankan koneksi dan cleanup database dari lifespan yang sudah ada.
    async with database_lifespan(app):
        await init_auth_indexes(app.state.db)
        await init_voting_indexes(app.state.db)
        yield


app = FastAPI(lifespan=lifespan)
install_auth(app)

BASE_DIR = Path(__file__).resolve().parent
app.mount(
    "/assets",
    StaticFiles(directory=str(BASE_DIR / "assets")),
    name="assets",
)

app.include_router(home_router)
app.include_router(pilih_router)
app.include_router(data_router)
# app.include_router(add_candidate_router)
app.include_router(choose_candidate_router)
app.include_router(ranking_api_router)
app.include_router(ranking_page_router)