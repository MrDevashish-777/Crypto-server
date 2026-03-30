from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

from src.data.models import CandleList
from src.indicators.ema import EMA
from src.indicators.rsi import RSI
from src.indicators.macd import MACD
from src.indicators.atr import ATR
from src.signals.market_regime import MarketRegimeDetector, MarketRegime

logger = logging.getLogger(__name__)


SignalSide = Literal["BUY", "SELL"]
SetupType = Literal[
    "trend_pullback",
    "volume_breakout",
    "support_resistance_reversal",
]


@dataclass(frozen=True)
class ConfluenceFeatures:
    asset: str
    timeframe: str
    side: SignalSide
    setup_type: SetupType

    price: float
    atr: float

    ema20: float
    ema50: float
    ema200: float

    rsi: float
    macd_hist: float
    macd_hist_prev: float

    volume: float
    volume_ratio: float

    # Key levels used by TP/SL + entry-range formatting.
    key_level: float
    breakout_level: Optional[float]

    # Diagnostics / confluence evidence.
    confluence_hits: tuple[str, ...]
    pre_confidence: float  # 0..1
    adx: Optional[float]


def _volume_ratio(volumes: list[float], lookback: int) -> float:
    if len(volumes) < lookback + 1:
        return 1.0
    prev = volumes[-(lookback + 1) : -1]
    avg = sum(prev) / max(len(prev), 1)
    if avg <= 0:
        return 1.0
    return volumes[-1] / avg


def _find_pivots(values: list[float], *, is_high: bool) -> list[tuple[int, float]]:
    """
    Simple local-extrema pivots.
    - pivot high: v[i] > v[i-1] and v[i] > v[i+1]
    - pivot low:  v[i] < v[i-1] and v[i] < v[i+1]
    """

    if len(values) < 3:
        return []

    pivots: list[tuple[int, float]] = []
    for i in range(1, len(values) - 1):
        prev_v = values[i - 1]
        curr_v = values[i]
        next_v = values[i + 1]
        if is_high and curr_v > prev_v and curr_v > next_v:
            pivots.append((i, curr_v))
        if not is_high and curr_v < prev_v and curr_v < next_v:
            pivots.append((i, curr_v))
    return pivots


def _swing_structure_ok(highs: list[float], lows: list[float], *, side: SignalSide) -> bool:
    """
    Validate HH/HL (up) or LH/LL (down) using last two pivots.
    """

    # Limit the analysis window to reduce noise and false pivots.
    window = min(80, len(highs))
    highs_w = highs[-window:]
    lows_w = lows[-window:]

    piv_highs = _find_pivots(highs_w, is_high=True)
    piv_lows = _find_pivots(lows_w, is_high=False)

    if len(piv_highs) < 2 or len(piv_lows) < 2:
        return False

    # Use the last 2 pivots of each type (already in chronological order).
    last2_highs = piv_highs[-2:]
    last2_lows = piv_lows[-2:]

    h1, h2 = last2_highs[0][1], last2_highs[1][1]
    l1, l2 = last2_lows[0][1], last2_lows[1][1]

    if side == "BUY":
        return h2 > h1 and l2 > l1
    # SELL
    return h2 < h1 and l2 < l1


