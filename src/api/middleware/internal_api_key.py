from fastapi import Header, HTTPException

from config.settings import settings


async def require_internal_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> None:
    """
    Protect internal endpoints (service-to-service) with an API key.
    """

    expected = settings.PLANITT_PROCESSOR_INTERNAL_API_KEY
    if not expected:
        raise HTTPException(status_code=500, detail="Processor internal API key not configured")

    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid internal API key")

