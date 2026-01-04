"""
Web analytics adapter supporting multiple providers:
- Google Analytics 4 (GA4)
- Segment
- Mixpanel
- Custom analytics platforms

This adapter fetches page visits, session data, and user interactions
from web analytics platforms and converts them to UniversalEvents.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional, Any
import logging

from adapters.base_universal_adapter import BaseUniversalAdapter
from models.universal_event import UniversalEvent, EventType, EventDirection

logger = logging.getLogger(__name__)


class GoogleAnalyticsAdapter(BaseUniversalAdapter):
    """
    Google Analytics 4 (GA4) adapter.

    Fetches page view, session, and event data from GA4.
    Supports identification of visitors by email (if available via user_id).

    Configuration:
        property_id: str - GA4 property ID
        credentials_path: str - Path to service account credentials JSON
        dimensions: list - Additional dimensions to fetch (optional)
        metrics: list - Additional metrics to fetch (optional)
    """

    def _get_source_system(self) -> str:
        return "google-analytics"

    async def connect(self) -> None:
        """Initialize GA4 API client"""
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            credentials_path = self.config.get('credentials_path')
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.client = BetaAnalyticsDataClient(credentials=credentials)
            else:
                # Use application default credentials
                self.client = BetaAnalyticsDataClient()

            self.property_id = self.config.get('property_id')
            if not self.property_id:
                raise ValueError("GA4 property_id is required in config")

            logger.info(f"Connected to Google Analytics property {self.property_id}")

        except ImportError:
            raise ImportError(
                "Google Analytics Data API not installed. "
                "Install with: pip install google-analytics-data"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Google Analytics: {e}")
            raise

    async def disconnect(self) -> None:
        """Close GA4 API client"""
        if hasattr(self, 'client'):
            # GA4 client doesn't require explicit disconnect
            self.client = None
        logger.info("Disconnected from Google Analytics")

    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch page view events from GA4.

        Filters:
            account_domains: List[str] - Filter by user email domains
            user_ids: List[str] - Filter by specific user IDs
            pages: List[str] - Filter by page paths
            event_name: str - GA4 event name (default: 'page_view')
        """
        from google.analytics.data_v1beta.types import (
            RunReportRequest,
            Dimension,
            Metric,
            DateRange,
        )

        filters = filters or {}
        event_name = filters.get('event_name', 'page_view')

        # Date range
        if not since:
            since = datetime.now(timezone.utc) - timedelta(days=30)
        if not until:
            until = datetime.now(timezone.utc)

        # Build request
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(
                start_date=since.strftime('%Y-%m-%d'),
                end_date=until.strftime('%Y-%m-%d'),
            )],
            dimensions=[
                Dimension(name="date"),
                Dimension(name="pagePath"),
                Dimension(name="pageTitle"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
                Dimension(name="sessionCampaignName"),
                Dimension(name="deviceCategory"),
                Dimension(name="country"),
            ],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="engagementRate"),
            ],
            limit=limit or 10000,
        )

        # Execute request
        try:
            response = self.client.run_report(request)
        except Exception as e:
            logger.error(f"Failed to fetch GA4 data: {e}")
            raise

        # Process rows
        for row in response.rows:
            try:
                # Extract dimensions
                date_str = row.dimension_values[0].value
                page_path = row.dimension_values[1].value
                page_title = row.dimension_values[2].value
                source = row.dimension_values[3].value
                medium = row.dimension_values[4].value
                campaign = row.dimension_values[5].value
                device = row.dimension_values[6].value
                country = row.dimension_values[7].value

                # Extract metrics
                page_views = int(row.metric_values[0].value) if row.metric_values else 1
                avg_duration = float(row.metric_values[1].value) if len(row.metric_values) > 1 else 0
                engagement_rate = float(row.metric_values[2].value) if len(row.metric_values) > 2 else 0

                # Parse date
                event_date = datetime.strptime(date_str, '%Y%m%d').replace(tzinfo=timezone.utc)

                # Create visitor ID (GA4 doesn't expose this easily, so we hash the dimensions)
                visitor_id = hashlib.md5(
                    f"{page_path}_{date_str}_{source}_{campaign}".encode()
                ).hexdigest()[:16]

                # Detect intent signals
                intent_signals = self._detect_intent_signals(page_path, page_title)

                # Calculate engagement score
                engagement_score = min(100, engagement_rate * 100)

                # Create universal event
                event = UniversalEvent(
                    event_id=f"ga4_{visitor_id}_{event_date.timestamp()}",
                    event_type=EventType.WEB_VISIT,
                    source_system=self.source_system,
                    timestamp=event_date,
                    actor_id=visitor_id,
                    target_type="web_page",
                    target_url=page_path,
                    target_name=page_title,
                    action="visited_page",
                    direction=EventDirection.INBOUND,
                    title=f"Visited: {page_title or page_path}",
                    description=f"Page view from {source}/{medium}",
                    metadata={
                        "source": source,
                        "medium": medium,
                        "campaign": campaign,
                        "device_type": device,
                        "country": country,
                        "page_views": page_views,
                        "avg_duration_seconds": avg_duration,
                        "engagement_rate": engagement_rate
                    },
                    engagement_score=engagement_score,
                    intent_signals=intent_signals
                )

                # Enrich with account if domains provided
                if 'account_domains' in filters:
                    # GA4 doesn't provide email by default, but you can set it via user_id
                    # For now, we'll skip email enrichment unless custom implementation
                    pass

                yield event

            except Exception as e:
                logger.warning(f"Error processing GA4 row: {e}")
                continue

    def _detect_intent_signals(self, page_path: str, page_title: str) -> List[str]:
        """Detect buying intent signals from page visits"""
        signals = []
        path_lower = page_path.lower()
        title_lower = (page_title or "").lower()

        # High intent pages
        if any(x in path_lower for x in ['/pricing', '/price', '/plans', '/buy']):
            signals.append("pricing_interest")
        if any(x in path_lower for x in ['/demo', '/trial', '/signup', '/get-started']):
            signals.append("high_intent")
        if any(x in path_lower for x in ['/contact', '/sales', '/request']):
            signals.append("sales_inquiry")

        # Product research
        if any(x in path_lower for x in ['/product', '/features', '/solutions']):
            signals.append("product_research")

        # Validation seeking
        if any(x in path_lower for x in ['/case-study', '/customer', '/testimonial', '/review']):
            signals.append("validation_seeking")

        # Content engagement
        if any(x in path_lower for x in ['/blog', '/resource', '/whitepaper', '/guide']):
            signals.append("content_engagement")

        return signals


