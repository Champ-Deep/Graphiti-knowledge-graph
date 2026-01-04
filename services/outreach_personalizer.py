"""
Outreach Personalization Engine

Uses LLM to generate highly personalized outreach messages based on:
- Comprehensive contact profile
- Intent signals and buying stage
- Psychographic data (interests, personal details)
- Recent engagement history
- Account context
"""
from typing import Dict, List, Optional, Any
import logging
import os

logger = logging.getLogger(__name__)


class OutreachPersonalizer:
    """
    Generate personalized outreach messages using LLM.

    Combines all available prospect data to create highly targeted,
    relevant outreach that resonates with the individual.
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        model: str = "gpt-4",
        api_key: Optional[str] = None
    ):
        """
        Initialize outreach personalizer.

        Parameters
        ----------
        llm_provider : str
            LLM provider: 'openai', 'anthropic', 'openrouter'
        model : str
            Model to use for generation
        api_key : str, optional
            API key (will use environment variable if not provided)
        """
        self.llm_provider = llm_provider
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')

    async def generate_email(
        self,
        profile: Dict[str, Any],
        purpose: str = "intro",
        tone: str = "professional",
        length: str = "short"
    ) -> Dict[str, Any]:
        """
        Generate personalized email based on profile.

        Parameters
        ----------
        profile : dict
            Comprehensive contact profile from ProfileBuilder
        purpose : str
            Email purpose: 'intro', 'follow_up', 'demo_request', 'value_prop'
        tone : str
            Desired tone: 'professional', 'casual', 'friendly', 'urgent'
        length : str
            Email length: 'short' (2-3 paragraphs), 'medium', 'long'

        Returns
        -------
        dict
            {
                'subject': str,
                'body': str,
                'personalization_notes': list,
                'confidence_score': float
            }
        """
        # Build context for LLM
        context = self._build_context(profile)

        # Generate email using LLM
        prompt = self._build_email_prompt(context, purpose, tone, length)

        try:
            result = await self._call_llm(prompt)

            return {
                'subject': result.get('subject'),
                'body': result.get('body'),
                'personalization_notes': result.get('personalization_notes', []),
                'confidence_score': self._calculate_confidence(profile)
            }
        except Exception as e:
            logger.error(f"Error generating email: {e}")
            return {
                'subject': f"Following up on {profile.get('account', {}).get('name')}",
                'body': "Error generating personalized email. Please try again.",
                'personalization_notes': [],
                'confidence_score': 0.0
            }

    async def generate_linkedin_message(
        self,
        profile: Dict[str, Any],
        purpose: str = "connection_request"
    ) -> Dict[str, Any]:
        """
        Generate personalized LinkedIn message.

        Parameters
        ----------
        profile : dict
            Contact profile
        purpose : str
            'connection_request', 'inmail', 'follow_up'

        Returns
        -------
        dict
            {
                'message': str,
                'note': str (for connection requests)
            }
        """
        context = self._build_context(profile)
        prompt = self._build_linkedin_prompt(context, purpose)

        try:
            result = await self._call_llm(prompt)
            return result
        except Exception as e:
            logger.error(f"Error generating LinkedIn message: {e}")
            return {
                'message': "Error generating message",
                'note': ""
            }

    async def generate_call_script(
        self,
        profile: Dict[str, Any],
        call_type: str = "discovery"
    ) -> Dict[str, Any]:
        """
        Generate personalized call script.

        Parameters
        ----------
        profile : dict
            Contact profile
        call_type : str
            'discovery', 'demo', 'closing', 'follow_up'

        Returns
        -------
        dict
            {
                'opening': str,
                'talking_points': list,
                'questions': list,
                'objection_handling': dict,
                'closing': str
            }
        """
        context = self._build_context(profile)
        prompt = self._build_call_script_prompt(context, call_type)

        try:
            result = await self._call_llm(prompt)
            return result
        except Exception as e:
            logger.error(f"Error generating call script: {e}")
            return {
                'opening': "Error generating script",
                'talking_points': [],
                'questions': [],
                'objection_handling': {},
                'closing': ""
            }

    def _build_context(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Build context dictionary from profile for LLM"""
        contact = profile.get('contact', {})
        account = profile.get('account', {})
        psycho = profile.get('psychographics', {})
        engagement = profile.get('engagement', {})
        intent = profile.get('intent', {})
        firmographics = profile.get('firmographics', {})
        technographics = profile.get('technographics', {})

        return {
            # Contact info
            'name': contact.get('name', 'Unknown'),
            'title': contact.get('title'),
            'company': account.get('name'),
            'seniority': contact.get('seniority'),

            # Psychographic insights
            'interests': [i.get('topic') for i in psycho.get('interests', [])[:5]],
            'personal_details': psycho.get('personal_details', [])[:3],
            'topics_discussed': psycho.get('topics_discussed', [])[:5],

            # Engagement data
            'email_engagement': engagement.get('email', {}),
            'web_engagement': engagement.get('web', {}),
            'social_engagement': engagement.get('social', {}),
            'engagement_score': engagement.get('overall_score', 0),

            # Intent data
            'intent_score': intent.get('score', 0),
            'intent_level': intent.get('level', 'low'),
            'intent_signals': intent.get('signals', []),

            # Company context
            'industry': firmographics.get('industry'),
            'employee_count': firmographics.get('employee_count'),
            'technologies': [t.get('name') for t in technographics.get('technologies', [])[:5]],

            # Buying stage
            'buying_stage': self._infer_buying_stage(intent),
        }

    def _build_email_prompt(
        self,
        context: Dict[str, Any],
        purpose: str,
        tone: str,
        length: str
    ) -> str:
        """Build prompt for email generation"""
        return f"""You are an expert sales development representative crafting a personalized outreach email.

CONTEXT ABOUT THE PROSPECT:
Name: {context['name']}
Title: {context['title']}
Company: {context['company']}
Industry: {context['industry']}

INTERESTS & TOPICS:
{', '.join(context['interests']) if context['interests'] else 'No specific interests detected'}

PERSONAL DETAILS:
{self._format_personal_details(context['personal_details'])}

ENGAGEMENT DATA:
- Intent Level: {context['intent_level']} (score: {context['intent_score']}/100)
- Intent Signals: {', '.join(context['intent_signals'])}
- Buying Stage: {context['buying_stage']}
- Email Opens: {context['email_engagement'].get('total_emails', 0)}
- Page Views: {context['web_engagement'].get('total_page_views', 0)}
- High-Intent Pages Visited: {len(context['web_engagement'].get('high_intent_pages', []))}

TECHNOLOGIES THEY USE:
{', '.join(context['technologies']) if context['technologies'] else 'Unknown'}

TASK:
Write a {length} {purpose} email with a {tone} tone.

REQUIREMENTS:
1. Personalize based on their interests, recent activity, or personal details
2. Reference specific intent signals if relevant (e.g., pricing page visit)
3. Match the buying stage - don't be too aggressive if they're early-stage
4. Be authentic and human - avoid salesy language
5. Include a clear, low-friction call-to-action
6. Keep subject line under 50 characters

Return your response as JSON with this structure:
{{
    "subject": "Your subject line",
    "body": "Your email body with \\n for line breaks",
    "personalization_notes": ["List", "of", "personalization", "elements", "used"]
}}
"""

    def _build_linkedin_prompt(self, context: Dict[str, Any], purpose: str) -> str:
        """Build prompt for LinkedIn message generation"""
        return f"""Generate a LinkedIn {purpose} message to:

Name: {context['name']}
Title: {context['title']}
Company: {context['company']}
Interests: {', '.join(context['interests'][:3])}
Intent Level: {context['intent_level']}

LinkedIn messages must be:
- Very concise (under 300 characters for connection requests)
- Reference a mutual interest or common ground
- Avoid being overly salesy
- Have a clear reason for connecting

Return as JSON:
{{
    "message": "Your message text",
    "note": "Connection request note (if applicable)"
}}
"""

    def _build_call_script_prompt(self, context: Dict[str, Any], call_type: str) -> str:
        """Build prompt for call script generation"""
        return f"""Create a {call_type} call script for:

Prospect: {context['name']} - {context['title']} at {context['company']}
Intent: {context['intent_level']} ({context['intent_score']}/100)
Stage: {context['buying_stage']}
Key Interests: {', '.join(context['interests'][:3])}
Recent Activity: {', '.join(context['intent_signals'][:3])}

Return as JSON:
{{
    "opening": "Opening statement (30 seconds)",
    "talking_points": ["Point 1", "Point 2", "Point 3"],
    "questions": ["Discovery question 1", "Question 2"],
    "objection_handling": {{
        "too_expensive": "Response...",
        "not_right_now": "Response..."
    }},
    "closing": "Closing statement with next steps"
}}
"""

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM to generate content"""
        if self.llm_provider == "openai":
            return await self._call_openai(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            import openai
            import json

            openai.api_key = self.api_key

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert sales professional who writes highly personalized, effective outreach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            content = response.choices[0].message.content

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                return {"result": content}

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _format_personal_details(self, details: List[Dict[str, Any]]) -> str:
        """Format personal details for prompt"""
        if not details:
            return "No personal details available"

        formatted = []
        for detail in details[:3]:
            category = detail.get('category', 'Unknown')
            text = detail.get('detail', '')
            formatted.append(f"- {category.title()}: {text}")

        return '\n'.join(formatted)

    def _infer_buying_stage(self, intent_data: Dict[str, Any]) -> str:
        """Infer buying stage from intent signals"""
        signals = intent_data.get('signals', [])

        if any(s in ['pricing_interest', 'sales_inquiry'] for s in signals):
            return 'decision'
        elif any(s in ['product_research', 'validation_seeking'] for s in signals):
            return 'consideration'
        else:
            return 'awareness'

    def _calculate_confidence(self, profile: Dict[str, Any]) -> float:
        """
        Calculate confidence score for personalization quality.

        Higher confidence = more data available = better personalization
        """
        confidence = 0.0

        # Basic contact info (+20)
        contact = profile.get('contact', {})
        if contact.get('name'):
            confidence += 10
        if contact.get('title'):
            confidence += 10

        # Psychographic data (+30)
        psycho = profile.get('psychographics', {})
        if psycho.get('interests'):
            confidence += 15
        if psycho.get('personal_details'):
            confidence += 15

        # Engagement data (+30)
        engagement = profile.get('engagement', {})
        if engagement.get('overall_score', 0) > 20:
            confidence += 15
        if len(engagement.get('email', {}).get('emails', [])) > 0:
            confidence += 15

        # Intent data (+20)
        intent = profile.get('intent', {})
        if intent.get('signals'):
            confidence += 20

        return min(100, confidence)
