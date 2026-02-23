from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.facebook.pages import PagesService
from app.services.facebook.posts import PostsService
from app.services.facebook.insights import InsightsService
from app.services.session_storage import get_session_storage
from app.utils.facebook.formatters import format_post_insights
from app.config import get_settings

router = APIRouter(prefix="/facebook", tags=["Facebook Pages"])

settings = get_settings()
session_store = get_session_storage(settings.session_storage)


@router.get("/pages")
async def get_pages(session_id: str):
    """Get all Facebook Pages the user manages"""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    pages_service = PagesService(access_token=session["access_token"])
    
    try:
        pages_data = await pages_service.fetch_pages()
        pages = pages_data.get('data', [])
        
        return {
            "user_id": session["user_id"],
            "user_name": session["user_name"],
            "total_pages": len(pages),
            "pages": pages
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch pages: {str(e)}")


@router.get("/pages/{page_id}/posts")
async def get_page_posts(page_id: str, session_id: str, limit: int = 25, page_token: Optional[str] = None):
    """Get posts from a specific Facebook Page with engagement metrics"""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if limit > 100:
        limit = 100
    
    access_token = page_token if page_token else session["access_token"]
    pages_service = PagesService(access_token=access_token)
    
    try:
        posts_data = await pages_service.fetch_page_posts(page_id, limit)
        posts = posts_data.get('data', [])
        
        if 'error' in posts_data:
            error = posts_data['error']
            return {
                "page_id": page_id,
                "total_posts": 0,
                "posts": [],
                "error": error.get('message', 'Unknown error'),
                "error_code": error.get('code')
            }
        
        # Transform posts to include engagement data
        transformed_posts = []
        for post in posts:
            likes_count = post.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments_count = post.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares_count = post.get('shares', {}).get('count', 0)
            reactions_count = post.get('reactions', {}).get('summary', {}).get('total_count', 0)
            
            transformed_post = {
                'id': post.get('id'),
                'message': post.get('message', ''),
                'story': post.get('story', ''),
                'created_time': post.get('created_time'),
                'permalink_url': post.get('permalink_url'),
                'engagement': {
                    'likes': likes_count,
                    'comments': comments_count,
                    'shares': shares_count,
                    'reactions': reactions_count,
                    'total': likes_count + comments_count + shares_count
                }
            }
            transformed_posts.append(transformed_post)
        
        return {
            "page_id": page_id,
            "total_posts": len(transformed_posts),
            "posts": transformed_posts,
            "paging": posts_data.get('paging', {})
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch posts: {str(e)}")


@router.get("/posts/{post_id}/insights")
async def get_post_insights(post_id: str, session_id: str, page_token: Optional[str] = None):
    """Get insights for a specific Facebook post"""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if not post_id or '_' not in post_id:
        raise HTTPException(status_code=400, detail=f"Invalid post ID format: '{post_id}'")
    
    access_token = page_token if page_token else session["access_token"]
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    posts_service = PostsService(access_token=access_token)
    
    try:
        post_data = await posts_service.fetch_post_insights(post_id)
        formatted_insights = format_post_insights(post_data)
        
        if not formatted_insights.get('post_id'):
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "success": True,
            "data": formatted_insights,
            "message": "Post insights retrieved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        
        if "400" in error_message and "Bad Request" in error_message:
            raise HTTPException(status_code=400, detail=f"Invalid post ID or the post cannot be accessed")
        elif "permission" in error_message.lower() or "oauth" in error_message.lower():
            raise HTTPException(status_code=403, detail="Permission denied")
        elif "not found" in error_message.lower() or "404" in error_message:
            raise HTTPException(status_code=404, detail="Post not found")
        else:
            raise HTTPException(status_code=400, detail=f"Failed to fetch post insights: {error_message}")


@router.get("/pages/{page_id}/insights")
async def get_page_insights(page_id: str, session_id: str, page_token: Optional[str] = None):
    """
    Get basic insights for a Facebook Page
    
    Returns basic page information without time period
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    access_token = page_token if page_token else session["access_token"]
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    insights_service = InsightsService(access_token=access_token)
    
    try:
        insights_data = await insights_service.fetch_page_basic_info(page_id)
        
        return {
            "success": True,
            "data": insights_data,
            "message": "Page insights retrieved successfully"
        }
    except Exception as e:
        error_message = str(e)
        
        if "permission" in error_message.lower() or "oauth" in error_message.lower():
            raise HTTPException(
                status_code=403, 
                detail="Permission denied. Make sure the page access token has proper permissions."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Failed to fetch page insights: {error_message}")



@router.get("/pages/{page_id}/messaging-insights")
async def get_page_messaging_insights(page_id: str, session_id: str, page_token: Optional[str] = None, days: int = 7):
    """
    Get messaging-specific insights for a Facebook Page
    
    Returns audience, responsiveness, conversations, and outcomes metrics for messaging
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days parameter must be between 1 and 90")
    
    access_token = page_token if page_token else session["access_token"]
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    insights_service = InsightsService(access_token=access_token)
    
    try:
        insights_data = await insights_service.fetch_messaging_insights(page_id, days=days)
        
        return {
            "success": True,
            "data": insights_data,
            "message": "Messaging insights retrieved successfully"
        }
    except Exception as e:
        error_message = str(e)
        
        if "permission" in error_message.lower() or "oauth" in error_message.lower():
            raise HTTPException(
                status_code=403, 
                detail="Permission denied. Make sure the page access token has pages_messaging and read_insights permissions."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Failed to fetch messaging insights: {error_message}")