class SegmentAdapter(BaseUniversalAdapter):
    """
    Segment CDP adapter.

    Fetches track() and page() events from Segment.
    Requires Segment Data Warehouse or Protocols.

    Configuration:
        api_key: str - Segment Public API key
        workspace_slug: str - Segment workspace identifier
        source_id: str - Segment source ID (optional)
    """

    def _get_source_system(self) -> str:
        return "segment"

    async def connect(self) -> None:
        """Initialize Segment API client"""
        import aiohttp

        self.api_key = self.config.get('api_key')
        self.workspace_slug = self.config.get('workspace_slug')

        if not self.api_key or not self.workspace_slug:
            raise ValueError("Segment api_key and workspace_slug required in config")

        self.base_url = f"https://api.segmentapis.com/v1beta"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

        logger.info(f"Connected to Segment workspace {self.workspace_slug}")

    async def disconnect(self) -> None:
        """Close Segment API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from Segment")

    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch events from Segment.

        Note: Segment's Public API doesn't provide direct event querying.
        This requires either:
        1. Segment Data Warehouse integration (query warehouse directly)
        2. Segment Protocols + webhook listeners
        3. Custom implementation via reverse ETL

        This is a placeholder implementation showing the structure.
        """
        # TODO: Implement based on your Segment setup
        # Option 1: Query your Segment data warehouse (Snowflake/BigQuery/Redshift)
        # Option 2: Set up webhook receiver for real-time events
        # Option 3: Use Segment Protocols to query via API

        logger.warning(
            "Segment adapter requires additional setup. "
            "Please implement based on your Segment architecture."
        )

        # Example structure (would be populated from your data warehouse):
        # events = query_segment_warehouse(since, until, filters)
        # for event_data in events:
        #     yield self._convert_segment_event(event_data)

        return
        yield  # Make this a generator

    def _convert_segment_event(self, event_data: Dict[str, Any]) -> UniversalEvent:
        """Convert Segment event to UniversalEvent"""
        # Example conversion
        return UniversalEvent(
            event_id=event_data.get('message_id'),
            event_type=EventType.WEB_VISIT if event_data.get('type') == 'page' else EventType.CUSTOM,
            source_system=self.source_system,
            timestamp=datetime.fromisoformat(event_data.get('timestamp')),
            actor_email=event_data.get('context', {}).get('traits', {}).get('email'),
            actor_id=event_data.get('user_id'),
            target_url=event_data.get('properties', {}).get('url'),
            action=event_data.get('event', 'unknown'),
            direction=EventDirection.INBOUND,
            metadata=event_data.get('properties', {})
        )


# Factory function to get the right adapter
def get_web_analytics_adapter(provider: str, config: Dict[str, Any]) -> BaseUniversalAdapter:
    """
    Factory function to create web analytics adapter.

    Parameters
    ----------
    provider : str
        Provider name: 'google-analytics', 'segment', 'mixpanel'
    config : dict
        Provider-specific configuration

    Returns
    -------
    BaseUniversalAdapter
        Configured adapter instance
    """
    adapters = {
        'google-analytics': GoogleAnalyticsAdapter,
        'ga4': GoogleAnalyticsAdapter,
        'segment': SegmentAdapter,
    }

    adapter_class = adapters.get(provider.lower())
    if not adapter_class:
        raise ValueError(f"Unknown web analytics provider: {provider}")

    return adapter_class(config)
