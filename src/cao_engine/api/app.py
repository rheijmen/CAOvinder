"""FastAPI application for querying CAO data and moments."""


from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from cao_engine import __version__
from cao_engine.config import Settings
from cao_engine.storage.json_store import JSONStore
from cao_engine.storage.moment_store import MomentStore

app = FastAPI(
    title="CAO Intelligence Engine",
    description="API for querying structured Dutch CAO data and moments",
    version=__version__,
)

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_settings() -> Settings:
    return Settings()


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


# OLD ENDPOINT - Commented out to use the modern API from cao_routes.py
# @app.get("/api/v1/caos")
# async def list_caos():
#     """List all processed CAO documents."""
#     settings = _get_settings()
#     store = JSONStore(settings)
#     docs = store.list_documents()
#     return {
#         "caos": [p.stem for p in docs],
#         "count": len(docs),
#     }


@app.get("/api/v1/momenten")
async def list_momenten(
    cao: str | None = Query(None, description="Filter by CAO name"),
    categorie: str | None = Query(None, description="Filter by moment category"),
    days_ahead: int = Query(90, description="Show moments in the next N days"),
):
    """List moments from the moment store."""
    settings = _get_settings()
    store = MomentStore(settings)

    if categorie:
        from cao_engine.models.momenten import MomentCategorie

        try:
            cat = MomentCategorie(categorie)
        except ValueError:
            return {"error": f"Unknown category: {categorie}"}
        moments = store.query_by_categorie(cat, cao)
    else:
        moments = store.query_upcoming(days_ahead=days_ahead, cao_naam=cao)

    return {
        "momenten": [m.model_dump(mode="json") for m in moments],
        "count": len(moments),
    }


@app.get("/api/v1/momenten/{moment_id}")
async def get_moment(moment_id: str):
    """Get a specific moment by ID."""
    settings = _get_settings()
    store = MomentStore(settings)

    for ms in store.load_all():
        for m in ms.momenten:
            if m.moment_id == moment_id:
                return m.model_dump(mode="json")

    return {"error": "Moment not found"}


# Import and include the modern API routes
from cao_engine.api.routes.cao_routes import router as cao_router
from cao_engine.api.routes.processing_routes import router as processing_router

app.include_router(cao_router)
app.include_router(processing_router)
