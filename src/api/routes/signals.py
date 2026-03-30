"""
Signal API Routes
Endpoints for signal generation and retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Optional
import logging
from src.signals.engine import SignalEngine
from src.signals.signal import TradingSignal, SignalResponse
from config.constants import CRYPTO_PAIRS, TIMEFRAMES
from src.api.middleware.internal_api_key import require_internal_api_key
from src.planitt.processor import PlanittProcessor
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/signals",
    tags=["signals"],
    dependencies=[Depends(require_internal_api_key)],
)

# Global signal engine instance
signal_engine = None
planitt_processor: Optional[PlanittProcessor] = None


async def get_signal_engine():
    """Get signal engine instance"""
    global signal_engine
    if signal_engine is None:
        signal_engine = SignalEngine()
    return signal_engine


async def shutdown_signal_engine():
    """Shutdown signal engine resources"""
    global signal_engine
    if signal_engine is not None:
        await signal_engine.close()
        signal_engine = None
        logger.info("Signal engine shut down successfully")


async def get_planitt_processor() -> PlanittProcessor:
    """Get (singleton) Planitt processing pipeline."""
    global planitt_processor
    if planitt_processor is None:
        planitt_processor = PlanittProcessor()
    return planitt_processor


async def shutdown_planitt_processor() -> None:
    """Shutdown Planitt processor resources."""
    global planitt_processor
    if planitt_processor is not None:
        await planitt_processor.close()
        planitt_processor = None


@router.get("", response_model=SignalResponse)
async def get_signals(
    symbol: Optional[str] = Query(None, description="Crypto symbol (BTC, ETH, etc)"),
    timeframe: Optional[str] = Query("15m", description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(10, description="Number of signals to return"),
):
    """
    Get recently generated signals
    
    Query Parameters:
    - symbol: Filter by symbol (optional)
    - timeframe: Filter by timeframe (default: 15m)
    - limit: Number of results (default: 10)
    """
    try:
        engine = await get_signal_engine()
        signals = engine.get_signal_history(symbol, timeframe)
        signals = signals[:limit]

        return SignalResponse(
            success=True,
            data=signals,
            message=f"Retrieved {len(signals)} signals"
        )
    except Exception as e:
        logger.error(f"Error retrieving signals: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate", response_model=SignalResponse)
async def generate_signal(
    symbol: str = Query(..., description="Crypto symbol (BTC, ETH, etc)"),
    timeframe: str = Query("15m", description="Timeframe"),
    strategy: str = Query("planitt", description="(Deprecated) strategy hint"),
):
    """
    Generate a trading signal for a symbol
    
    Query Parameters:
    - symbol: Cryptocurrency symbol (required)
    - timeframe: Analysis timeframe (default: 15m)
    - strategy: Strategy to use (default: rsi)
    """
    try:
        if symbol not in CRYPTO_PAIRS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported symbol: {symbol}. Supported: {list(CRYPTO_PAIRS.keys())}",
            )
        if timeframe not in TIMEFRAMES:
            raise HTTPException(status_code=400, detail=f"Unsupported timeframe: {timeframe}")

        correlation_id = f"planitt-{int(datetime.utcnow().timestamp() * 1000)}-{symbol}"

        processor = await get_planitt_processor()
        payload = await processor.generate_and_forward(
            symbol=symbol,
            timeframe=timeframe,
            correlation_id=correlation_id,
        )

        if payload is None:
            return SignalResponse(success=False, message="NO TRADE - conditions unclear")

        return SignalResponse(
            success=True,
            data=payload,
            message=f"Signal emitted for {payload.get('asset')}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{symbol}", response_model=SignalResponse)
async def analyze_symbol(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe for analysis"),
):
    """
    Get deep AI analysis for a crypto symbol
    """
    if symbol not in CRYPTO_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
    
    try:
        engine = await get_signal_engine()
        analysis = await engine.get_llm_analysis(symbol, timeframe)
        
        return SignalResponse(
            success=True,
            data=analysis if isinstance(analysis, dict) else {"analysis": analysis},
            message=f"Analysis generated for {symbol}"
        )
    except Exception as e:
        logger.error(f"Error analyzing symbol {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_supported_symbols():
    """Get list of supported symbols"""
    data = {
        "symbols": list(CRYPTO_PAIRS.keys()),
        "count": len(CRYPTO_PAIRS)
    }
    return SignalResponse(
        success=True,
        data=data,
        message=f"Found {len(CRYPTO_PAIRS)} supported symbols"
    )


@router.get("/timeframes")
async def get_supported_timeframes():
    """Get list of supported timeframes"""
    data = {
        "timeframes": list(TIMEFRAMES.keys()),
        "count": len(TIMEFRAMES)
    }
    return SignalResponse(
        success=True,
        data=data,
        message=f"Found {len(TIMEFRAMES)} supported timeframes"
    )


@router.get("/strategies")
async def get_supported_strategies():
    """Get list of supported strategies"""
    data = {
        "strategies": ["rsi", "macd", "multi_strategy"],
        "descriptions": {
            "rsi": "RSI-based strategy - buy on oversold, sell on overbought",
            "macd": "MACD-based strategy - buy on bullish crossover, sell on bearish",
            "multi_strategy": "Consensus from multiple strategies",
        }
    }
    return SignalResponse(
        success=True,
        data=data,
        message="Available trading strategies"
    )


@router.get("/market/status", response_model=SignalResponse)
async def get_market_status():
    """Get real-time status of the crypto market"""
    try:
        engine = await get_signal_engine()
        if hasattr(engine, 'get_market_status') and callable(getattr(engine, 'get_market_status')):
            status = await engine.get_market_status()
        else:
            logger.warning("get_market_status method not available in SignalEngine")
            status = {}
        return SignalResponse(
            success=True,
            data=status,
            message="Market status retrieved"
        )
    except Exception as e:
        logger.error(f"Error fetching market status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}", response_model=SignalResponse)
async def get_signals_for_symbol(
    symbol: str = Path(..., description="Crypto symbol"),
    limit: int = Query(10, description="Number of results"),
):
    """Get signals for a specific symbol"""
    if symbol not in CRYPTO_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")

    try:
        engine = await get_signal_engine()
        if hasattr(engine, 'get_signal_history') and callable(getattr(engine, 'get_signal_history')):
            signals = engine.get_signal_history(symbol)
            signals = signals[:limit] if signals else []
        else:
            logger.warning("get_signal_history method not available in SignalEngine")
            signals = []

        return SignalResponse(
            success=True,
            data={
                "symbol": symbol,
                "signals": signals,
                "count": len(signals)
            },
            message=f"Retrieved {len(signals)} signals for {symbol}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching signals for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
