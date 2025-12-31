"""
Withings Token Guardian MCP

A standalone service that manages Withings OAuth token refresh.
Receives webhook calls from Withings MCP when 401 errors occur.
"""

import os
import httpx
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Withings Token Guardian MCP",
    description="Manages Withings OAuth token refresh via webhook",
    version="1.0.0"
)

# Environment variables
WITHINGS_MCP_URL = os.getenv("WITHINGS_MCP_URL", "https://withings-mcp-production.up.railway.app")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "")
GUARDIAN_SECRET = os.getenv("GUARDIAN_SECRET", "")  # Secret for webhook authentication
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN", "")  # Railway API token for updating env vars
RAILWAY_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID", "")
RAILWAY_SERVICE_ID = os.getenv("RAILWAY_SERVICE_ID", "")  # Withings MCP service ID


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Withings Token Guardian MCP",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "withings_mcp_url": WITHINGS_MCP_URL
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "config": {
            "withings_mcp_configured": bool(WITHINGS_MCP_URL),
            "admin_token_configured": bool(ADMIN_API_TOKEN),
            "guardian_secret_configured": bool(GUARDIAN_SECRET),
            "railway_token_configured": bool(RAILWAY_TOKEN),
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/refresh-needed")
async def refresh_needed(
    request: Request,
    x_guardian_secret: Optional[str] = Header(None)
):
    """
    Webhook endpoint called by Withings MCP when 401 error occurs.
    Triggers token refresh and returns success/failure.
    
    Headers:
        X-Guardian-Secret: Secret token for authentication
    
    Returns:
        success: bool
        message: str
        timestamp: str
    """
    # Verify webhook secret
    if GUARDIAN_SECRET and x_guardian_secret != GUARDIAN_SECRET:
        logger.warning(f"Unauthorized refresh attempt from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid guardian secret")
    
    logger.info("🔄 Token refresh webhook triggered")
    
    try:
        # Call Withings MCP admin refresh endpoint
        refresh_result = await refresh_withings_token()
        
        if refresh_result["success"]:
            logger.info("✅ Token refresh successful")
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "expires_at": refresh_result.get("expires_at"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            logger.error(f"❌ Token refresh failed: {refresh_result.get('error')}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Token refresh failed",
                    "error": refresh_result.get("error"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    except Exception as e:
        logger.error(f"❌ Exception during token refresh: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Token refresh exception",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.post("/refresh")
async def manual_refresh(
    x_admin_token: Optional[str] = Header(None)
):
    """
    Manual token refresh endpoint.
    Can be called directly for testing or manual refresh.
    
    Headers:
        X-Admin-Token: Admin API token for authentication
    """
    if GUARDIAN_SECRET and x_admin_token != GUARDIAN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    
    logger.info("🔧 Manual token refresh triggered")
    
    try:
        refresh_result = await refresh_withings_token()
        
        if refresh_result["success"]:
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "expires_at": refresh_result.get("expires_at"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Token refresh failed",
                    "error": refresh_result.get("error")
                }
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Exception during refresh",
                "error": str(e)
            }
        )


async def refresh_withings_token() -> dict:
    """
    Call Withings MCP admin refresh endpoint.
    
    Returns:
        dict with success status and details
    """
    if not ADMIN_API_TOKEN:
        return {
            "success": False,
            "error": "ADMIN_API_TOKEN not configured"
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{WITHINGS_MCP_URL}/admin/token/refresh",
                headers={"X-Admin-Token": ADMIN_API_TOKEN}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Token refresh successful, expires at: {data.get('expires_at')}")
                return {
                    "success": True,
                    "expires_at": data.get("expires_at"),
                    "expires_in_seconds": data.get("expires_in_seconds")
                }
            else:
                error_text = response.text
                logger.error(f"Token refresh failed: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}"
                }
    
    except Exception as e:
        logger.error(f"Error calling Withings MCP: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
