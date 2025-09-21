"""
Command-line interface for NAMASTE ICD Service.

Provides CLI tools for searching terminology and testing the service.
"""

import asyncio
import argparse
import json
import sys
from typing import Optional

import httpx


class NAMASTECLI:
    """Command-line interface for NAMASTE ICD Service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, system: Optional[str] = None, limit: int = 10):
        """
        Search for terminology concepts.
        
        Args:
            query: Search query string
            system: Terminology system to search
            limit: Maximum number of results
        """
        try:
            params = {"q": query, "limit": limit}
            if system:
                params["system"] = system
            
            response = await self.client.get(
                f"{self.base_url}/autocomplete/terms",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"\n🔍 Search Results for '{query}'")
            print(f"System: {system or 'all'}")
            print(f"Total Results: {data['total_results']}")
            print(f"Execution Time: {data.get('execution_time_ms', 0):.2f}ms")
            print("-" * 80)
            
            for i, result in enumerate(data['results'], 1):
                concept = result['concept']
                print(f"{i}. {concept['code']} - {concept['display']}")
                print(f"   System: {concept['system']}")
                if concept.get('definition'):
                    print(f"   Definition: {concept['definition'][:100]}...")
                
                # Show mappings if available
                if result.get('mappings'):
                    print(f"   Mappings:")
                    for mapping in result['mappings']:
                        print(f"     → {mapping['target_system']}:{mapping['target_code']} "
                              f"({mapping['equivalence']}, confidence: {mapping['confidence']})")
                
                print()
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def translate(self, system: str, code: str):
        """
        Translate a concept between systems.
        
        Args:
            system: Source terminology system
            code: Source concept code
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/translate/{system}/{code}"
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"\n🔄 Translation Results for {system}:{code}")
            print("-" * 80)
            
            if not data.get('parameter'):
                print("No translations found.")
                return
            
            # Group parameters by translation
            translations = []
            current_translation = {}
            
            for param in data['parameter']:
                name = param['name']
                if name == 'target':
                    if current_translation:
                        translations.append(current_translation)
                    current_translation = {
                        'target': param['valueCodeableConcept']['coding'][0]
                    }
                elif name in ['equivalence', 'confidence', 'method', 'evidence']:
                    if name == 'confidence':
                        current_translation[name] = param['valueDecimal']
                    elif name == 'evidence':
                        current_translation[name] = param['valueString']
                    else:
                        current_translation[name] = param['valueString']
            
            if current_translation:
                translations.append(current_translation)
            
            for i, translation in enumerate(translations, 1):
                target = translation['target']
                print(f"{i}. {target['system']}:{target['code']} - {target['display']}")
                print(f"   Equivalence: {translation.get('equivalence', 'unknown')}")
                print(f"   Confidence: {translation.get('confidence', 0.0)}")
                if translation.get('method'):
                    print(f"   Method: {translation['method']}")
                if translation.get('evidence'):
                    print(f"   Evidence: {translation['evidence']}")
                print()
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def health(self):
        """Check service health."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            data = response.json()
            
            print("\n🏥 Service Health Check")
            print("-" * 40)
            print(f"Status: {data['status']}")
            print(f"Service: {data['service']}")
            print(f"Version: {data['version']}")
            print(f"Database: {data['database']}")
            print(f"ICD-11 API: {data['icd11_api']}")
            print(f"ABHA Auth: {data['abha_auth']}")
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def codesystem(self, page: int = 1, page_size: int = 10):
        """
        Get NAMASTE CodeSystem.
        
        Args:
            page: Page number
            page_size: Number of concepts per page
        """
        try:
            params = {"page": page, "page_size": page_size}
            response = await self.client.get(
                f"{self.base_url}/fhir/CodeSystem/namaste",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"\n📚 NAMASTE CodeSystem (Page {page})")
            print(f"Total Concepts: {len(data.get('concept', []))}")
            print("-" * 80)
            
            for concept in data.get('concept', []):
                print(f"• {concept['code']} - {concept['display']}")
                if concept.get('definition'):
                    print(f"  Definition: {concept['definition'][:100]}...")
                print()
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="NAMASTE ICD Service CLI")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Service base URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search terminology")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--system", help="Terminology system (namaste, icd11, all)")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    
    # Translate command
    translate_parser = subparsers.add_parser("translate", help="Translate concept")
    translate_parser.add_argument("--system", required=True, help="Source system")
    translate_parser.add_argument("--code", required=True, help="Source code")
    
    # Health command
    subparsers.add_parser("health", help="Check service health")
    
    # CodeSystem command
    codesystem_parser = subparsers.add_parser("codesystem", help="Get NAMASTE CodeSystem")
    codesystem_parser.add_argument("--page", type=int, default=1, help="Page number")
    codesystem_parser.add_argument("--page-size", type=int, default=10, help="Page size")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = NAMASTECLI(args.base_url)
    
    try:
        if args.command == "search":
            await cli.search(args.query, args.system, args.limit)
        elif args.command == "translate":
            await cli.translate(args.system, args.code)
        elif args.command == "health":
            await cli.health()
        elif args.command == "codesystem":
            await cli.codesystem(args.page, args.page_size)
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())
