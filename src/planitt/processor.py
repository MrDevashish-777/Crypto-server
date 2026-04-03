from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config.constants import CRYPTO_PAIRS, TIMEFRAMES
from config.settings import settings
from src.data.data_fetcher import DataFetcher
from src.llm.agent import LLMAgentFactory
from src.llm.context import ContextManager
from src.planitt.confluence import evaluate_confluence_pre_gates_with_reason
from src.planitt.schemas import (
    PlanittSignal,
    compute_expires_at,
    now_utc,
    parse_planitt_llm_decision,
)
from src.planitt.targets import compute_planitt_targets

logger = logging.getLogger(__name__)


def timeframe_to_cycle_seconds(timeframe: str) -> int:
    # Binance format timeframes supported in config/constants.py
    mapping = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
        "1M": 2592000,
    }
    return mapping.get(timeframe, 900)


class PlanittProcessor:
    """
    Planitt processor pipeline:
    pre-gates -> Ollama decision -> deterministic tp/sl -> validate -> POST to NestJS.
    """

    def __init__(self) -> None:
        self.data_fetcher = DataFetcher()
        self.context_manager = ContextManager()

        self.llm_agent = LLMAgentFactory.create_agent(
            provider=settings.LLM_PROVIDER,
            api_key=getattr(settings, f"{settings.LLM_PROVIDER.upper()}_API_KEY", None),
            model=getattr(settings, f"{settings.LLM_PROVIDER.upper()}_MODEL", None),
            base_url=settings.OLLAMA_BASE_URL if settings.LLM_PROVIDER == "ollama" else None,
        )

        self._dedup: dict[str, bool] = {}
        self._dedup_lock = asyncio.Lock()

    async def close(self) -> None:
        await self.data_fetcher.close()

    def _dedup_key(self, *, asset: str, timeframe: str, created_at: datetime) -> str:
        cycle_seconds = timeframe_to_cycle_seconds(timeframe)
        cycle_id = int(created_at.replace(tzinfo=timezone.utc).timestamp() // cycle_seconds)
        return f"{asset}:{timeframe}:{cycle_id}"

    async def generate_and_forward(
        self,
        *,
        symbol: str,
        timeframe: str,
        correlation_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Returns the payload forwarded to backend, or None if dropped as NO TRADE.
        """

        if symbol not in CRYPTO_PAIRS:
            return None
        if timeframe not in TIMEFRAMES:
            return None

        pair_asset = CRYPTO_PAIRS[symbol]

        created_at = now_utc()
        dedup_key = self._dedup_key(asset=pair_asset, timeframe=timeframe, created_at=created_at)
        async with self._dedup_lock:
            if dedup_key in self._dedup:
                logger.info(
                    "Planitt drop: duplicate",
                    extra={"correlation_id": correlation_id, "asset": pair_asset, "timeframe": timeframe},
                )
                return None
            # Reserve the key early to avoid concurrency duplicates.
            self._dedup[dedup_key] = True

        try:
            # 1) Fetch candles
            candle_list = await self.data_fetcher.fetch_candles(
                symbol=symbol,
                timeframe=timeframe,
                limit=260,
                from_cache=True,
                min_candles=settings.PLANITT_MIN_CANDLES,
            )

            # 2) Pre-gates (confluence)
            eval_result = evaluate_confluence_pre_gates_with_reason(
                candle_list,
                adx_trend_threshold=settings.PLANITT_ADX_TREND_THRESHOLD,
                volume_multiplier=settings.PLANITT_VOLUME_MULTIPLIER,
                touch_tolerance_pct=settings.PLANITT_TOUCH_TOLERANCE_PCT,
                min_confluence_hits=settings.PLANITT_MIN_CONFLUENCE_HITS,
            )
            features = eval_result.features
            if features is None:
                logger.info(
                    "Planitt drop: confluence_failed",
                    extra={
                        "correlation_id": correlation_id,
                        "asset": pair_asset,
                        "timeframe": timeframe,
                        "reason": eval_result.reject_reason,
                    },
                )
                async with self._dedup_lock:
                    self._dedup.pop(dedup_key, None)
                return None

            # 3) LLM decision (Ollama)
            market_data_for_llm = self._build_llm_input(features, candle_list)
            context = ""  # keep deterministic and avoid coupling to trade history for now
            if hasattr(self.context_manager, "get_market_regime_context"):
                context = self.context_manager.get_market_regime_context()

            if hasattr(self.llm_agent, "generate_planitt_decision"):
                decision_raw = await self.llm_agent.generate_planitt_decision(
                    market_data=market_data_for_llm,
                    context=context,
                )
            else:
                logger.warning("LLM provider missing Planitt decision API; falling back to NO TRADE")
                decision_raw = "NO TRADE"
            parsed_decision = parse_planitt_llm_decision(decision_raw)
            if parsed_decision.model is None:
                # Helpful diagnostics: include raw response preview when JSON parsing fails.
                decision_raw_str = (
                    decision_raw[:500]
                    if isinstance(decision_raw, str)
                    else str(decision_raw)[:500]
                )
                logger.info(
                    "Planitt drop: llm_no_trade_or_invalid",
                    extra={
                        "correlation_id": correlation_id,
                        "asset": pair_asset,
                        "timeframe": timeframe,
                        "reason": parsed_decision.dropped_reason,
                        "decision_raw_preview": decision_raw_str,
                    },
                )
                async with self._dedup_lock:
                    self._dedup.pop(dedup_key, None)
                return None

            decision = parsed_decision.model
            if decision.confidence < settings.PLANITT_MIN_CONFIDENCE:
                logger.info(
                    "Planitt drop: confidence_below_threshold",
                    extra={"correlation_id": correlation_id, "asset": pair_asset, "timeframe": timeframe, "confidence": decision.confidence},
                )
                async with self._dedup_lock:
                    self._dedup.pop(dedup_key, None)
                return None

            # 4) Deterministic numeric levels
            targets = compute_planitt_targets(features)

            # 5) Assemble strict Planitt payload for validation
            planitt_signal = PlanittSignal.model_validate(
                {
                    "asset": pair_asset,
                    "signal_type": decision.signal_type,
                    "entry_range": targets["entry_range"],
                    "stop_loss": targets["stop_loss"],
                    "take_profit": targets["take_profit"],
                    "risk_reward_ratio": targets["risk_reward_ratio"],
                    "confidence": decision.confidence,
                    "timeframe": timeframe,
                    "strategy": decision.strategy,
                    "reason": decision.reason,
                    "validity": decision.validity,
                }
            )

            expires_at = compute_expires_at(created_at, planitt_signal.validity)
            reason_suffix = ""
            if features.candlestick_pattern:
                reason_suffix = (
                    f" | pattern={features.candlestick_pattern}"
                    f" strength={features.candlestick_strength:.2f}"
                    f" confirmed={features.candlestick_confirmed}"
                )
            payload = {
                "asset": planitt_signal.asset,
                "signal_type": planitt_signal.signal_type,
                "entry_range": planitt_signal.entry_range,
                "stop_loss": planitt_signal.stop_loss,
                "take_profit": planitt_signal.take_profit.model_dump(),
                "timeframe": planitt_signal.timeframe,
                "confidence": planitt_signal.confidence,
                "strategy": planitt_signal.strategy,
                "reason": f"{planitt_signal.reason}{reason_suffix}",
                "validity": planitt_signal.validity,
                "created_at": created_at.isoformat(),
                "status": "active",
                "risk_reward_ratio": planitt_signal.risk_reward_ratio,
                # Internal helpers for dedup/expiry on the backend.
                "expires_at": expires_at.isoformat() if expires_at else None,
                "dedup_key": dedup_key,
            }

            # 6) Forward to backend (internal API key)
            await self._post_to_backend(payload, correlation_id=correlation_id)
            return payload
        except Exception:
            async with self._dedup_lock:
                self._dedup.pop(dedup_key, None)
            raise
        

    def _build_llm_input(self, features: Any, candle_list: Any) -> dict[str, Any]:
        # Keep input compact but sufficient for the model to justify decision.
        # Keep it smaller to reduce Ollama latency/timeouts during local scans.
        n = min(20, len(candle_list.candles))
        candles = candle_list.candles[-n:]
        return {
            "asset": features.asset,
            "timeframe": features.timeframe,
            "price": features.price,
            "ohlcv": {
                "open": [c.open for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
                "volume": [c.volume for c in candles],
            },
            "indicators": {
                "RSI": round(features.rsi, 3),
                "MACD": {
                    "hist": round(features.macd_hist, 6),
                    "hist_prev": round(features.macd_hist_prev, 6),
                },
                "EMA": {"20": round(features.ema20, 6), "50": round(features.ema50, 6), "200": round(features.ema200, 6)},
                "ATR": round(features.atr, 6),
                "volume_ratio": round(features.volume_ratio, 3),
                "adx": features.adx,
            },
            "setup_candidates": {
                "setup_type": features.setup_type,
                "key_level": features.key_level,
                "confluence_hits": list(features.confluence_hits),
                "pre_confidence": round(features.pre_confidence, 3),
                "candlestick": {
                    "pattern": features.candlestick_pattern,
                    "bias": features.candlestick_bias,
                    "strength": round(features.candlestick_strength, 3),
                    "confirmed": features.candlestick_confirmed,
                },
            },
        }

    async def _post_to_backend(self, payload: dict[str, Any], *, correlation_id: str) -> None:
        base_url = settings.PLANITT_BACKEND_BASE_URL.rstrip("/")
        url = f"{base_url}/signals"
        api_key = settings.PLANITT_BACKEND_INTERNAL_API_KEY

        if not api_key or api_key == "change-me":
            logger.error(
                "Planitt backend API key missing; set PLANITT_BACKEND_INTERNAL_API_KEY",
                extra={"correlation_id": correlation_id, "asset": payload.get("asset")},
            )
            return

        headers = {"x-api-key": api_key, "x-correlation-id": correlation_id}
        max_retries = 4
        backoff = 0.8

        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code in (200, 201):
                        return
                    if resp.status_code == 409:
                        logger.info(
                            "Planitt backend deduped signal",
                            extra={"correlation_id": correlation_id, "asset": payload.get("asset")},
                        )
                        return
                    if resp.status_code >= 500:
                        logger.warning(
                            "Planitt backend error (retry)",
                            extra={
                                "correlation_id": correlation_id,
                                "asset": payload.get("asset"),
                                "status": resp.status_code,
                                "attempt": attempt,
                                "body": resp.text[:400],
                            },
                        )
                        raise RuntimeError(f"backend {resp.status_code}")

                    # Non-retryable failures (400/401 etc)
                    logger.error(
                        "Planitt backend rejected payload",
                        extra={"correlation_id": correlation_id, "asset": payload.get("asset"), "status": resp.status_code, "body": resp.text[:400]},
                    )
                    return
                except Exception as e:
                    if attempt >= max_retries:
                        logger.error(
                            "Planitt backend POST failed (max retries)",
                            extra={"correlation_id": correlation_id, "asset": payload.get("asset"), "error": str(e)},
                        )
                        return
                    sleep_s = backoff * (2 ** (attempt - 1)) + random.random() * 0.2
                    await asyncio.sleep(sleep_s)

