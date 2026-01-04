"""
Quick Start: Sales Intelligence Demo

A simplified example that works WITHOUT any enrichment APIs.
Perfect for testing the core functionality with just email data.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_requirements():
    """Check if minimum requirements are met"""
    print("🔍 Checking requirements...\n")

    errors = []
    warnings = []

    # Check required environment variables
    required_vars = {
        'NEO4J_URI': 'Neo4j database URI',
        'NEO4J_USER': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password',
        'OPENAI_API_KEY': 'OpenAI API key',
    }

    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            errors.append(f"  ❌ {var} not set ({description})")
        else:
            # Mask sensitive values
            if 'KEY' in var or 'PASSWORD' in var:
                masked = value[:8] + '...' if len(value) > 8 else '***'
                print(f"  ✅ {var}: {masked}")
            else:
                print(f"  ✅ {var}: {value}")

    # Check optional enrichment APIs
    optional_vars = {
        'CLEARBIT_API_KEY': 'Clearbit enrichment',
        'BUILTWITH_API_KEY': 'BuiltWith technographics',
        'PDL_API_KEY': 'People Data Labs',
        'GA4_PROPERTY_ID': 'Google Analytics',
        'LINKEDIN_ACCESS_TOKEN': 'LinkedIn',
    }

    print("\n📊 Optional Integrations:")
    for var, description in optional_vars.items():
        if os.getenv(var):
            print(f"  ✅ {description} enabled")
        else:
            warnings.append(f"  ⚠️  {description} not configured (optional)")

    # Print errors and warnings
    if errors:
        print("\n❌ ERRORS - Required configuration missing:")
        for error in errors:
            print(error)
        print("\nPlease copy .env.example to .env and fill in required values.")
        return False

    if warnings:
        print("\n⚠️  Some optional integrations not configured:")
        for warning in warnings[:2]:  # Show first 2
            print(warning)
        print(f"  ... and {len(warnings) - 2} more")
        print("\nThis is OK! The system will work with email data only.")

    return True


async def main():
    """Run the quick start demo"""
    print("=" * 70)
    print("🚀 SALES INTELLIGENCE QUICK START")
    print("=" * 70)
    print()

    # Check requirements
    if not check_requirements():
        print("\n❌ Setup incomplete. Exiting.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Starting services...")
    print("=" * 70 + "\n")

    try:
        # Import services
        from config.settings import get_settings
        from services.graphiti_service import GraphitiService
        from services.profile_builder import ProfileBuilder

        settings = get_settings()

        # Initialize GraphitiService
        print("🔧 Connecting to knowledge graph...")
        graphiti_service = GraphitiService(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            openai_api_key=settings.openai_api_key,
            openai_base_url=settings.openai_base_url,
            model_name=settings.model_name,
        )

        await graphiti_service.connect()
        print("✅ Connected to knowledge graph\n")

        # Initialize ProfileBuilder (will work even without enrichment APIs)
        print("🔧 Initializing profile builder...")
        enrichment_configs = {}

        if os.getenv('CLEARBIT_API_KEY'):
            from adapters.enrichment_adapters import get_enrichment_adapter
            enrichment_configs['clearbit'] = {'api_key': os.getenv('CLEARBIT_API_KEY')}
            print("  ✅ Clearbit enrichment enabled")

        if os.getenv('BUILTWITH_API_KEY'):
            enrichment_configs['builtwith'] = {'api_key': os.getenv('BUILTWITH_API_KEY')}
            print("  ✅ BuiltWith enrichment enabled")

        if not enrichment_configs:
            print("  ℹ️  No enrichment APIs configured (using knowledge graph data only)")

        profile_builder = ProfileBuilder(
            graphiti_service=graphiti_service,
            enrichment_configs=enrichment_configs
        )
        print("✅ Profile builder ready\n")

        # Demo: Query knowledge graph
        print("=" * 70)
        print("📊 DEMO: Querying Knowledge Graph")
        print("=" * 70 + "\n")

        # Get available accounts
        print("🔍 Searching for accounts in knowledge graph...")

        # Simple query to see what's in the graph
        try:
            results = await graphiti_service.search_account(
                account_name="",  # Empty to search all
                query="What accounts and companies are in the knowledge graph?",
                num_results=10
            )

            nodes = results.get('nodes', [])
            accounts = [n for n in nodes if n.get('entity_type') == 'Account']

            if accounts:
                print(f"\n✅ Found {len(accounts)} account(s):")
                for account in accounts[:5]:
                    print(f"  • {account.get('name', 'Unknown')}")

                # Try to build a profile for the first account
                if accounts:
                    account_name = accounts[0].get('name')
                    print(f"\n📊 Building profile for: {account_name}")
                    print("-" * 70)

                    profile = await profile_builder.build_account_profile(
                        account_name=account_name,
                        enrich=bool(enrichment_configs)  # Only enrich if APIs available
                    )

                    print(f"\n✅ Account Profile:")
                    print(f"  Name: {profile.get('name')}")
                    print(f"  Contacts: {len(profile.get('contacts', []))}")

                    firmographics = profile.get('firmographics', {})
                    if firmographics:
                        print(f"\n  Firmographics:")
                        for key, value in list(firmographics.items())[:5]:
                            print(f"    • {key}: {value}")

                    contacts = profile.get('contacts', [])
                    if contacts:
                        print(f"\n  Key Contacts:")
                        for contact in contacts[:3]:
                            name = contact.get('name', 'Unknown')
                            title = contact.get('title', '')
                            print(f"    • {name}" + (f" - {title}" if title else ""))

            else:
                print("\n⚠️  No accounts found in knowledge graph yet.")
                print("\nTo populate the graph, you need to:")
                print("  1. Configure Gmail OAuth (run setup_gmail_oauth.py)")
                print("  2. Sync emails (this happens automatically when API server starts)")
                print("  3. Or manually add data using the sync service")
                print("\nFor now, the system is ready but has no data to work with.")

        except Exception as e:
            print(f"\n⚠️  Error querying knowledge graph: {e}")
            print("\nThis is normal if the graph is empty or Neo4j isn't running.")

        # Show next steps
        print("\n" + "=" * 70)
        print("✅ QUICK START COMPLETE!")
        print("=" * 70)
        print("\n📚 Next Steps:")
        print("\n1. Start the API server:")
        print("   python api_server.py")
        print("\n2. Test the API:")
        print("   curl http://localhost:8080/health")
        print("\n3. Build a profile via API:")
        print("   curl -X POST http://localhost:8080/api/profiles/account \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"account_name\": \"your-account-name\", \"enrich\": false}'")
        print("\n4. Read the full guide:")
        print("   cat SALES_INTEGRATION_GUIDE.md")
        print("\n5. Run the full example:")
        print("   python examples/sales_outreach_example.py")
        print()

        # Cleanup
        await graphiti_service.disconnect()
        print("✅ Disconnected from knowledge graph\n")

    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nMake sure you've installed all dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nCheck that:")
        print("  1. Neo4j is running (docker-compose up -d)")
        print("  2. Environment variables are set correctly (.env file)")
        print("  3. You have the required permissions")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
