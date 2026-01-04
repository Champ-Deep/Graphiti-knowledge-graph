"""
Enrichment adapters for firmographic and technographic data:
- Clearbit (firmographics + technographics)
- BuiltWith (technographics)
- ZoomInfo (firmographics)
- People Data Labs (contact enrichment)

These adapters provide on-demand enrichment rather than event streams.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

from adapters.base_universal_adapter import BaseEnrichmentAdapter
from models.universal_event import UniversalEvent, EventType, EventDirection

logger = logging.getLogger(__name__)


class ClearbitAdapter(BaseEnrichmentAdapter):
    """
    Clearbit enrichment adapter.

    Provides comprehensive firmographic and technographic data:
    - Company: Industry, size, revenue, funding, technologies
    - Person: Title, role, seniority, social profiles

    Configuration:
        api_key: str - Clearbit API key
    """

    def _get_source_system(self) -> str:
        return "clearbit"

    async def connect(self) -> None:
        """Initialize Clearbit API client"""
        import aiohttp

        self.api_key = self.config.get('api_key')
        if not self.api_key:
            raise ValueError("Clearbit api_key required in config")

        self.base_url = "https://company.clearbit.com/v2"
        self.person_url = "https://person.clearbit.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

        logger.info("Connected to Clearbit API")

    async def disconnect(self) -> None:
        """Close Clearbit API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from Clearbit")

    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich contact using Clearbit Person API.

        Returns:
            {
                'name': str,
                'title': str,
                'role': str,
                'seniority': str,
                'company': dict,
                'social_profiles': dict,
                'location': str,
                etc.
            }
        """
        if not email:
            logger.warning("Email required for Clearbit person enrichment")
            return {}

        url = f"{self.person_url}/people/find"
        params = {"email": email}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_person_data(data)
                elif response.status == 404:
                    logger.info(f"No Clearbit data found for {email}")
                    return {}
                else:
                    logger.error(f"Clearbit API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error enriching contact with Clearbit: {e}")
            return {}

    async def enrich_account(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich account using Clearbit Company API.

        Returns:
            {
                'name': str,
                'domain': str,
                'industry': str,
                'employee_count': int,
                'estimated_revenue': str,
                'funding_raised': int,
                'technologies': list,
                'category': dict,
                etc.
            }
        """
        if not domain:
            logger.warning("Domain required for Clearbit company enrichment")
            return {}

        url = f"{self.base_url}/companies/find"
        params = {"domain": domain}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_company_data(data)
                elif response.status == 404:
                    logger.info(f"No Clearbit data found for {domain}")
                    return {}
                else:
                    logger.error(f"Clearbit API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error enriching account with Clearbit: {e}")
            return {}

    def _normalize_person_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Clearbit person data"""
        return {
            'name': data.get('name', {}).get('fullName'),
            'first_name': data.get('name', {}).get('givenName'),
            'last_name': data.get('name', {}).get('familyName'),
            'email': data.get('email'),
            'title': data.get('employment', {}).get('title'),
            'role': data.get('employment', {}).get('role'),
            'seniority': data.get('employment', {}).get('seniority'),
            'company_name': data.get('employment', {}).get('name'),
            'company_domain': data.get('employment', {}).get('domain'),
            'location': data.get('location'),
            'bio': data.get('bio'),
            'social_profiles': {
                'linkedin': data.get('linkedin', {}).get('handle'),
                'twitter': data.get('twitter', {}).get('handle'),
                'github': data.get('github', {}).get('handle'),
            },
            'raw_data': data
        }

    def _normalize_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Clearbit company data"""
        return {
            'name': data.get('name'),
            'domain': data.get('domain'),
            'description': data.get('description'),
            'industry': data.get('category', {}).get('industry'),
            'sector': data.get('category', {}).get('sector'),
            'employee_count': data.get('metrics', {}).get('employees'),
            'employee_range': data.get('metrics', {}).get('employeesRange'),
            'estimated_revenue': data.get('metrics', {}).get('estimatedAnnualRevenue'),
            'funding_raised': data.get('metrics', {}).get('raised'),
            'founded_year': data.get('foundedYear'),
            'location': data.get('location'),
            'technologies': data.get('tech', []),
            'tags': data.get('tags', []),
            'social_profiles': {
                'linkedin': data.get('linkedin', {}).get('handle'),
                'twitter': data.get('twitter', {}).get('handle'),
                'facebook': data.get('facebook', {}).get('handle'),
            },
            'raw_data': data
        }


