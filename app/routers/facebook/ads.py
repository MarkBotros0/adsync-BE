from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.facebook.ads import AdsService
from app.services.session_storage import get_session_storage
from app.utils.facebook.formatters import format_ad_insights
from app.config import get_settings

router = APIRouter(prefix="/facebook/insights", tags=["Facebook Ads"])

settings = get_settings()
session_store = get_session_storage(settings.session_storage)


@router.get("/{account_id}")
async def get_facebook_insights(account_id: str, session_id: Optional[str] = None, token: Optional[str] = None):
    """Get Facebook ad insights for an account"""
    if session_id:
        session = session_store.get(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        access_token = session["access_token"]
    elif token:
        access_token = token
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    ads_service = AdsService(access_token=access_token)

    try:
        raw_data = await ads_service.fetch_ad_insights(account_id)
        clean_data = format_ad_insights(raw_data.get('data', []))
        
        if not clean_data:
            return {
                "account_id": account_id,
                "insights": [],
                "summary": {
                    "total_rows": 0,
                    "average_ctr": 0,
                    "total_clicks": 0,
                    "total_impressions": 0,
                    "total_spend": 0
                },
                "message": "No ad data found for this account"
            }

        return {
            "account_id": account_id,
            "insights": clean_data,
            "summary": {
                "total_rows": len(clean_data),
                "average_ctr": sum(d['ctr'] for d in clean_data) / len(clean_data),
                "total_clicks": sum(d.get('clicks', 0) for d in clean_data),
                "total_impressions": sum(d.get('impressions', 0) for d in clean_data),
                "total_spend": sum(d.get('spend', 0) for d in clean_data)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights: {str(e)}")