def evaluate_confluence_pre_gates(
    candle_list: CandleList,
    *,
    adx_trend_threshold: float = 25.0,
    volume_multiplier: float = 1.5,
    touch_tolerance_pct: float = 0.0025,  # 0.25%
    min_confluence_hits: int = 3,
) -> Optional[ConfluenceFeatures]:
    """
    Strict pre-gates:
    - EMA alignment (20/50/200)
    - HH/HL or LH/LL swing structure
    - Non-sideways filter using ADX/regime detection
    - Detect allowed setups + confluence evidence (2-3 hits minimum)
    """

    closes = candle_list.closes
    highs = candle_list.highs
    lows = candle_list.lows
    volumes = candle_list.volumes

    required_len = 205  # EMA200 needs ~200 closes
    if len(closes) < required_len:
        return None

    # --- Non-sideways filter (must be trending) ---
    regime_detector = MarketRegimeDetector()
    regime_result = regime_detector.detect(candle_list)
    if regime_result.regime == MarketRegime.RANGING or regime_result.regime == MarketRegime.VOLATILE:
        return None
    if regime_result.adx is None or regime_result.adx < adx_trend_threshold:
        return None

    # --- Trend alignment EMA stack (20/50/200) ---
    ema20_ind = EMA(period=20)
    ema50_ind = EMA(period=50)
    ema200_ind = EMA(period=200)
    ema20_ind.calculate(closes)
    ema50_ind.calculate(closes)
    ema200_ind.calculate(closes)

    ema20 = ema20_ind.latest_value
    ema50 = ema50_ind.latest_value
    ema200 = ema200_ind.latest_value
    if ema20 is None or ema50 is None or ema200 is None:
        return None

    side: Optional[SignalSide] = None
    if ema20 > ema50 > ema200:
        side = "BUY"
    elif ema20 < ema50 < ema200:
        side = "SELL"
    else:
        return None

    # --- Swing structure HH/HL vs LH/LL ---
    if not _swing_structure_ok(highs, lows, side=side):
        return None

    # --- Indicators: RSI + MACD histogram direction ---
    rsi_ind = RSI(period=14)
    rsi_ind.calculate(closes)
    rsi = rsi_ind.latest_value
    prev_rsi = rsi_ind.previous_value
    if rsi is None or prev_rsi is None:
        return None

    macd_ind = MACD()
    macd_ind.calculate(closes)
    hist = macd_ind.histogram
    if len(hist) < 2:
        return None
    macd_hist = hist[-1]
    macd_hist_prev = hist[-2]

    # --- Volatility + volume spike ---
    atr_ind = ATR(period=14)
    atr_values = atr_ind.calculate_from_ohlc(highs, lows, closes)
    if not atr_values:
        return None
    atr = float(atr_values[-1])

    volume_ratio = _volume_ratio(volumes, lookback=20)
    current_volume = float(volumes[-1])
    price = float(closes[-1])

    # --- Allowed setups + confluence evidence ---
    confluence_hits: list[str] = []

    # 1) Trend alignment
    confluence_hits.append("ema_alignment")

    # 2) Indicator confirmation (RSI + MACD)
    if side == "BUY":
        # Avoid overbought and require momentum turn
        indicator_ok = 35 <= rsi <= 65 and rsi >= prev_rsi and macd_hist > 0
    else:
        indicator_ok = 35 <= rsi <= 65 and rsi <= prev_rsi and macd_hist < 0
    if indicator_ok:
        confluence_hits.append("rsi_macd_confirmation")

    # 3) Volume spike
    if volume_ratio >= volume_multiplier:
        confluence_hits.append("volume_spike")

    # 4) Key level reaction (pullback touch OR breakout level break)
    lookback = 20
    prev_high = max(highs[-(lookback + 1) : -1]) if len(highs) > lookback + 1 else price
    prev_low = min(lows[-(lookback + 1) : -1]) if len(lows) > lookback + 1 else price

    pullback_touch = False
    breakout_break = False

    if side == "BUY":
        pullback_touch = abs(price - ema50) / ema50 <= touch_tolerance_pct
        breakout_break = price > prev_high
    else:
        pullback_touch = abs(price - ema50) / ema50 <= touch_tolerance_pct
        breakout_break = price < prev_low

    key_level: float
    breakout_level: Optional[float] = None

    setup_type: Optional[SetupType] = None
    if pullback_touch:
        confluence_hits.append("key_level_reaction_pullback")
        setup_type = "trend_pullback"
        key_level = ema50
    elif breakout_break:
        confluence_hits.append("key_level_reaction_breakout")
        setup_type = "volume_breakout"
        key_level = prev_high if side == "BUY" else prev_low
        breakout_level = key_level
    else:
        # Support/resistance reversal fallback: near most recent pivot high/low.
        # (Still strict: requires a meaningful pivot proximity and indicator confirmation.)
        piv_highs = _find_pivots(highs[-80:], is_high=True)
        piv_lows = _find_pivots(lows[-80:], is_high=False)
        if side == "BUY" and piv_lows:
            last_pivot_low = piv_lows[-1][1]
            near_level = abs(price - last_pivot_low) / last_pivot_low <= touch_tolerance_pct
            if near_level:
                confluence_hits.append("key_level_reaction_reversal")
                setup_type = "support_resistance_reversal"
                key_level = last_pivot_low
        elif side == "SELL" and piv_highs:
            last_pivot_high = piv_highs[-1][1]
            near_level = abs(price - last_pivot_high) / last_pivot_high <= touch_tolerance_pct
            if near_level:
                confluence_hits.append("key_level_reaction_reversal")
                setup_type = "support_resistance_reversal"
                key_level = last_pivot_high
        else:
            return None

    if len(confluence_hits) < min_confluence_hits or setup_type is None:
        return None

    # Pre-confidence heuristic (0..1): more confluence hits and stronger volume ratio.
    pre_conf = min(0.95, 0.45 + (len(confluence_hits) * 0.12) + (max(0.0, volume_ratio - 1.0) * 0.05))

    return ConfluenceFeatures(
        asset=candle_list.symbol,
        timeframe=candle_list.timeframe,
        side=side,
        setup_type=setup_type,
        price=price,
        atr=atr,
        ema20=float(ema20),
        ema50=float(ema50),
        ema200=float(ema200),
        rsi=float(rsi),
        macd_hist=float(macd_hist),
        macd_hist_prev=float(macd_hist_prev),
        volume=current_volume,
        volume_ratio=float(volume_ratio),
        key_level=float(key_level),
        breakout_level=float(breakout_level) if breakout_level is not None else None,
        confluence_hits=tuple(confluence_hits),
        pre_confidence=float(pre_conf),
        adx=regime_result.adx,
    )

