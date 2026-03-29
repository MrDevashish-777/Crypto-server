"""
News API Routes
Endpoints for fetching latest market news and sentiment
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
import logging
from src.api.routes.signals import get_signal_engine
from src.signals.signal import SignalResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news", tags=["news"])

@router.get("", response_model=SignalResponse)
async def get_news(
    limit: int = Query(10, description="Number of news items to return"),
):
    """
    Get latest market news with AI-analyzed sentiment
    """
    try:
        engine = await get_signal_engine()
        news = await engine.get_market_news(limit=limit)
        
        return SignalResponse(
            success=True,
            data=news,
            message=f"Retrieved {len(news)} news items with sentiment analysis"
        )
    except Exception as e:
        logger.error(f"Error retrieving news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