class BuiltWithAdapter(BaseEnrichmentAdapter):
    """
    BuiltWith technographic enrichment adapter.

    Detects technologies used by a website:
    - CRM systems
    - Marketing automation
    - Analytics platforms
    - Infrastructure (CDN, hosting, etc.)
    - Payment processors
    - And 100+ other categories

    Configuration:
        api_key: str - BuiltWith API key
    """

    def _get_source_system(self) -> str:
        return "builtwith"

    async def connect(self) -> None:
        """Initialize BuiltWith API client"""
        import aiohttp

        self.api_key = self.config.get('api_key')
        if not self.api_key:
            raise ValueError("BuiltWith api_key required in config")

        self.base_url = "https://api.builtwith.com"
        self.session = aiohttp.ClientSession()

        logger.info("Connected to BuiltWith API")

    async def disconnect(self) -> None:
        """Close BuiltWith API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from BuiltWith")

    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """BuiltWith doesn't provide contact enrichment"""
        return {}

    async def enrich_account(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect technologies used by account's website.

        Returns:
            {
                'domain': str,
                'technologies': [
                    {
                        'name': str,
                        'category': str,
                        'first_detected': str,
                        'last_detected': str
                    }
                ],
                'categories': dict (technologies grouped by category)
            }
        """
        if not domain:
            logger.warning("Domain required for BuiltWith enrichment")
            return {}

        url = f"{self.base_url}/v20/api.json"
        params = {
            "KEY": self.api_key,
            "LOOKUP": domain
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_tech_data(domain, data)
                else:
                    logger.error(f"BuiltWith API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error enriching account with BuiltWith: {e}")
            return {}

    def _normalize_tech_data(self, domain: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize BuiltWith technology data"""
        technologies = []
        categories = {}

        for result in data.get('Results', []):
            for path in result.get('Result', {}).get('Paths', []):
                for tech in path.get('Technologies', []):
                    category = tech.get('Tag', 'Other')
                    tech_info = {
                        'name': tech.get('Name'),
                        'category': category,
                        'first_detected': tech.get('FirstDetected'),
                        'last_detected': tech.get('LastDetected'),
                        'description': tech.get('Description'),
                    }
                    technologies.append(tech_info)

                    # Group by category
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(tech_info['name'])

        return {
            'domain': domain,
            'technologies': technologies,
            'categories': categories,
            'tech_count': len(technologies),
            'raw_data': data
        }


class PeopleDataLabsAdapter(BaseEnrichmentAdapter):
    """
    People Data Labs (PDL) enrichment adapter.

    Comprehensive contact enrichment:
    - Contact details and social profiles
    - Job history and skills
    - Education background
    - Interests and topics

    Configuration:
        api_key: str - PDL API key
    """

    def _get_source_system(self) -> str:
        return "people-data-labs"

    async def connect(self) -> None:
        """Initialize PDL API client"""
        import aiohttp

        self.api_key = self.config.get('api_key')
        if not self.api_key:
            raise ValueError("PDL api_key required in config")

        self.base_url = "https://api.peopledatalabs.com/v5"
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

        logger.info("Connected to People Data Labs API")

    async def disconnect(self) -> None:
        """Close PDL API session"""
        if hasattr(self, 'session'):
            await self.session.close()
        logger.info("Disconnected from People Data Labs")

    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich contact using PDL Person Enrichment API.

        Returns comprehensive profile data.
        """
        url = f"{self.base_url}/person/enrich"

        # Build query params
        params = {}
        if email:
            params['email'] = email
        elif name and company:
            params['name'] = name
            params['company'] = company
        else:
            logger.warning("Email or (name + company) required for PDL enrichment")
            return {}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_person_data(data)
                elif response.status == 404:
                    logger.info(f"No PDL data found")
                    return {}
                else:
                    logger.error(f"PDL API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error enriching contact with PDL: {e}")
            return {}

    async def enrich_account(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich account using PDL Company Enrichment API.
        """
        url = f"{self.base_url}/company/enrich"

        params = {}
        if domain:
            params['website'] = domain
        elif company_name:
            params['name'] = company_name
        else:
            logger.warning("Domain or company name required for PDL company enrichment")
            return {}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_company_data(data)
                elif response.status == 404:
                    logger.info(f"No PDL company data found")
                    return {}
                else:
                    logger.error(f"PDL API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error enriching account with PDL: {e}")
            return {}

    def _normalize_person_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize PDL person data"""
        return {
            'name': data.get('full_name'),
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'email': data.get('emails', [{}])[0].get('address') if data.get('emails') else None,
            'phone': data.get('phone_numbers', [{}])[0] if data.get('phone_numbers') else None,
            'title': data.get('job_title'),
            'company_name': data.get('job_company_name'),
            'seniority': data.get('job_title_levels', [None])[0],
            'industry': data.get('industry'),
            'location': data.get('location_name'),
            'skills': data.get('skills', []),
            'interests': data.get('interests', []),
            'social_profiles': {
                'linkedin': data.get('linkedin_url'),
                'twitter': data.get('twitter_url'),
                'facebook': data.get('facebook_url'),
                'github': data.get('github_url'),
            },
            'education': data.get('education', []),
            'job_history': data.get('experience', []),
            'raw_data': data
        }

    def _normalize_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize PDL company data"""
        return {
            'name': data.get('name'),
            'domain': data.get('website'),
            'description': data.get('summary'),
            'industry': data.get('industry'),
            'employee_count': data.get('employee_count'),
            'founded_year': data.get('founded'),
            'location': data.get('location', {}).get('name'),
            'social_profiles': {
                'linkedin': data.get('linkedin_url'),
                'twitter': data.get('twitter_url'),
                'facebook': data.get('facebook_url'),
            },
            'tags': data.get('tags', []),
            'raw_data': data
        }


# Factory function
def get_enrichment_adapter(provider: str, config: Dict[str, Any]) -> BaseEnrichmentAdapter:
    """
    Factory function to create enrichment adapter.

    Parameters
    ----------
    provider : str
        Provider name: 'clearbit', 'builtwith', 'people-data-labs', 'zoominfo'
    config : dict
        Provider-specific configuration

    Returns
    -------
    BaseEnrichmentAdapter
        Configured adapter instance
    """
    adapters = {
        'clearbit': ClearbitAdapter,
        'builtwith': BuiltWithAdapter,
        'people-data-labs': PeopleDataLabsAdapter,
        'pdl': PeopleDataLabsAdapter,
    }

    adapter_class = adapters.get(provider.lower())
    if not adapter_class:
        raise ValueError(f"Unknown enrichment provider: {provider}")

    return adapter_class(config)
