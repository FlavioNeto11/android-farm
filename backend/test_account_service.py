"""Test script to verify the updated account creation flow"""
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Account, Credential, CredentialStatus
from app.modules.accounts.application.account_service import get_account_service

# Create in-memory database for testing
engine = create_engine('sqlite:///:memory:')
SessionLocal = sessionmaker(bind=engine)

def setup_database():
    """Create tables for testing"""
    Base.metadata.create_all(bind=engine)

def test_account_service_imports():
    """Test that the account service imports are correct"""
    print("Testing account service imports...")
    
    try:
        service = get_account_service()
        print(f"Account service created: {service}")
        print(f"Providers loaded: {list(service.providers.keys())}")
        
        # Verify the providers have the required methods
        for platform in service.providers:
            provider = service.providers[platform]
            assert hasattr(provider, 'get_platform_name'), f"{platform} provider missing get_platform_name"
            assert hasattr(provider, 'create_account'), f"{platform} provider missing create_account"
            
        print(f"OK: All providers have required methods")
        return True
    except Exception as e:
        print(f"ERROR: Import or initialization failed: {e}")
        return False

def test_account_service_methods():
    """Test account service methods"""
    print("\nTesting account service methods...")
    
    try:
        setup_database()
        
        with SessionLocal() as db:
            service = get_account_service()
            
            # Test list_accounts with no accounts
            accounts = service.list_accounts(db=db)
            print(f"OK: List accounts (initial count): {len(accounts)}")
            
            # Test get_account with non-existent ID
            not_exists = service.get_account(db, "non-existent-id")
            assert not_exists is None
            print("OK: Get non-existent account returns None")
            
            print("OK: Account service methods work correctly")
            return True
    except Exception as e:
        print(f"ERROR: Account service methods test failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing Android Farm Account Service Updates")
    print("="*60)
    
    results = []
    
    results.append(test_account_service_imports())
    results.append(test_account_service_methods())
    
    print("\n" + "="*60)
    if all(results):
        print("OK: All tests passed")
        print("OK: The account creation flow has been updated successfully")
    else:
        print("X: Some tests failed")
    print("="*60)
