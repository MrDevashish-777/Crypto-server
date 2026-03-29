"""
News Fetcher Service
Fetches latest crypto news from RSS feeds
"""

import logging
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "cryptopanic": "https://cryptopanic.com/news/rss",
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
}

class NewsFetcher:
    """Service to fetch and parse crypto news from various RSS feeds"""

    def __init__(self):
        self.timeout = 10.0

    async def fetch_all_news(self, limit_per_feed: int = 10) -> List[Dict[str, Any]]:
        """Fetch news from all configured RSS feeds in parallel"""
        tasks = []
        for source, url in RSS_FEEDS.items():
            tasks.append(self.fetch_feed(source, url, limit_per_feed))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Error fetching feed: {str(res)}")
        
        # Sort by published date (descending)
        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return all_news

    async def fetch_feed(self, source: str, url: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self.parse_rss(source, response.text, limit)
        except Exception as e:
            logger.error(f"Failed to fetch {source} feed from {url}: {str(e)}")
            return []

    def parse_rss(self, source: str, xml_content: str, limit: int) -> List[Dict[str, Any]]:
        """Parse RSS XML content"""
        news_items = []
        try:
            root = ET.fromstring(xml_content)
            items = root.findall(".//item")
            
            for item in items[:limit]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                description = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")
                
                # Basic cleaning of description (remove HTML tags if any)
                # For simplicity, we just take the first 200 chars
                clean_description = description[:200] + "..." if len(description) > 200 else description

                news_items.append({
                    "title": title,
                    "link": link,
                    "description": clean_description,
                    "published_at": pub_date,
                    "source": source,
                })
        except Exception as e:
            logger.error(f"Error parsing RSS from {source}: {str(e)}")
            
        return news_items
