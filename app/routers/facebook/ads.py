from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.services.facebook.ads import AdsService
from app.repositories.facebook_session import FacebookSessionRepository
from app.database import get_session_local
from app.utils.facebook.formatters import format_ad_insights

router = APIRouter(prefix="/facebook/insights", tags=["Facebook Ads"])


@router.get("/{account_id}")
async def get_facebook_insights(account_id: str, session_id: str | None = None, token: str | None = None):
    """Get Facebook ad insights for an account"""
    if session_id:
        db = get_session_local()()
        try:
            repo = FacebookSessionRepository(db)
            session = repo.get_by_session_id(session_id)
            if not session or session.expires_at.replace(tzinfo=None) < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            access_token = session.access_token
        finally:
            db.close()
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
                    "total_spend": 0,
                },
                "message": "No ad data found for this account",
            }

        return {
            "account_id": account_id,
            "insights": clean_data,
            "summary": {
                "total_rows": len(clean_data),
                "average_ctr": sum(d['ctr'] for d in clean_data) / len(clean_data),
                "total_clicks": sum(d.get('clicks', 0) for d in clean_data),
                "total_impressions": sum(d.get('impressions', 0) for d in clean_data),
                "total_spend": sum(d.get('spend', 0) for d in clean_data),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights: {str(e)}")
