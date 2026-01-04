"""
Universal adapter interface for ANY data source.

This provides a consistent interface for ingesting data from:
- Email providers (Gmail, Outlook)
- Web analytics (Google Analytics, Segment, Mixpanel)
- Social media (LinkedIn, Twitter, Facebook)
- Enrichment APIs (Clearbit, ZoomInfo, BuiltWith)
- CRM systems (Salesforce, HubSpot)
- Custom data sources

All adapters normalize their data into UniversalEvent objects.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Any

from models.universal_event import UniversalEvent


class BaseUniversalAdapter(ABC):
    """
    Abstract base class for universal data source adapters.

    All data source adapters should inherit from this class and implement
    the required methods. This ensures consistent behavior across all
    integrations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with configuration.

        Parameters
        ----------
        config : dict, optional
            Adapter-specific configuration (API keys, credentials, etc.)
        """
        self.config = config or {}
        self.source_system = self._get_source_system()

    @abstractmethod
    def _get_source_system(self) -> str:
        """
        Return the name of the source system.

        Returns
        -------
        str
            Source system identifier (e.g., 'google-analytics', 'linkedin', 'clearbit')
        """
        pass

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the data source.

        This should handle authentication, initialization, and any
        necessary setup.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the data source.

        Clean up resources, close sessions, etc.
        """
        pass

    @abstractmethod
    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch events from the data source.

        Parameters
        ----------
        since : datetime, optional
            Only fetch events after this date
        until : datetime, optional
            Only fetch events before this date
        filters : dict, optional
            Adapter-specific filters (e.g., account_id, user_id, event_types)
        limit : int, optional
            Maximum number of events to fetch

        Yields
        ------
        UniversalEvent
            Normalized event objects
        """
        pass

    async def fetch_events_for_account(
        self,
        account_name: str,
        account_domains: List[str],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Fetch events for a specific account.

        This is a convenience method that uses account domains/identifiers
        to filter events. Adapters can override this for more efficient
        account-based querying.

        Parameters
        ----------
        account_name : str
            Account name for labeling
        account_domains : list of str
            Email domains associated with the account
        since : datetime, optional
            Only fetch events after this date
        until : datetime, optional
            Only fetch events before this date
        limit : int, optional
            Maximum number of events to fetch

        Yields
        ------
        UniversalEvent
            Events associated with the account
        """
        filters = {
            'account_name': account_name,
            'account_domains': account_domains
        }

        async for event in self.fetch_events(
            since=since,
            until=until,
            filters=filters,
            limit=limit
        ):
            # Ensure account is set
            if not event.account_name:
                event.account_name = account_name
            if not event.account_domain and account_domains:
                event.account_domain = account_domains[0]

            yield event

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the data source.

        Returns
        -------
        dict
            Connection status information
            {
                'connected': bool,
                'message': str,
                'details': dict (optional)
            }
        """
        try:
            await self.connect()
            await self.disconnect()
            return {
                'connected': True,
                'message': f'Successfully connected to {self.source_system}',
                'source_system': self.source_system
            }
        except Exception as e:
            return {
                'connected': False,
                'message': f'Failed to connect to {self.source_system}: {str(e)}',
                'source_system': self.source_system,
                'error': str(e)
            }

    def enrich_event_with_account(
        self,
        event: UniversalEvent,
        account_configs: List[Dict[str, Any]]
    ) -> UniversalEvent:
        """
        Enrich an event with account information based on email domain.

        This is a universal helper that all adapters can use to map
        events to accounts.

        Parameters
        ----------
        event : UniversalEvent
            Event to enrich
        account_configs : list of dict
            Account configurations with 'name' and 'domains' keys

        Returns
        -------
        UniversalEvent
            Enriched event with account_name and account_domain set
        """
        if event.actor_domain:
            for account_config in account_configs:
                if event.actor_domain in account_config.get('domains', []):
                    event.account_name = account_config['name']
                    event.account_domain = account_config['domains'][0]
                    break

        return event


class BaseEnrichmentAdapter(BaseUniversalAdapter):
    """
    Base class for enrichment adapters (Clearbit, ZoomInfo, etc.).

    Enrichment adapters don't stream events - they provide
    on-demand enrichment data for contacts and accounts.
    """

    @abstractmethod
    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich a contact with additional data.

        Parameters
        ----------
        email : str, optional
            Contact email address
        name : str, optional
            Contact name
        company : str, optional
            Company name

        Returns
        -------
        dict
            Enrichment data (title, location, social profiles, etc.)
        """
        pass

    @abstractmethod
    async def enrich_account(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich an account with additional data.

        Parameters
        ----------
        domain : str, optional
            Company domain
        company_name : str, optional
            Company name

        Returns
        -------
        dict
            Enrichment data (industry, size, revenue, technologies, etc.)
        """
        pass

    async def fetch_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[UniversalEvent]:
        """
        Enrichment adapters don't stream events.

        This method is not applicable for enrichment adapters.
        Use enrich_contact() or enrich_account() instead.
        """
        # Enrichment adapters don't produce event streams
        # They provide on-demand enrichment data
        raise NotImplementedError(
            f"{self.source_system} is an enrichment adapter. "
            "Use enrich_contact() or enrich_account() instead of fetch_events()."
        )
