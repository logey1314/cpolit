from fastapi import FastAPI
from app.api.users import router as user_router
from app.api.community_interactions import router as community_router
from app.api.interactions import router as interaction_router
from app.api.interactions import router as interaction_router
from app.api.user_segments import router as user_segment_router
from app.api.touch_strategies import router as touch_strategy_router
from app.api.content_drafts import router as content_draft_router
from app.api.compliance import router as compliance_router
from app.api.frequency import router as frequency_router
from app.api.operation_tasks import router as operation_task_router

app = FastAPI()

app.include_router(user_router, prefix="/api/v1")
app.include_router(community_router, prefix="/api/v1")
app.include_router(interaction_router, prefix="/api/v1")
app.include_router(interaction_router, prefix="/api/v1")
app.include_router(user_segment_router, prefix="/api/v1")
app.include_router(touch_strategy_router, prefix="/api/v1")
app.include_router(content_draft_router, prefix="/api/v1")
app.include_router(compliance_router, prefix="/api/v1")
app.include_router(frequency_router, prefix="/api/v1")
app.include_router(operation_task_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
