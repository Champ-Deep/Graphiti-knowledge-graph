"""
Social media adapters for:
- LinkedIn
- Twitter/X
- Facebook (basic support)

Fetches engagement data, profile information, and social interactions.
"""
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional, Any
import logging

from adapters.base_universal_adapter import BaseUniversalAdapter, BaseEnrichmentAdapter
from models.universal_event import UniversalEvent, EventType, EventDirection, SocialEngagementEvent

logger = logging.getLogger(__name__)


class LinkedInAdapter(BaseUniversalAdapter):
    """
    LinkedIn adapter for fetching:
    - Company page engagement (likes, comments, shares)
    - Profile enrichment data
    - Job changes (buying triggers!)
    - Content interactions

    Configuration:
        access_token: str - LinkedIn OAuth access token
        organization_id: str - Your company's LinkedIn organization ID (for page analytics)
        api_version: str - LinkedIn API version (default: v2)
    """

    def _get_source_system(self) -> str:
        return "linkedin"

    async def connect(self) -> None:
        """Initialize LinkedIn API client"""
        import aiohttp

        self.access_token = self.config.get('access_token')
        self.organization_id = self.config.get('organization_id')

        if not self.access_token:
            raise ValueError("LinkedIn access_token required in config")

        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

        logger.info("Connected to LinkedIn API")

    async def disconnect(self) -> None:
        """Close LinkedIn API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from LinkedIn")

    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch engagement events from LinkedIn.

        Fetches likes, comments, and shares on your company's posts.
        """
        if not self.organization_id:
            logger.warning("organization_id not configured, skipping LinkedIn fetch")
            return

        # Fetch organization shares (posts)
        shares = await self._fetch_organization_shares(since, until, limit)

        # Fetch engagement for each share
        for share in shares:
            share_id = share.get('id')
            share_text = share.get('text', {}).get('text', '')
            share_timestamp = datetime.fromtimestamp(
                share.get('created', {}).get('time', 0) / 1000,
                tz=timezone.utc
            )

            # Fetch likes
            async for like_event in self._fetch_share_likes(share_id, share_text, share_timestamp):
                yield like_event

            # Fetch comments
            async for comment_event in self._fetch_share_comments(share_id, share_text, share_timestamp):
                yield comment_event

    async def _fetch_organization_shares(
        self,
        since: Optional[datetime],
        until: Optional[datetime],
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Fetch posts/shares from company page"""
        url = f"{self.base_url}/shares"
        params = {
            "q": "owners",
            "owners": f"urn:li:organization:{self.organization_id}",
            "count": limit or 50
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('elements', [])
                else:
                    logger.error(f"LinkedIn API error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching LinkedIn shares: {e}")
            return []

    async def _fetch_share_likes(
        self,
        share_id: str,
        post_text: str,
        post_timestamp: datetime
    ) -> AsyncIterator[UniversalEvent]:
        """Fetch likes on a specific post"""
        url = f"{self.base_url}/socialActions/{share_id}/likes"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for like in data.get('elements', []):
                        actor = like.get('actor', '')
                        # Extract person URN
                        # Format: urn:li:person:ABC123

                        yield UniversalEvent(
                            event_id=f"linkedin_like_{share_id}_{actor}",
                            event_type=EventType.SOCIAL_ENGAGEMENT,
                            source_system=self.source_system,
                            timestamp=post_timestamp,  # LinkedIn doesn't provide like timestamp
                            actor_id=actor,
                            target_type="social_post",
                            target_id=share_id,
                            action="like",
                            direction=EventDirection.INBOUND,
                            title="Liked LinkedIn post",
                            description=post_text[:200],
                            metadata={
                                "platform": "linkedin",
                                "post_id": share_id,
                                "engagement_type": "like"
                            },
                            engagement_score=30,
                            intent_signals=["social_engagement"]
                        )
        except Exception as e:
            logger.error(f"Error fetching LinkedIn likes: {e}")

    async def _fetch_share_comments(
        self,
        share_id: str,
        post_text: str,
        post_timestamp: datetime
    ) -> AsyncIterator[UniversalEvent]:
        """Fetch comments on a specific post"""
        url = f"{self.base_url}/socialActions/{share_id}/comments"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for comment in data.get('elements', []):
                        actor = comment.get('actor', '')
                        comment_text = comment.get('message', {}).get('text', '')
                        comment_time = datetime.fromtimestamp(
                            comment.get('created', {}).get('time', 0) / 1000,
                            tz=timezone.utc
                        )

                        yield UniversalEvent(
                            event_id=f"linkedin_comment_{share_id}_{actor}_{comment_time.timestamp()}",
                            event_type=EventType.SOCIAL_ENGAGEMENT,
                            source_system=self.source_system,
                            timestamp=comment_time,
                            actor_id=actor,
                            target_type="social_post",
                            target_id=share_id,
                            action="comment",
                            direction=EventDirection.INBOUND,
                            title="Commented on LinkedIn post",
                            description=post_text[:200],
                            content_text=comment_text,
                            metadata={
                                "platform": "linkedin",
                                "post_id": share_id,
                                "engagement_type": "comment"
                            },
                            engagement_score=60,
                            intent_signals=["social_engagement", "active_discussion"]
                        )
        except Exception as e:
            logger.error(f"Error fetching LinkedIn comments: {e}")

    async def enrich_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Enrich a LinkedIn profile.

        Note: This requires LinkedIn Profile API access which is restricted.
        Most companies use third-party enrichment APIs (Clearbit, etc.) instead.
        """
        # This would require LinkedIn Profile API access
        # Most use cases should use Clearbit or similar enrichment services
        logger.warning("LinkedIn profile enrichment requires special API access")
        return {}


class TwitterAdapter(BaseUniversalAdapter):
    """
    Twitter/X adapter for fetching:
    - Mentions of your company
    - Engagement with your tweets
    - Profile information

    Configuration:
        bearer_token: str - Twitter API v2 bearer token
        account_id: str - Your company's Twitter account ID
    """

    def _get_source_system(self) -> str:
        return "twitter"

    async def connect(self) -> None:
        """Initialize Twitter API client"""
        import aiohttp

        self.bearer_token = self.config.get('bearer_token')
        self.account_id = self.config.get('account_id')

        if not self.bearer_token:
            raise ValueError("Twitter bearer_token required in config")

        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

        logger.info("Connected to Twitter API")

    async def disconnect(self) -> None:
        """Close Twitter API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from Twitter")

    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch engagement events from Twitter.

        Fetches mentions, replies, retweets, and likes.
        """
        if not self.account_id:
            logger.warning("account_id not configured, skipping Twitter fetch")
            return

        # Fetch mentions of your account
        async for event in self._fetch_mentions(since, until, limit):
            yield event

    async def _fetch_mentions(
        self,
        since: Optional[datetime],
        until: Optional[datetime],
        limit: Optional[int]
    ) -> AsyncIterator[UniversalEvent]:
        """Fetch mentions of your Twitter account"""
        url = f"{self.base_url}/users/{self.account_id}/mentions"
        params = {
            "max_results": min(limit or 100, 100),
            "tweet.fields": "created_at,author_id,text,public_metrics",
            "expansions": "author_id",
            "user.fields": "name,username"
        }

        if since:
            params["start_time"] = since.isoformat()
        if until:
            params["end_time"] = until.isoformat()

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Build user lookup
                    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}

                    for tweet in data.get('data', []):
                        author_id = tweet.get('author_id')
                        author = users.get(author_id, {})

                        yield UniversalEvent(
                            event_id=f"twitter_mention_{tweet.get('id')}",
                            event_type=EventType.SOCIAL_ENGAGEMENT,
                            source_system=self.source_system,
                            timestamp=datetime.fromisoformat(
                                tweet.get('created_at').replace('Z', '+00:00')
                            ),
                            actor_id=author_id,
                            actor_name=author.get('name'),
                            target_type="social_post",
                            target_id=tweet.get('id'),
                            action="mention",
                            direction=EventDirection.INBOUND,
                            title=f"@{author.get('username')} mentioned you",
                            content_text=tweet.get('text'),
                            metadata={
                                "platform": "twitter",
                                "tweet_id": tweet.get('id'),
                                "author_username": author.get('username'),
                                "likes": tweet.get('public_metrics', {}).get('like_count', 0),
                                "retweets": tweet.get('public_metrics', {}).get('retweet_count', 0)
                            },
                            engagement_score=50,
                            intent_signals=["social_engagement"]
                        )
                else:
                    logger.error(f"Twitter API error: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching Twitter mentions: {e}")


