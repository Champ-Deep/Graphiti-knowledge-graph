"""
Unified Profile Builder Service

Aggregates data from ALL sources to build comprehensive prospect profiles:
- Firmographics (from enrichment APIs + email)
- Technographics (from BuiltWith + Clearbit)
- Psychographics (from email content + social media)
- Engagement signals (from email + web + social)
- Intent scoring (from all sources)
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import logging

from services.graphiti_service import GraphitiService
from adapters.enrichment_adapters import get_enrichment_adapter

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """
    Builds comprehensive profiles by aggregating data from:
    - Knowledge graph (email, web, social events)
    - Enrichment APIs (firmographics, technographics)
    - Intent scoring engine
    """

    def __init__(
        self,
        graphiti_service: GraphitiService,
        enrichment_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialize profile builder.

        Parameters
        ----------
        graphiti_service : GraphitiService
            Graphiti service instance for querying knowledge graph
        enrichment_configs : dict, optional
            Enrichment provider configs:
            {
                'clearbit': {'api_key': '...'},
                'builtwith': {'api_key': '...'},
                'people-data-labs': {'api_key': '...'}
            }
        """
        self.graphiti = graphiti_service
        self.enrichment_configs = enrichment_configs or {}
        self.enrichment_adapters = {}

        # Initialize enrichment adapters
        for provider, config in self.enrichment_configs.items():
            try:
                self.enrichment_adapters[provider] = get_enrichment_adapter(provider, config)
            except Exception as e:
                logger.warning(f"Failed to initialize {provider} adapter: {e}")

    async def build_contact_profile(
        self,
        account_name: str,
        contact_email: Optional[str] = None,
        contact_name: Optional[str] = None,
        enrich: bool = True
    ) -> Dict[str, Any]:
        """
        Build comprehensive contact profile.

        Parameters
        ----------
        account_name : str
            Account name
        contact_email : str, optional
            Contact email address
        contact_name : str, optional
            Contact name
        enrich : bool
            Whether to enrich with external APIs (default: True)

        Returns
        -------
        dict
            Comprehensive contact profile with all available data
        """
        profile = {
            'contact': {},
            'account': {},
            'firmographics': {},
            'technographics': {},
            'psychographics': {},
            'engagement': {},
            'intent': {},
            'recommended_approach': None
        }

        # 1. Query knowledge graph for contact data
        if contact_email:
            kg_query = f"Tell me everything about {contact_email} including their interests, communication patterns, and recent interactions"
        elif contact_name:
            kg_query = f"Tell me everything about {contact_name} at {account_name}"
        else:
            kg_query = f"Tell me about contacts at {account_name}"

        try:
            kg_data = await self.graphiti.search_account(
                account_name=account_name,
                query=kg_query,
                num_results=50
            )

            # Extract contact info from knowledge graph
            profile['contact'] = self._extract_contact_from_kg(
                kg_data,
                contact_email,
                contact_name
            )

            # Extract psychographics (interests, personal details)
            profile['psychographics'] = self._extract_psychographics_from_kg(kg_data)

            # Extract engagement data
            profile['engagement'] = await self._build_engagement_profile(
                account_name,
                contact_email or contact_name
            )

        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")

        # 2. Enrich with external APIs if requested
        if enrich and contact_email:
            enrichment_data = await self._enrich_contact(contact_email)
            profile['contact'].update(enrichment_data.get('contact', {}))
            profile['firmographics'].update(enrichment_data.get('firmographics', {}))
            profile['technographics'].update(enrichment_data.get('technographics', {}))

        # 3. Build account profile
        profile['account'] = await self.build_account_profile(account_name, enrich=enrich)

        # 4. Calculate intent score
        profile['intent'] = self._calculate_intent_score(profile)

        # 5. Generate outreach recommendations
        profile['recommended_approach'] = await self._generate_outreach_strategy(profile)

        return profile

    async def build_account_profile(
        self,
        account_name: str,
        enrich: bool = True
    ) -> Dict[str, Any]:
        """
        Build comprehensive account profile.

        Parameters
        ----------
        account_name : str
            Account name
        enrich : bool
            Whether to enrich with external APIs

        Returns
        -------
        dict
            Account profile data
        """
        account_profile = {
            'name': account_name,
            'contacts': [],
            'firmographics': {},
            'technographics': {},
            'engagement_summary': {},
            'intent_signals': []
        }

        # Query knowledge graph
        try:
            # Get all contacts
            contacts_query = f"Who are the contacts at {account_name}?"
            contacts_data = await self.graphiti.search_account(
                account_name=account_name,
                query=contacts_query,
                num_results=30
            )

            account_profile['contacts'] = self._extract_contacts_list(contacts_data)

            # Get firmographics from knowledge graph
            firmographics_query = f"What firmographic data do we know about {account_name}?"
            firmographics_data = await self.graphiti.search_account(
                account_name=account_name,
                query=firmographics_query,
                num_results=20
            )

            # Get technographics
            tech_query = f"What technologies does {account_name} use?"
            tech_data = await self.graphiti.search_account(
                account_name=account_name,
                query=tech_query,
                num_results=20
            )

            account_profile['firmographics'] = self._extract_firmographics_from_kg(
                firmographics_data
            )
            account_profile['technographics'] = self._extract_technographics_from_kg(
                tech_data
            )

        except Exception as e:
            logger.error(f"Error building account profile from KG: {e}")

        # Enrich with external APIs
        if enrich:
            # Assume account has primary domain
            domain = account_profile.get('firmographics', {}).get('domain')

            if domain:
                enrichment_data = await self._enrich_account(domain)
                account_profile['firmographics'].update(
                    enrichment_data.get('firmographics', {})
                )
                account_profile['technographics'].update(
                    enrichment_data.get('technographics', {})
                )

        return account_profile

    async def _build_engagement_profile(
        self,
        account_name: str,
        contact_identifier: str
    ) -> Dict[str, Any]:
        """Build engagement profile from all channels"""
        engagement = {
            'email': {},
            'web': {},
            'social': {},
            'overall_score': 0,
            'last_engagement': None,
            'engagement_trend': 'unknown'
        }

        try:
            # Email engagement
            email_query = f"What email interactions have we had with {contact_identifier}?"
            email_data = await self.graphiti.search_account(
                account_name=account_name,
                query=email_query,
                num_results=20
            )

            engagement['email'] = self._analyze_email_engagement(email_data)

            # Web engagement
            web_query = f"What web pages has {contact_identifier} visited?"
            web_data = await self.graphiti.search_account(
                account_name=account_name,
                query=web_query,
                num_results=20
            )

            engagement['web'] = self._analyze_web_engagement(web_data)

            # Social engagement
            social_query = f"What social media interactions has {contact_identifier} had?"
            social_data = await self.graphiti.search_account(
                account_name=account_name,
                query=social_query,
                num_results=20
            )

            engagement['social'] = self._analyze_social_engagement(social_data)

            # Calculate overall engagement score
            engagement['overall_score'] = self._calculate_engagement_score(engagement)

        except Exception as e:
            logger.error(f"Error building engagement profile: {e}")

        return engagement

    async def _enrich_contact(self, email: str) -> Dict[str, Any]:
        """Enrich contact using all available enrichment APIs"""
        enrichment_data = {
            'contact': {},
            'firmographics': {},
            'technographics': {}
        }

        # Try Clearbit first
        if 'clearbit' in self.enrichment_adapters:
            try:
                adapter = self.enrichment_adapters['clearbit']
                await adapter.connect()
                data = await adapter.enrich_contact(email=email)
                await adapter.disconnect()

                if data:
                    enrichment_data['contact'].update({
                        'title': data.get('title'),
                        'role': data.get('role'),
                        'seniority': data.get('seniority'),
                        'location': data.get('location'),
                        'social_profiles': data.get('social_profiles', {})
                    })

                    if data.get('company_name'):
                        enrichment_data['firmographics'].update({
                            'company': data.get('company_name'),
                            'domain': data.get('company_domain')
                        })
            except Exception as e:
                logger.error(f"Clearbit enrichment failed: {e}")

        # Try People Data Labs
        if 'people-data-labs' in self.enrichment_adapters:
            try:
                adapter = self.enrichment_adapters['people-data-labs']
                await adapter.connect()
                data = await adapter.enrich_contact(email=email)
                await adapter.disconnect()

                if data:
                    enrichment_data['contact'].update({
                        'phone': data.get('phone'),
                        'skills': data.get('skills', []),
                        'interests': data.get('interests', []),
                        'education': data.get('education', []),
                        'job_history': data.get('job_history', [])
                    })
            except Exception as e:
                logger.error(f"PDL enrichment failed: {e}")

        return enrichment_data

    async def _enrich_account(self, domain: str) -> Dict[str, Any]:
        """Enrich account using all available enrichment APIs"""
        enrichment_data = {
            'firmographics': {},
            'technographics': {}
        }

        # Clearbit for firmographics
        if 'clearbit' in self.enrichment_adapters:
            try:
                adapter = self.enrichment_adapters['clearbit']
                await adapter.connect()
                data = await adapter.enrich_account(domain=domain)
                await adapter.disconnect()

                if data:
                    enrichment_data['firmographics'].update({
                        'domain': data.get('domain'),
                        'industry': data.get('industry'),
                        'sector': data.get('sector'),
                        'employee_count': data.get('employee_count'),
                        'revenue': data.get('estimated_revenue'),
                        'funding': data.get('funding_raised'),
                        'founded': data.get('founded_year'),
                        'location': data.get('location'),
                        'description': data.get('description')
                    })

                    # Clearbit also provides basic tech data
                    if data.get('technologies'):
                        enrichment_data['technographics']['technologies'] = data['technologies']
            except Exception as e:
                logger.error(f"Clearbit account enrichment failed: {e}")

        # BuiltWith for detailed technographics
        if 'builtwith' in self.enrichment_adapters:
            try:
                adapter = self.enrichment_adapters['builtwith']
                await adapter.connect()
                data = await adapter.enrich_account(domain=domain)
                await adapter.disconnect()

                if data:
                    enrichment_data['technographics'].update({
                        'technologies': data.get('technologies', []),
                        'tech_categories': data.get('categories', {}),
                        'tech_count': data.get('tech_count', 0)
                    })
            except Exception as e:
                logger.error(f"BuiltWith enrichment failed: {e}")

        return enrichment_data

    def _extract_contact_from_kg(
        self,
        kg_data: Dict[str, Any],
        email: Optional[str],
        name: Optional[str]
    ) -> Dict[str, Any]:
        """Extract contact info from knowledge graph results"""
        contact_info = {}

        # Extract from nodes
        for node in kg_data.get('nodes', []):
            if node.get('entity_type') == 'Contact':
                # Match by email or name
                node_name = node.get('name', '')
                if email and email.lower() in str(node).lower():
                    contact_info['name'] = node_name
                    contact_info['email'] = email
                elif name and name.lower() in node_name.lower():
                    contact_info['name'] = node_name

        return contact_info

    def _extract_psychographics_from_kg(self, kg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract psychographic data from knowledge graph"""
        psychographics = {
            'interests': [],
            'personal_details': [],
            'communication_style': {},
            'topics_discussed': []
        }

        for node in kg_data.get('nodes', []):
            entity_type = node.get('entity_type')

            if entity_type == 'PersonalDetail':
                psychographics['personal_details'].append({
                    'category': node.get('category'),
                    'detail': node.get('detail')
                })
            elif entity_type == 'Topic':
                psychographics['topics_discussed'].append(node.get('name'))

        # Extract interests from edges
        for edge in kg_data.get('edges', []):
            if edge.get('relationship_type') == 'INTERESTED_IN':
                psychographics['interests'].append({
                    'topic': edge.get('target_node_name'),
                    'level': edge.get('level', 'medium')
                })

        return psychographics

    def _extract_contacts_list(self, kg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract list of contacts from knowledge graph"""
        contacts = []

        for node in kg_data.get('nodes', []):
            if node.get('entity_type') == 'Contact':
                contacts.append({
                    'name': node.get('name'),
                    'title': node.get('title'),
                    'email': node.get('email')
                })

        return contacts

    def _extract_firmographics_from_kg(self, kg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract firmographic data from knowledge graph"""
        firmographics = {}

        for node in kg_data.get('nodes', []):
            if node.get('entity_type') == 'Firmographic':
                attr = node.get('attribute')
                value = node.get('value')
                if attr and value:
                    firmographics[attr] = value

        return firmographics

    def _extract_technographics_from_kg(self, kg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technographic data from knowledge graph"""
        technologies = []

        for node in kg_data.get('nodes', []):
            if node.get('entity_type') == 'Technology':
                technologies.append({
                    'name': node.get('name'),
                    'category': node.get('category'),
                    'vendor': node.get('vendor')
                })

        return {'technologies': technologies}

    def _analyze_email_engagement(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze email engagement patterns"""
        return {
            'total_emails': len(email_data.get('nodes', [])),
            'response_rate': 0.0,  # TODO: Calculate from data
            'avg_response_time_hours': 0.0,  # TODO: Calculate from data
            'last_email_date': None
        }

    def _analyze_web_engagement(self, web_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze web engagement patterns"""
        page_visits = []

        for node in web_data.get('nodes', []):
            if node.get('entity_type') == 'WebPage':
                page_visits.append(node)

        return {
            'total_page_views': len(page_visits),
            'unique_pages': len(set(p.get('url') for p in page_visits)),
            'high_intent_pages': [p for p in page_visits if 'pricing' in p.get('url', '').lower()],
            'last_visit_date': None
        }

    def _analyze_social_engagement(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze social media engagement"""
        engagements = []

        for node in social_data.get('nodes', []):
            if node.get('entity_type') == 'Communication':
                if node.get('channel') in ['linkedin', 'twitter']:
                    engagements.append(node)

        return {
            'total_engagements': len(engagements),
            'platforms': list(set(e.get('channel') for e in engagements)),
            'last_engagement_date': None
        }

    def _calculate_engagement_score(self, engagement: Dict[str, Any]) -> float:
        """Calculate overall engagement score (0-100)"""
        score = 0.0

        # Email engagement (40 points)
        email = engagement.get('email', {})
        score += min(40, email.get('total_emails', 0) * 5)

        # Web engagement (40 points)
        web = engagement.get('web', {})
        score += min(40, web.get('total_page_views', 0) * 4)

        # High-intent pages (bonus 20 points)
        high_intent_pages = len(web.get('high_intent_pages', []))
        score += min(20, high_intent_pages * 10)

        # Social engagement (20 points)
        social = engagement.get('social', {})
        score += min(20, social.get('total_engagements', 0) * 5)

        return min(100, score)

    def _calculate_intent_score(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate buying intent score"""
        intent_score = 0.0
        signals = []

        # Email engagement signals
        email_count = profile['engagement'].get('email', {}).get('total_emails', 0)
        if email_count > 5:
            signals.append('active_communication')
            intent_score += 20

        # Web engagement signals
        web = profile['engagement'].get('web', {})
        high_intent_pages = len(web.get('high_intent_pages', []))
        if high_intent_pages > 0:
            signals.append('pricing_interest')
            intent_score += 30

        # Social engagement signals
        social_count = profile['engagement'].get('social', {}).get('total_engagements', 0)
        if social_count > 0:
            signals.append('social_awareness')
            intent_score += 15

        # Overall engagement score contributes
        overall_engagement = profile['engagement'].get('overall_score', 0)
        intent_score += (overall_engagement / 100) * 35

        return {
            'score': min(100, intent_score),
            'level': 'high' if intent_score > 70 else 'medium' if intent_score > 40 else 'low',
            'signals': signals
        }

    async def _generate_outreach_strategy(self, profile: Dict[str, Any]) -> str:
        """Generate personalized outreach recommendations"""
        # This would ideally use an LLM to generate personalized recommendations
        # For now, return a template-based approach

        contact = profile.get('contact', {})
        psycho = profile.get('psychographics', {})
        intent = profile.get('intent', {})

        strategy = []

        # Personalization based on interests
        interests = psycho.get('interests', [])
        if interests:
            topics = [i['topic'] for i in interests[:3]]
            strategy.append(f"Mention their interest in: {', '.join(topics)}")

        # Based on intent signals
        if 'pricing_interest' in intent.get('signals', []):
            strategy.append("Reference recent pricing page visits. Offer to discuss pricing options.")

        # Based on engagement level
        if intent.get('level') == 'high':
            strategy.append("High intent - suggest immediate demo or sales call.")
        elif intent.get('level') == 'medium':
            strategy.append("Medium intent - share relevant case study or content.")

        # Personal details
        personal_details = psycho.get('personal_details', [])
        if personal_details:
            detail = personal_details[0]
            strategy.append(f"Build rapport by mentioning their {detail['category']}: {detail['detail']}")

        return " ".join(strategy) if strategy else "Generic outreach recommended."
