"""
Data Fetcher - Main data collection and management module
"""

import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from src.data.binance_client import BinanceClient, BinanceAPIError
from src.data.models import Candle, CandleList
from config.constants import CRYPTO_PAIRS, TIMEFRAMES, MIN_CANDLES_FOR_ANALYSIS
from config.settings import settings

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Centralized module for fetching and managing market data
    Handles caching, rate limiting, and data validation
    """

    def __init__(self):
        """Initialize data fetcher"""
        self.binance_client = BinanceClient()
        self.candle_cache: Dict[str, Dict[str, CandleList]] = {}
        self.last_fetch_time: Dict[str, float] = {}
        self.min_candles = MIN_CANDLES_FOR_ANALYSIS

        logger.info("DataFetcher initialized")

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        from_cache: bool = True,
        min_candles: Optional[int] = None
    ) -> CandleList:
        """
        Fetch candlestick data for a symbol
        
        Args:
            symbol: Crypto symbol (e.g., "BTC")
            timeframe: Timeframe (e.g., "15m")
            limit: Number of candles to fetch
            from_cache: Use cached data if available
            min_candles: Minimum candles required (overrides default)
        
        Returns:
            CandleList object with candles
        """
        # Validate inputs
        if symbol not in CRYPTO_PAIRS:
            raise ValueError(f"Unsupported symbol: {symbol}")
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        # Check cache
        cache_key = f"{symbol}_{timeframe}"
        if from_cache and cache_key in self.candle_cache:
            # Check if cached data has enough candles if min_candles specified
            cached_data = self.candle_cache[cache_key]
            required = min_candles if min_candles is not None else self.min_candles.get(timeframe, 20)
            if len(cached_data) >= required:
                logger.debug(f"Using cached data for {cache_key}")
                return cached_data

        try:
            # Fetch from Binance
            pair = CRYPTO_PAIRS[symbol]
            candles = await self.binance_client.get_klines(
                symbol=pair,
                interval=timeframe,
                limit=limit
            )

            required = min_candles if min_candles is not None else self.min_candles.get(timeframe, 20)
            if len(candles) < required:
                raise ValueError(f"Insufficient candles for {timeframe}: {len(candles)} (required: {required})")

            # Create CandleList
            candle_list = CandleList(symbol=symbol, timeframe=timeframe, candles=candles)

            # Cache the data
            self.candle_cache[cache_key] = candle_list
            self.last_fetch_time[cache_key] = datetime.utcnow().timestamp()

            logger.info(f"Fetched {len(candles)} candles for {symbol} {timeframe}")
            return candle_list

        except BinanceAPIError as e:
            logger.error(f"Binance API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching candles: {str(e)}")
            raise

    async def fetch_all_symbols(
        self,
        timeframe: str = "15m",
        limit: int = 100
    ) -> Dict[str, CandleList]:
        """
        Fetch candles for all supported symbols
        
        Args:
            timeframe: Timeframe to fetch
            limit: Number of candles per symbol
        
        Returns:
            Dictionary of symbol -> CandleList
        """
        results = {}
        symbols = list(CRYPTO_PAIRS.keys())
        
        logger.info(f"Fetching candles for {len(symbols)} symbols")

        # Fetch in parallel with rate limit
        tasks = [
            self.fetch_candles(symbol, timeframe, limit)
            for symbol in symbols
        ]

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, result in zip(symbols, results_list):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbol}: {str(result)}")
            else:
                results[symbol] = result

        logger.info(f"Successfully fetched {len(results)}/{len(symbols)} symbols")
        return results

    async def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol
        
        Args:
            symbol: Crypto symbol (e.g., "BTC")
        
        Returns:
            Current price as float
        """
        if symbol not in CRYPTO_PAIRS:
            raise ValueError(f"Unsupported symbol: {symbol}")

        try:
            pair = CRYPTO_PAIRS[symbol]
            price = await self.binance_client.get_avg_price(pair)
            logger.debug(f"Current price of {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            raise

    async def test_connection(self) -> bool:
        """Test connection to Binance API"""
        try:
            is_connected = await self.binance_client.ping()
            if is_connected:
                logger.info("Successfully connected to Binance API")
            else:
                logger.error("Failed to connect to Binance API")
            return is_connected
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Clear cache for specific symbol/timeframe or all
        
        Args:
            symbol: Specific symbol to clear (None = all)
            timeframe: Specific timeframe to clear (None = all)
        """
        if symbol and timeframe:
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.candle_cache:
                del self.candle_cache[cache_key]
                logger.info(f"Cleared cache for {cache_key}")
        elif symbol:
            keys_to_delete = [k for k in self.candle_cache if k.startswith(symbol)]
            for k in keys_to_delete:
                del self.candle_cache[k]
            logger.info(f"Cleared cache for {symbol}")
        else:
            self.candle_cache.clear()
            logger.info("Cleared all candle cache")

    async def close(self):
        """Close connections"""
        await self.binance_client.close()
        logger.info("DataFetcher closed")
