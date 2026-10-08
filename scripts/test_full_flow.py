#!/usr/bin/env python
"""Test script for end-to-end account creation: Outlook + Instagram with DB save"""
import asyncio
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "test_full_flow.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from app.db import init_db, get_db_session
from app.config import settings
from app.security.secret_store import init_secret_store, get_secret_store
from app.models import Account, AccountStatus, Credential, CredentialStatus
from app.modules.accounts.domain.account import PersonaData
from app.modules.accounts.platforms.full_signup import FullAccountSignup
from app.modules.browsers.domain.browser_profile import get_browser_manager, init_browser_manager
from app.modules.accounts.platforms.instagram.verifier import InstagramLoginVerifier
from sqlalchemy import text


async def test_full_flow_with_db():
    """Test the full Outlook + Instagram account creation flow with DB save"""

    print("\n" + "="*80)
    print("ANDROID FARM - TEST FULL ACCOUNT CREATION FLOW (with DB save)")
    print("Outlook -> Instagram")
    print("="*80 + "\n")

    result = {
        "start_time": None,
        "end_time": None,
        "persona_id": None,
        "outlook_handle": None,
        "instagram_handle": None,
        "outlook_password": None,
        "instagram_password": None,
        "pass": False,
        "steps": [],
        "errors": []
    }

    try:
        from datetime import datetime, timezone
        result["start_time"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Test started at: {result['start_time']}")

        # Initialize database and secret store
        init_db(settings.database_url)
        init_secret_store(
            key_file=settings.secret_store_key_file,
            storage_path=settings.secret_store_storage_path
        )
        logger.info("Database and secret store initialized")
        result["steps"].append({"step": "db_initialized", "status": "success"})

        # Initialize browser
        init_browser_manager(headless=True, anti_detect=True)
        browser_manager = get_browser_manager()
        logger.info("Browser manager initialized")

        context = await browser_manager.create_context(
            account_id="test-full-flow-db",
            proxy_host=None,
            proxy_port=None,
            proxy_username=None,
            proxy_password=None,
            viewport_size={"width": 1280, "height": 720}
        )
        logger.info("Browser context created")

        outlook_page = await context.new_page()
        instagram_page = await context.new_page()
        logger.info("Browser pages created")

        # Create persona
        persona_id = "test-full-flow-db-001"
        logger.info(f"Test persona ID: {persona_id}")
        result["persona_id"] = persona_id

        persona_data = PersonaData(
            profile_id=persona_id,
            display_name="Test Full Flow",
            first_name="TestFull",
            last_name="Flow",
            email="testfullflow@example.com",
            birth_date="1990-01-01",
            gender="male",
            locale="en_US"
        )
        result["steps"].append({"step": "persona_created", "status": "success"})

        # Run full signup
        logger.info("Starting full account creation...")
        full_signup = FullAccountSignup()

        full_signup_result = await full_signup.create_full_account(
            persona_data=persona_data,
            proxy_config=None,
            timeout=120
        )

        logger.info(f"Full signup result: {full_signup_result}")

        if not full_signup_result.get("verified"):
            error_msg = "Full signup verification failed"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            result["steps"].append({"step": "full_signup", "status": "failed", "error": error_msg})
            raise Exception(error_msg)

        result["outlook_handle"] = full_signup_result.get("outlook_email")
        result["outlook_password"] = full_signup_result.get("outlook_password")
        result["instagram_handle"] = full_signup_result.get("instagram_handle")
        result["instagram_password"] = full_signup_result.get("instagram_password")

        logger.info(f"Outlook: {result['outlook_handle']}")
        logger.info(f"Instagram: @{result['instagram_handle']}")
        result["steps"].append({"step": "full_signup", "status": "success"})

        # Save to database
        logger.info("\n" + "="*80)
        logger.info("SAVING ACCOUNTS TO DATABASE")
        logger.info("="*80 + "\n")

        session = get_db_session()
        secret_store = get_secret_store()

        # Save Outlook account
        outlook_account = Account(
            platform="outlook",
            profile_id=persona_id,
            status=AccountStatus.ready,
            handle=result["outlook_handle"],
        )
        session.add(outlook_account)
        session.flush()

        outlook_secret_ref = secret_store.encrypt(result["outlook_password"])
        outlook_credential = Credential(
            account_id=outlook_account.id,
            login_identifier=result["outlook_handle"],
            secret_ref=outlook_secret_ref,
            status=CredentialStatus.active
        )
        session.add(outlook_credential)
        logger.info(f"Outlook account saved: {result['outlook_handle']} (ID: {outlook_account.id})")

        # Save Instagram account
        instagram_account = Account(
            platform="instagram",
            profile_id=persona_id,
            status=AccountStatus.ready,
            handle=result["instagram_handle"],
        )
        session.add(instagram_account)
        session.flush()

        instagram_secret_ref = secret_store.encrypt(result["instagram_password"])
        instagram_credential = Credential(
            account_id=instagram_account.id,
            login_identifier=result["instagram_handle"],
            secret_ref=instagram_secret_ref,
            status=CredentialStatus.active
        )
        session.add(instagram_credential)
        logger.info(f"Instagram account saved: @{result['instagram_handle']} (ID: {instagram_account.id})")

        session.commit()
        logger.info("Both accounts committed to database!")
        result["steps"].append({"step": "db_save", "status": "success"})

        # Verify in database
        logger.info("\n" + "="*80)
        logger.info("DATABASE VERIFICATION")
        logger.info("="*80 + "\n")

        accounts = session.execute(text(
            "SELECT id, platform, handle, status FROM accounts WHERE profile_id = :pid ORDER BY platform"
        ), {"pid": persona_id}).fetchall()

        for acc in accounts:
            logger.info(f"  {acc.platform}: {acc.handle} (status: {acc.status}, id: {acc.id})")

        if len(accounts) == 2:
            result["steps"].append({"step": "db_verify", "status": "success"})
        else:
            result["errors"].append(f"Expected 2 accounts, found {len(accounts)}")
            result["steps"].append({"step": "db_verify", "status": "failed"})

        # Verify Instagram account exists via HTTP
        logger.info("\n" + "="*80)
        logger.info("INSTAGRAM HTTP VERIFICATION")
        logger.info("="*80 + "\n")

        from app.modules.accounts.platforms.instagram.verifier import InstagramAccountVerifier
        verifier = InstagramAccountVerifier()
        verification = await verifier.verify_account(result["instagram_handle"], timeout=10)

        if verification.get("verified"):
            logger.info(f"[OK] Instagram @{result['instagram_handle']} exists!")
            result["steps"].append({"step": "http_verify", "status": "success"})
        else:
            logger.error(f"[FAIL] Instagram @{result['instagram_handle']} not found")
            result["errors"].append(f"Instagram account not found via HTTP")
            result["steps"].append({"step": "http_verify", "status": "failed"})

        result["pass"] = len(result["errors"]) == 0
        result["end_time"] = datetime.now(timezone.utc).isoformat()

        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Start: {result['start_time']}")
        logger.info(f"End: {result['end_time']}")
        logger.info(f"Persona: {result['persona_id']}")
        logger.info(f"Outlook: {result['outlook_handle']}")
        logger.info(f"Instagram: @{result['instagram_handle']}")
        logger.info(f"Steps: {len(result['steps'])}")
        logger.info(f"Errors: {len(result['errors'])}")
        logger.info(f"RESULT: {'[PASS]' if result['pass'] else '[FAIL]'}")
        logger.info("="*80 + "\n")

        return result

    except Exception as e:
        error_msg = f"Test failed: {e}"
        logger.error(error_msg, exc_info=True)
        from datetime import datetime, timezone
        result["end_time"] = datetime.now(timezone.utc).isoformat()
        result["errors"].append(str(e))
        result["pass"] = False
        return result

    finally:
        try:
            if instagram_page:
                await instagram_page.close()
            if outlook_page:
                await outlook_page.close()
            if context:
                await context.close()
            if browser_manager and browser_manager.playwright:
                await browser_manager.playwright.stop()
            logger.info("Browser resources cleaned up")
        except:
            pass


def main():
    try:
        result = asyncio.run(test_full_flow_with_db())

        if result["pass"]:
            print("\n[PASS] TEST PASSED")
            print(f"- Outlook account created and saved: {result['outlook_handle']}")
            print(f"- Instagram account created and saved: @{result['instagram_handle']}")
            print(f"- Both accounts verified in database")
            print(f"- Instagram account verified via HTTP")
            return 0
        else:
            print("\n[FAIL] TEST FAILED")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        return 2
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
