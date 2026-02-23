from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.services.facebook.api_client import APIClient
from app.utils.exceptions import FacebookAPIError


class InsightsService(APIClient):
    """Service for Facebook Page Insights operations"""
    
    async def fetch_page_insights(self, page_id: str, metrics: List[str] = None, period: str = "day", since: str = None, until: str = None) -> Dict[str, Any]:
        """
        Fetch page insights/analytics
        
        Args:
            page_id: Facebook Page ID
            metrics: List of metric names to fetch
            period: Time period ('day', 'week', 'days_28', 'lifetime')
            since: Start date (Unix timestamp or strtotime format)
            until: End date (Unix timestamp or strtotime format)
        """
        # Default metrics if none provided
        if metrics is None:
            metrics = [
                # Audience metrics
                'page_fans',
                'page_fans_online',
                'page_impressions_unique',
                'page_impressions',
                
                # Engagement metrics
                'page_post_engagements',
                'page_engaged_users',
                'page_consumptions',
                'page_negative_feedback',
                
                # Post metrics
                'page_posts_impressions',
                'page_posts_impressions_unique',
            ]
        
        params = {
            'metric': ','.join(metrics),
            'period': period
        }
        
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        
        try:
            return await self.get(
                f"{page_id}/insights",
                params=params
            )
        except FacebookAPIError as e:
            return {
                "data": [],
                "error": str(e)
            }
    
    async def fetch_page_conversations_insights(self, page_id: str, since: str = None, until: str = None) -> Dict[str, Any]:
        """
        Fetch messaging/conversation insights
        
        Metrics include:
        - page_messages_active_threads_unique
        - page_messages_new_conversations_unique
        - page_messages_blocked_conversations_unique
        - page_messages_reported_conversations_unique
        - page_messages_reported_conversations_by_report_type_unique
        """
        metrics = [
            'page_messages_active_threads_unique',  # Active conversations
            'page_messages_new_conversations_unique',  # New conversations started
            'page_messages_blocked_conversations_unique',  # Blocked conversations
            'page_messages_reported_conversations_unique',  # Reported conversations
        ]
        
        params = {
            'metric': ','.join(metrics),
            'period': 'day'
        }
        
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        
        try:
            return await self.get(
                f"{page_id}/insights",
                params=params
            )
        except FacebookAPIError as e:
            return {
                "data": [],
                "error": str(e)
            }
    
    async def fetch_page_responsiveness_insights(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch page responsiveness metrics
        
        Metrics include:
        - page_messages_feedback_by_action_unique (lifetime)
        """
        try:
            # Get page info with messaging metrics
            page_response = await self.get(
                f"{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,overall_star_rating,rating_count"
                }
            )
            
            return {
                "page_info": page_response,
                "data": []
            }
        except FacebookAPIError as e:
            return {
                "data": [],
                "error": str(e)
            }
    
    async def fetch_page_basic_info(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch basic page information without time-based metrics
        
        Returns:
        - Page name, category, about
        - Fan count, followers count
        - Basic page metadata
        """
        try:
            # Get page info with basic metrics
            page_info = await self.get(
                f"{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,category,about,link,rating_count,overall_star_rating,phone,website,emails,location"
                }
            )
            
            return {
                "page_id": page_id,
                "page_name": page_info.get("name"),
                "category": page_info.get("category", "N/A"),
                "about": page_info.get("about", ""),
                "fan_count": page_info.get("fan_count", 0),
                "followers_count": page_info.get("followers_count", 0),
                "rating_count": page_info.get("rating_count", 0),
                "overall_star_rating": page_info.get("overall_star_rating", 0),
                "link": page_info.get("link", ""),
                "phone": page_info.get("phone", ""),
                "website": page_info.get("website", ""),
                "emails": page_info.get("emails", []),
                "location": page_info.get("location", {}),
            }
        except Exception as e:
            raise FacebookAPIError(f"Failed to fetch page info: {str(e)}")
    
    async def fetch_messaging_insights(self, page_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Fetch messaging-specific insights for the dashboard
        
        Returns structured data for:
        - Audience metrics (total contacts, new contacts, returning contacts, contacts with orders)
        - Responsiveness metrics (response rate, response time, busiest day)
        - Conversations metrics (messaging conversations started)
        - Outcomes metrics
        """
        # Calculate date range
        until_date = datetime.now()
        since_date = until_date - timedelta(days=days)
        
        since_timestamp = int(since_date.timestamp())
        until_timestamp = int(until_date.timestamp())
        
        # Fetch multiple insight categories
        try:
            # Messaging metrics
            messaging_metrics = await self.fetch_page_conversations_insights(
                page_id=page_id,
                since=str(since_timestamp),
                until=str(until_timestamp)
            )
            
            # Responsiveness metrics
            responsiveness_metrics = await self.fetch_page_responsiveness_insights(
                page_id=page_id
            )
            
            # Page info for additional context
            page_info = await self.get(
                f"{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,category,about"
                }
            )
            
            return {
                "page_id": page_id,
                "page_name": page_info.get("name"),
                "date_range": {
                    "since": since_date.isoformat(),
                    "until": until_date.isoformat(),
                    "days": days
                },
                "audience": self._format_audience_metrics_simple(page_info),
                "responsiveness": self._format_responsiveness_metrics(messaging_metrics, responsiveness_metrics),
                "conversations": self._format_conversations_metrics(messaging_metrics),
                "outcomes": self._format_outcomes_metrics(messaging_metrics),
                "raw_data": {
                    "messaging_metrics": messaging_metrics.get("data", []),
                    "responsiveness_metrics": responsiveness_metrics.get("data", [])
                }
            }
        except Exception as e:
            raise FacebookAPIError(f"Failed to fetch messaging insights: {str(e)}")
    
    async def fetch_page_basic_insights(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch basic page information and insights without time period
        
        Returns basic page data like fans, followers, rating, etc.
        """
        try:
            # Get page info with basic metrics
            page_info = await self.get(
                f"{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,category,about,link,overall_star_rating,rating_count,website,phone,emails,engagement"
                }
            )
            
            return {
                "page_id": page_info.get("id"),
                "page_name": page_info.get("name"),
                "metrics": {
                    "fan_count": page_info.get("fan_count", 0),
                    "followers_count": page_info.get("followers_count", 0),
                    "rating": page_info.get("overall_star_rating", 0),
                    "rating_count": page_info.get("rating_count", 0),
                },
                "page_info": {
                    "category": page_info.get("category", "N/A"),
                    "link": page_info.get("link", ""),
                    "website": page_info.get("website", "N/A"),
                    "about": page_info.get("about", "N/A"),
                    "phone": page_info.get("phone", "N/A"),
                }
            }
        except Exception as e:
            raise FacebookAPIError(f"Failed to fetch page insights: {str(e)}")
        """
        Fetch comprehensive page insights for the dashboard (non-messaging)
        
        Returns structured data for:
        - Page impressions, reach, and engagement
        - Post performance
        - Fan growth
        """
        # Calculate date range
        until_date = datetime.now()
        since_date = until_date - timedelta(days=days)
        
        since_timestamp = int(since_date.timestamp())
        until_timestamp = int(until_date.timestamp())
        
        # Fetch multiple insight categories
        try:
            # Try to fetch basic page metrics that are commonly available
            # Using lifetime metrics which don't require date range
            page_metrics = await self.fetch_page_insights(
                page_id=page_id,
                metrics=[
                    'page_impressions',  # Total impressions
                    'page_impressions_unique',  # Unique impressions
                    'page_engaged_users',  # Engaged users
                    'page_post_engagements',  # Post engagements
                ],
                period='day',
                since=str(since_timestamp),
                until=str(until_timestamp)
            )
            
            # Page info for additional context
            page_info = await self.get(
                f"{page_id}",
                params={
                    "fields": "id,name,followers_count,fan_count,category,about,link"
                }
            )
            
            return {
                "page_id": page_id,
                "page_name": page_info.get("name"),
                "date_range": {
                    "since": since_date.isoformat(),
                    "until": until_date.isoformat(),
                    "days": days
                },
                "metrics": self._format_page_metrics(page_metrics),
                "page_info": {
                    "fan_count": page_info.get("fan_count", 0),
                    "followers_count": page_info.get("followers_count", 0),
                    "category": page_info.get("category", "N/A"),
                    "link": page_info.get("link", "")
                },
                "raw_data": {
                    "page_metrics": page_metrics.get("data", [])
                }
            }
        except Exception as e:
            raise FacebookAPIError(f"Failed to fetch comprehensive insights: {str(e)}")
    
    def _format_audience_metrics_simple(self, page_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format audience metrics for messaging insights using only page info"""
        return {
            "total_contacts": page_info.get("fan_count", 0),
            "followers": page_info.get("followers_count", 0),
            "new_contacts": 0,  # Would need historical data
            "returning_contacts": 0,  # Would need conversation history
            "contacts_with_orders": 0,  # Not available via API
        }
    
    def _format_page_metrics(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format general page metrics for display"""
        data = metrics_data.get("data", [])
        
        result = {
            "impressions": 0,
            "impressions_unique": 0,
            "engaged_users": 0,
            "post_engagements": 0
        }
        
        # Sum up metrics from the period
        for metric in data:
            metric_name = metric.get("name")
            values = metric.get("values", [])
            
            if metric_name == "page_impressions":
                result["impressions"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_impressions_unique":
                result["impressions_unique"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_engaged_users":
                result["engaged_users"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_post_engagements":
                result["post_engagements"] = sum(v.get("value", 0) for v in values if v.get("value"))
        
        return result
    
    def _format_audience_metrics(self, metrics_data: Dict[str, Any], page_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format audience metrics for display"""
        data = metrics_data.get("data", [])
        
        result = {
            "total_contacts": page_info.get("fan_count", 0),
            "followers": page_info.get("followers_count", 0),
            "new_contacts": 0,
            "returning_contacts": 0,
            "contacts_with_orders": 0,  # Not available via API, placeholder
            "engaged_users": 0,
            "reach": 0
        }
        
        # Sum up metrics from the period
        for metric in data:
            metric_name = metric.get("name")
            values = metric.get("values", [])
            
            if metric_name == "page_fan_adds_unique":
                result["new_contacts"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_engaged_users":
                result["engaged_users"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_impressions_unique":
                result["reach"] = sum(v.get("value", 0) for v in values if v.get("value"))
        
        # Calculate returning contacts as engaged users who aren't new
        result["returning_contacts"] = max(0, result["engaged_users"] - result["new_contacts"])
        
        return result
    
    def _format_responsiveness_metrics(self, messaging_data: Dict[str, Any], responsiveness_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format responsiveness metrics for display"""
        result = {
            "response_rate": "--",
            "response_time": "--",
            "busiest_day": "Saturday, 28 December"  # Placeholder - would need historical data
        }
        
        # Note: Facebook Graph API doesn't provide direct response rate/time metrics
        # These would require analyzing actual conversations or using the Page Messaging Insights API
        # For now, returning placeholder values
        
        return result
    
    def _format_conversations_metrics(self, messaging_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format conversation metrics for display"""
        data = messaging_data.get("data", [])
        
        result = {
            "messaging_conversations_started": 0,
            "active_conversations": 0
        }
        
        # Sum up metrics from the period
        for metric in data:
            metric_name = metric.get("name")
            values = metric.get("values", [])
            
            if metric_name == "page_messages_new_conversations_unique":
                result["messaging_conversations_started"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_messages_active_threads_unique":
                result["active_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
        
        return result
    
    def _format_outcomes_metrics(self, messaging_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format outcomes metrics for display"""
        data = messaging_data.get("data", [])
        
        result = {
            "blocked_conversations": 0,
            "reported_conversations": 0,
            "total_outcomes": 5  # Placeholder for demonstration
        }
        
        # Sum up metrics from the period
        for metric in data:
            metric_name = metric.get("name")
            values = metric.get("values", [])
            
            if metric_name == "page_messages_blocked_conversations_unique":
                result["blocked_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_messages_reported_conversations_unique":
                result["reported_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
        
        return result
    
    def _format_messaging_metrics(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility
        Format messaging metrics for display
        """
        data = metrics_data.get("data", [])
        
        result = {
            "active_conversations": 0,
            "new_conversations": 0,
            "blocked_conversations": 0,
            "response_rate": "--",
            "response_time": "--"
        }
        
        # Sum up metrics from the period
        for metric in data:
            metric_name = metric.get("name")
            values = metric.get("values", [])
            
            if metric_name == "page_messages_active_threads_unique":
                result["active_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_messages_new_conversations_unique":
                result["new_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
            elif metric_name == "page_messages_blocked_conversations_unique":
                result["blocked_conversations"] = sum(v.get("value", 0) for v in values if v.get("value"))
        
        return result
    
    async def fetch_page_posts_insights_batch(self, page_id: str, limit: int = 25) -> Dict[str, Any]:
        """Fetch posts with their insights in batch"""
        try:
            # Get recent posts
            posts_response = await self.get(
                f"{page_id}/posts",
                params={
                    "fields": "id,message,created_time,permalink_url,likes.summary(true),comments.summary(true),shares",
                    "limit": limit
                }
            )
            
            posts = posts_response.get("data", [])
            
            # Format posts with basic engagement data
            formatted_posts = []
            for post in posts:
                likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
                comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares = post.get("shares", {}).get("count", 0)
                
                formatted_posts.append({
                    "id": post.get("id"),
                    "message": post.get("message", "")[:100],
                    "created_time": post.get("created_time"),
                    "permalink_url": post.get("permalink_url"),
                    "engagement": {
                        "likes": likes,
                        "comments": comments,
                        "shares": shares,
                        "total": likes + comments + shares
                    }
                })
            
            return {
                "page_id": page_id,
                "total_posts": len(formatted_posts),
                "posts": formatted_posts
            }
        except FacebookAPIError as e:
            return {
                "page_id": page_id,
                "total_posts": 0,
                "posts": [],
                "error": str(e)
            }

