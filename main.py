from fastapi import FastAPI
from app.api.users import router as user_router
from app.api.community_interactions import router as community_router
from app.api.interactions import router as interaction_router
from app.api.interactions import router as interaction_router
from app.api.user_segments import router as user_segment_router

app = FastAPI()

app.include_router(user_router, prefix="/api/v1")
app.include_router(community_router, prefix="/api/v1")
app.include_router(interaction_router, prefix="/api/v1")
app.include_router(interaction_router, prefix="/api/v1")
app.include_router(user_segment_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)