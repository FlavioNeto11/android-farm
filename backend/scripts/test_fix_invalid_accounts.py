"""Simplified test script for Instagram account fix - runs directly against the database"""
import sys
import os
import asyncio
from sqlalchemy import create_engine, text

async def test_database_connection():
    """Test if we can connect to the database directly"""
    
    # Use absolute path to the database
    db_path = r'C:\git\android-farm\backend\data\farm.db'
    
    print(f"Testing connection to: {db_path}")
    print(f"File exists: {os.path.exists(db_path)}")
    
    # Try SQLite directly
    try:
        engine = create_engine(f'sqlite:///{db_path}')
        
        with engine.connect() as conn:
            # Check if Instagram accounts exist
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM accounts 
                WHERE platform = 'instagram' AND status = 'ready'
            """))
            
            count = result.scalar()
            print(f"\nInstagram accounts with status='ready': {count}")
            
            if count > 0:
                print("\nRecent accounts:")
                accounts_result = conn.execute(text("""
                    SELECT id, handle, created_at 
                    FROM accounts 
                    WHERE platform = 'instagram' AND status = 'ready'
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                
                for row in accounts_result:
                    print(f"  - ID: {row.id}, Handle: {row.handle}, Created: {row.created_at}")
            
            print("\n[+] Database connection successful!")
            
    except Exception as e:
        print(f"\n[-] Error connecting to database: {e}")

if __name__ == "__main__":
    asyncio.run(test_database_connection())
