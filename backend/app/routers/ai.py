from fastapi import APIRouter

from app.services import ai_budget

router = APIRouter(tags=["ai"])


@router.get("/ai/usage")
async def ai_usage() -> dict:
    """Today's Claude spending against AI_DAILY_BUDGET_USD."""
    return ai_budget.usage()
