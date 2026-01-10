from typing import Dict, Any
import pandas as pd


def format_post_insights(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format Facebook post data into structured insights"""
    likes_count = post_data.get('likes', {}).get('summary', {}).get('total_count', 0)
    comments_count = post_data.get('comments', {}).get('summary', {}).get('total_count', 0)
    shares_count = post_data.get('shares', {}).get('count', 0)
    reactions_count = post_data.get('reactions', {}).get('summary', {}).get('total_count', 0)
    
    reactions_breakdown = {}
    reactions_data = post_data.get('reactions', {}).get('data', [])
    
    for reaction in reactions_data:
        reaction_type = reaction.get('type', '').lower()
        if reaction_type:
            reactions_breakdown[reaction_type] = reactions_breakdown.get(reaction_type, 0) + 1
    
    message = post_data.get('message', '')
    truncated_message = message[:200] + '...' if len(message) > 200 else message
    
    return {
        "post_id": post_data.get('id'),
        "message": truncated_message,
        "created_time": post_data.get('created_time'),
        "permalink": post_data.get('permalink_url'),
        "type": post_data.get('type'),
        "engagement": {
            "likes": likes_count,
            "comments": comments_count,
            "shares": shares_count,
            "reactions": reactions_count,
            "total_engagement": likes_count + comments_count + shares_count
        },
        "reactions_breakdown": reactions_breakdown
    }


def format_ad_insights(raw_data: list) -> Dict[str, Any]:
    """Format Facebook ad insights data with CTR calculations"""
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        return []
    
    df['clicks'] = pd.to_numeric(df.get('clicks', 0), errors='coerce').fillna(0)
    df['impressions'] = pd.to_numeric(df.get('impressions', 0), errors='coerce').fillna(0)
    df['spend'] = pd.to_numeric(df.get('spend', 0), errors='coerce').fillna(0)
    
    df['ctr'] = df.apply(
        lambda row: (row['clicks'] / row['impressions'] * 100) if row['impressions'] > 0 else 0,
        axis=1
    )
    
    return df.to_dict(orient="records")

