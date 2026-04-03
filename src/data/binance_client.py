"""
Binance API Client Wrapper
Handles all Binance API interactions including REST and WebSocket
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import time
from config.settings import settings
from config.constants import CRYPTO_PAIRS, TIMEFRAMES
from src.data.models import Candle, CandleList
import hashlib
import hmac
import urllib.parse

logger = logging.getLogger(__name__)


class BinanceAPIError(Exception):
    """Custom exception for Binance API errors"""
    pass


class BinanceClient:
    """
    Binance API Client for fetching cryptocurrency market data
    Supports both REST API and WebSocket connections
    """

    def __init__(self):
        """Initialize Binance client with API credentials"""
        self.testnet = settings.BINANCE_TESTNET
        if self.testnet:
            self.api_key = settings.BINANCE_TESTNET_API_KEY or settings.BINANCE_API_KEY
            self.api_secret = settings.BINANCE_TESTNET_API_SECRET or settings.BINANCE_API_SECRET
        else:
            self.api_key = settings.BINANCE_API_KEY
            self.api_secret = settings.BINANCE_API_SECRET

        # API URLs
        if self.testnet:
            self.base_url = "https://testnet.binance.vision/api"
            self.ws_url = "wss://stream.testnet.binance.vision:9443/ws"
        else:
            self.base_url = "https://api.binance.com/api"
            self.ws_url = "wss://stream.binance.com:9443/ws"

        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections = {}
        
        logger.info(f"Binance client initialized (Testnet: {self.testnet})")

    async def _init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def _sign_request(self, params: Dict) -> str:
        """Sign request with API secret"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Candle]:
        """
        Fetch historical candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Timeframe (e.g., "15m", "1h")
            limit: Number of candles to fetch (max 1000)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
        
        Returns:
            List of Candle objects
        """
        await self._init_session()

        if limit > 1000:
            limit = 1000

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        try:
            async with self.session.get(
                f"{self.base_url}/v3/klines",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise BinanceAPIError(f"Binance API error: {resp.status}")

                data = await resp.json()
                candles = []

                for kline in data:
                    candle = Candle(
                        timestamp=int(kline[0]),
                        open=float(kline[1]),
                        high=float(kline[2]),
                        low=float(kline[3]),
                        close=float(kline[4]),
                        volume=float(kline[5]),
                        quote_asset_volume=float(kline[7]),
                        number_of_trades=int(kline[8]),
                        taker_buy_base_asset_volume=float(kline[9]),
                        taker_buy_quote_asset_volume=float(kline[10]),
                    )
                    candles.append(candle)

                logger.debug(f"Fetched {len(candles)} candles for {symbol} {interval}")
                return candles

        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching klines for {symbol}")
            raise BinanceAPIError(f"Request timeout for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching klines: {str(e)}")
            raise BinanceAPIError(f"Error fetching klines: {str(e)}")

    async def get_ticker(self, symbol: str) -> Dict:
        """
        Get 24hr ticker price change statistics
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
        
        Returns:
            Dict with ticker information
        """
        await self._init_session()

        try:
            async with self.session.get(
                f"{self.base_url}/v3/ticker/24hr",
                params={"symbol": symbol},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise BinanceAPIError(f"Binance API error: {resp.status}")

                data = await resp.json()
                logger.debug(f"Fetched ticker for {symbol}")
                return data

        except Exception as e:
            logger.error(f"Error fetching ticker: {str(e)}")
            raise BinanceAPIError(f"Error fetching ticker: {str(e)}")

    async def get_avg_price(self, symbol: str) -> float:
        """
        Get current average price
        
        Args:
            symbol: Trading pair
        
        Returns:
            Average price as float
        """
        await self._init_session()

        try:
            async with self.session.get(
                f"{self.base_url}/v3/avgPrice",
                params={"symbol": symbol},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise BinanceAPIError(f"Binance API error: {resp.status}")

                data = await resp.json()
                return float(data["price"])

        except Exception as e:
            logger.error(f"Error fetching avg price: {str(e)}")
            raise BinanceAPIError(f"Error fetching avg price: {str(e)}")

    async def get_exchange_info(self) -> Dict:
        """
        Get exchange information
        
        Returns:
            Exchange information dict
        """
        await self._init_session()

        try:
            async with self.session.get(
                f"{self.base_url}/v3/exchangeInfo",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise BinanceAPIError(f"Binance API error: {resp.status}")

                return await resp.json()

        except Exception as e:
            logger.error(f"Error fetching exchange info: {str(e)}")
            raise BinanceAPIError(f"Error fetching exchange info: {str(e)}")

    async def ping(self) -> bool:
        """Test API connectivity"""
        await self._init_session()

        try:
            async with self.session.get(
                f"{self.base_url}/v3/ping",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200

        except Exception as e:
            logger.error(f"Ping failed: {str(e)}")
            return False
