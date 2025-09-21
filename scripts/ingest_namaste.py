"""
NAMASTE terminology ingestion script.

Loads NAMASTE concepts from CSV file into the database.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db.session import init_db, AsyncSessionLocal
from app.services.namaste_loader import NamasteLoader
from app.services.mapping_service import MappingService


async def main():
    """Main ingestion function."""
    print("🚀 Starting NAMASTE terminology ingestion...")
    
    # Initialize database
    print("📊 Initializing database...")
    await init_db()
    print("✅ Database initialized")
    
    # Get CSV file path
    csv_path = Path(__file__).parent.parent / "data" / "namaste_sample.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        print("Please ensure the CSV file exists in the data directory.")
        return
    
    print(f"📁 Loading concepts from: {csv_path}")
    
    # Load concepts
    async with AsyncSessionLocal() as db:
        loader = NamasteLoader(db)
        
        print("🔄 Loading NAMASTE concepts...")
        result = await loader.load_from_csv(str(csv_path))
        
        if result['success']:
            print(f"✅ Successfully loaded {result['loaded']} concepts")
            if result['skipped'] > 0:
                print(f"⚠️  Skipped {result['skipped']} existing concepts")
        else:
            print(f"❌ Error loading concepts: {result.get('error', 'Unknown error')}")
            return
        
        # Seed default mappings
        print("🔄 Seeding default mappings...")
        mapping_service = MappingService(db)
        mapping_result = await mapping_service.seed_default_mappings()
        
        print(f"✅ Added {mapping_result['added']} default mappings")
        if mapping_result['skipped'] > 0:
            print(f"⚠️  Skipped {mapping_result['skipped']} existing mappings")
        
        # Get statistics
        print("\n📈 Database Statistics:")
        print("-" * 40)
        
        # Count concepts
        from sqlalchemy import select, func
        from app.db.models import Concept, Mapping
        
        concept_count = await db.execute(select(func.count(Concept.id)))
        total_concepts = concept_count.scalar()
        
        mapping_count = await db.execute(select(func.count(Mapping.id)))
        total_mappings = mapping_count.scalar()
        
        print(f"Total Concepts: {total_concepts}")
        print(f"Total Mappings: {total_mappings}")
        
        # Count by system
        namaste_count = await db.execute(
            select(func.count(Concept.id)).where(Concept.system == "namaste")
        )
        namaste_concepts = namaste_count.scalar()
        
        print(f"NAMASTE Concepts: {namaste_concepts}")
        
        # Count mappings by source system
        namaste_mappings = await db.execute(
            select(func.count(Mapping.id)).where(Mapping.source_system == "namaste")
        )
        namaste_mapping_count = namaste_mappings.scalar()
        
        print(f"NAMASTE Mappings: {namaste_mapping_count}")
    
    print("\n🎉 NAMASTE terminology ingestion completed successfully!")
    print("\nNext steps:")
    print("1. Start the service: uvicorn src.app.main:app --reload --port 8000")
    print("2. Test the API: python src/cli/search_cli.py health")
    print("3. Search concepts: python src/cli/search_cli.py search 'fever'")
    print("4. View documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
