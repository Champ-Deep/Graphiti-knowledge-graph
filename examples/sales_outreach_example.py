"""
Example: Using the Knowledge Graph for Sales Outreach

This demonstrates how to use the comprehensive profile builder
to create highly personalized outreach for sales prospects.
"""
import asyncio
import os
import json
from dotenv import load_dotenv

from services.graphiti_service import GraphitiService
from services.profile_builder import ProfileBuilder
from services.outreach_personalizer import OutreachPersonalizer
from config.settings import get_settings

# Load environment variables
load_dotenv()


async def main():
    """Run the sales outreach example"""

    # Initialize services
    settings = get_settings()

    graphiti_service = GraphitiService(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        openai_api_key=settings.openai_api_key,
        openai_base_url=settings.openai_base_url,
        model_name=settings.model_name,
    )

    await graphiti_service.connect()
    print("✓ Connected to knowledge graph")

    # Configure enrichment APIs (optional - comment out if you don't have API keys)
    enrichment_configs = {}

    if os.getenv('CLEARBIT_API_KEY'):
        enrichment_configs['clearbit'] = {'api_key': os.getenv('CLEARBIT_API_KEY')}
        print("✓ Clearbit enrichment enabled")

    if os.getenv('BUILTWITH_API_KEY'):
        enrichment_configs['builtwith'] = {'api_key': os.getenv('BUILTWITH_API_KEY')}
        print("✓ BuiltWith enrichment enabled")

    # Initialize ProfileBuilder
    profile_builder = ProfileBuilder(
        graphiti_service=graphiti_service,
        enrichment_configs=enrichment_configs
    )

    # Initialize OutreachPersonalizer
    outreach_personalizer = OutreachPersonalizer(
        llm_provider="openai",
        model=os.getenv('OUTREACH_MODEL', 'gpt-4'),
        api_key=settings.openai_api_key
    )

    print("\n" + "="*60)
    print("SALES OUTREACH KNOWLEDGE GRAPH DEMO")
    print("="*60)

    # Example 1: Build contact profile
    print("\n📊 Example 1: Build Comprehensive Contact Profile")
    print("-" * 60)

    contact_profile = await profile_builder.build_contact_profile(
        account_name="acme-corp",
        contact_email="john.smith@acme.com",  # Replace with real contact
        enrich=True  # Enable enrichment (requires API keys)
    )

    print(f"\nContact: {contact_profile['contact'].get('name', 'Unknown')}")
    print(f"Title: {contact_profile['contact'].get('title', 'Unknown')}")
    print(f"Account: {contact_profile['account'].get('name', 'Unknown')}")

    print(f"\n💡 Intent Score: {contact_profile['intent'].get('score', 0)}/100")
    print(f"Intent Level: {contact_profile['intent'].get('level', 'unknown').upper()}")
    print(f"Signals: {', '.join(contact_profile['intent'].get('signals', []))}")

    print(f"\n🎯 Engagement Score: {contact_profile['engagement'].get('overall_score', 0)}/100")

    # Show interests
    interests = contact_profile['psychographics'].get('interests', [])
    if interests:
        print(f"\n💭 Interests:")
        for interest in interests[:5]:
            print(f"  - {interest.get('topic')} (level: {interest.get('level', 'medium')})")

    # Show personal details
    personal_details = contact_profile['psychographics'].get('personal_details', [])
    if personal_details:
        print(f"\n👤 Personal Details:")
        for detail in personal_details[:3]:
            print(f"  - {detail.get('category')}: {detail.get('detail')}")

    # Example 2: Build account profile
    print("\n\n🏢 Example 2: Build Account Profile")
    print("-" * 60)

    account_profile = await profile_builder.build_account_profile(
        account_name="acme-corp",
        enrich=True
    )

    print(f"\nAccount: {account_profile.get('name')}")
    print(f"Contacts: {len(account_profile.get('contacts', []))} people")

    firmographics = account_profile.get('firmographics', {})
    if firmographics:
        print(f"\n📈 Firmographics:")
        print(f"  Industry: {firmographics.get('industry', 'Unknown')}")
        print(f"  Employee Count: {firmographics.get('employee_count', 'Unknown')}")
        print(f"  Revenue: {firmographics.get('revenue', 'Unknown')}")

    technographics = account_profile.get('technographics', {})
    technologies = technographics.get('technologies', [])
    if technologies:
        print(f"\n🔧 Technologies:")
        for tech in technologies[:5]:
            tech_name = tech if isinstance(tech, str) else tech.get('name', 'Unknown')
            print(f"  - {tech_name}")

    # Example 3: Generate personalized email
    print("\n\n✉️ Example 3: Generate Personalized Outreach Email")
    print("-" * 60)

    email = await outreach_personalizer.generate_email(
        profile=contact_profile,
        purpose="intro",
        tone="professional",
        length="short"
    )

    print(f"\nSubject: {email.get('subject')}")
    print(f"\nBody:\n{email.get('body')}")
    print(f"\n📝 Personalization Notes:")
    for note in email.get('personalization_notes', []):
        print(f"  - {note}")
    print(f"\nConfidence Score: {email.get('confidence_score', 0)}/100")

    # Example 4: Generate LinkedIn message
    print("\n\n💼 Example 4: Generate LinkedIn Connection Request")
    print("-" * 60)

    linkedin_msg = await outreach_personalizer.generate_linkedin_message(
        profile=contact_profile,
        purpose="connection_request"
    )

    print(f"\nMessage:\n{linkedin_msg.get('message')}")
    if linkedin_msg.get('note'):
        print(f"\nConnection Note:\n{linkedin_msg.get('note')}")

    # Example 5: Generate call script
    print("\n\n📞 Example 5: Generate Sales Call Script")
    print("-" * 60)

    call_script = await outreach_personalizer.generate_call_script(
        profile=contact_profile,
        call_type="discovery"
    )

    print(f"\nOpening:\n{call_script.get('opening')}")
    print(f"\nTalking Points:")
    for i, point in enumerate(call_script.get('talking_points', []), 1):
        print(f"  {i}. {point}")
    print(f"\nDiscovery Questions:")
    for i, question in enumerate(call_script.get('questions', []), 1):
        print(f"  {i}. {question}")

    # Example 6: Query using REST API
    print("\n\n🌐 Example 6: Using REST API")
    print("-" * 60)
    print("\nYou can also use the REST API for integration with other tools:")
    print("\nEndpoints available:")
    print("  POST /api/profiles/contact - Build contact profile")
    print("  POST /api/profiles/account - Build account profile")
    print("  POST /api/outreach/generate - Generate personalized outreach")
    print("  GET  /api/accounts/{name}/intent - Get intent score")
    print("  GET  /api/accounts/{name}/firmographics - Get firmographic data")

    print("\nExample API call:")
    print("""
    import requests

    response = requests.post("http://localhost:8080/api/profiles/contact", json={
        "account_name": "acme-corp",
        "contact_email": "john.smith@acme.com",
        "enrich": true
    })

    profile = response.json()['profile']
    print(f"Intent Score: {profile['intent']['score']}")
    """)

    # Cleanup
    await graphiti_service.disconnect()
    print("\n✓ Disconnected from knowledge graph")

    print("\n" + "="*60)
    print("Demo complete! 🎉")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