class LinkedInEnrichmentAdapter(BaseEnrichmentAdapter):
    """
    LinkedIn profile enrichment adapter.

    Uses LinkedIn API or third-party services to enrich contact profiles.

    Note: Direct LinkedIn enrichment requires special API access.
    Consider using Clearbit, PDL, or similar services instead.
    """

    def _get_source_system(self) -> str:
        return "linkedin-enrichment"

    async def connect(self) -> None:
        """Initialize enrichment service"""
        # Use third-party enrichment service or LinkedIn API
        self.api_key = self.config.get('api_key')
        logger.info("LinkedIn enrichment adapter ready")

    async def disconnect(self) -> None:
        """Cleanup"""
        pass

    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich contact with LinkedIn data.

        Returns profile data, job history, skills, etc.
        """
        # TODO: Implement using your enrichment service
        # Example services: Clearbit, PDL, Apollo, etc.
        logger.warning("LinkedIn enrichment requires third-party service integration")
        return {}

    async def enrich_account(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enrich account with LinkedIn company data"""
        logger.warning("LinkedIn company enrichment requires third-party service integration")
        return {}


# Factory function
def get_social_media_adapter(provider: str, config: Dict[str, Any]) -> BaseUniversalAdapter:
    """
    Factory function to create social media adapter.

    Parameters
    ----------
    provider : str
        Provider name: 'linkedin', 'twitter', 'facebook'
    config : dict
        Provider-specific configuration

    Returns
    -------
    BaseUniversalAdapter
        Configured adapter instance
    """
    adapters = {
        'linkedin': LinkedInAdapter,
        'twitter': TwitterAdapter,
        'linkedin-enrichment': LinkedInEnrichmentAdapter,
    }

    adapter_class = adapters.get(provider.lower())
    if not adapter_class:
        raise ValueError(f"Unknown social media provider: {provider}")

    return adapter_class(config)
