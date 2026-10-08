#!/usr/bin/env python
"""Test script for end-to-end account creation: Outlook + Instagram"""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "test_flow.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from app.db import get_db_context
from sqlalchemy import text
from app.modules.accounts.domain.account import PersonaData
from app.modules.accounts.platforms.full_signup import FullAccountSignup
from app.modules.browsers.domain.browser_profile import get_browser_manager, init_browser_manager
from app.security.secret_store import get_secret_store


async def test_single_account_creation():
    """Test the full Outlook + Instagram account creation flow"""

    print("\n" + "="*80)
    print("TESTING FULL ACCOUNT CREATION FLOW: Outlook -> Instagram")
    print("="*80 + "\n")

    result = {
        "start_time": "",
        "end_time": "",
        "persona_id": None,
        "outlook_account": None,
        "instagram_account": None,
        "outlook_handle": None,
        "instagram_handle": None,
        "outlook_password": None,
        "instagram_password": None,
        "pass": False,
        "steps": [],
        "errors": []
    }

    try:
        from datetime import datetime
        result["start_time"] = datetime.utcnow().isoformat()
        logger.info(f"Test started at: {result['start_time']}")

        browser_manager = None
        outlook_page = None
        instagram_page = None
        context = None

        try:
            from app.modules.browsers.domain.browser_profile import get_browser_manager, init_browser_manager

            init_browser_manager(headless=True, anti_detect=True)
            browser_manager = get_browser_manager()
            logger.info("Browser manager initialized")

            context = await browser_manager.create_context(
                account_id="test-flow-single-account",
                proxy_host=None,
                proxy_port=None,
                proxy_username=None,
                proxy_password=None,
                viewport_size={"width": 1280, "height": 720}
            )
            logger.info("Browser context created")

            first_page = await context.new_page()
            outlook_page = first_page
            logger.info("First page created for Outlook signup")

            second_page = await context.new_page()
            instagram_page = second_page
            logger.info("Second page created for Instagram signup")

            persona_id = "test-persona-123456"
            logger.info(f"Test persona ID: {persona_id}")

            persona_data = PersonaData(
                profile_id=persona_id,
                display_name="Test Flow Account",
                first_name="Test",
                last_name="Flow",
                email="testflow@example.com",
                birth_date="1990-01-01",
                gender="male",
                locale="en_US"
            )

            logger.info("Persona data created")
            result["persona_id"] = persona_id
            result["steps"].append({"step": "persona_created", "status": "success"})

            logger.info("Starting full account creation...")
            full_signup = FullAccountSignup()

            full_signup_result = await full_signup.create_full_account(
                persona_data=persona_data,
                proxy_config=None,
                timeout=120
            )

            logger.info(f"Full signup result: {full_signup_result}")
            result["steps"].append({
                "step": "full_signup_completed",
                "status": "success" if full_signup_result.get("verified") else "failed",
                "result": full_signup_result
            })

            if not full_signup_result.get("verified"):
                error_msg = "Full signup verification failed"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                raise Exception(error_msg)

            success = full_signup_result.get("verified", False)

            result["outlook_email"] = full_signup_result.get("outlook_email")
            result["outlook_account"] = "Created"

            if success:
                result["steps"].append({"step": "outlook_created", "status": "success"})
            else:
                result["steps"].append({"step": "outlook_created", "status": "failed"})

            if full_signup_result.get("outlook_email"):
                logger.info(f"Outlook email: {full_signup_result['outlook_email']}")
                result["outlook_handle"] = full_signup_result["outlook_email"]
                result["outlook_password"] = full_signup_result["outlook_password"]

            result["instagram_handle"] = full_signup_result.get("instagram_handle")
            result["instagram_account"] = full_signup_result.get("instagram_handle", "Not created")

            logger.info("\n" + "="*80)
            logger.info("VERIFICATION STAGE: Database Check")
            logger.info("="*80 + "\n")

            # Verify accounts in database
            try:
                with get_db_context() as db:
                    outlook_accounts = db.execute(
                        text("SELECT id, platform, handle, status, created_at FROM accounts WHERE platform='outlook'")
                    ).fetchall()

                    logger.info(f"\n[Outlook Accounts in Database]")
                    if outlook_accounts:
                        for account in outlook_accounts:
                            logger.info(f"  ID: {account.id}")
                            logger.info(f"  Platform: {account.platform}")
                            logger.info(f"  Handle: {account.handle}")
                            logger.info(f"  Status: {account.status}")
                            logger.info(f"  Created: {account.created_at}")
                    else:
                        logger.info("  No Outlook accounts found in database")

                    instagram_accounts = db.execute(
                        text("SELECT id, platform, handle, status, created_at FROM accounts WHERE platform='instagram'")
                    ).fetchall()

                    logger.info(f"\n[Instagram Accounts in Database]")
                    if instagram_accounts:
                        for account in instagram_accounts:
                            logger.info(f"  ID: {account.id}")
                            logger.info(f"  Platform: {account.platform}")
                            logger.info(f"  Handle: {account.handle}")
                            logger.info(f"  Status: {account.status}")
                            logger.info(f"  Created: {account.created_at}")
                    else:
                        logger.info("  No Instagram accounts found in database")
            except RuntimeError as e:
                if "Database not initialized" in str(e):
                    logger.warning(f"\n[Database not initialized]")
                    logger.warning("Accounts were created successfully, but not stored in database.")
                    logger.info("")
                else:
                    raise

            verification_data = success and full_signup_result.get("outlook_email") and full_signup_result.get("instagram_handle")

            logger.info("\n" + "="*80)
            logger.info("VERIFICATION STAGE: Login Verification (Instagram)")
            logger.info("="*80 + "\n")

            if verification_data and full_signup_result.get("instagram_handle"):
                instagram_login_handle = full_signup_result["instagram_handle"]
                instagram_password = full_signup_result["instagram_password"]

                logger.info(f"Attempting Instagram login for @{instagram_login_handle}...")

                from app.modules.accounts.platforms.instagram.verifier import InstagramLoginVerifier
                login_verifier = InstagramLoginVerifier()

                login_result = await login_verifier.login_and_verify(
                    page=instagram_page,
                    handle=instagram_login_handle,
                    password=instagram_password,
                    timeout=30
                )

                logger.info(f"Login verification result: {login_result}")

                if login_result.get("logged_in"):
                    logger.info(f"[OK] Instagram login successful for @{instagram_login_handle}")
                    result["steps"].append({"step": "instagram_login_verified", "status": "success"})
                    result["pass"] = True
                else:
                    logger.error(f"[FAIL] Instagram login failed for @{instagram_login_handle}")
                    logger.error(f"Error: {login_result.get('error')}")
                    result["steps"].append({"step": "instagram_login_verified", "status": "failed"})
                    result["pass"] = False
                    if login_result.get("error"):
                        result["errors"].append(f"Instagram login failed: {login_result.get('error')}")

            else:
                logger.warning("Cannot verify Instagram login: account not created or missing credentials")
                result["steps"].append({"step": "instagram_login_skipped", "status": "skipped", "reason": "Account not created"})
                login_result = {"logged_in": False, "error": "Not verified"}

            result["end_time"] = datetime.utcnow().isoformat()

            logger.info("\n" + "="*80)
            logger.info("TEST SUMMARY")
            logger.info("="*80)
            logger.info(f"Start Time: {result['start_time']}")
            logger.info(f"End Time: {result['end_time']}")
            logger.info(f"Persona ID: {result['persona_id']}")
            logger.info(f"\n[OUTLOOK ACCOUNT]")
            logger.info(f"  Email Handle: {result['outlook_handle']}")
            logger.info(f"  Account Status: {result['outlook_account']}")
            logger.info(f"\n[INSTAGRAM ACCOUNT]")
            logger.info(f"  Username: {result['instagram_handle']}")
            logger.info(f"  Account Status: {result['instagram_account']}")
            logger.info(f"\nTEST RESULT: {'[PASS]' if result['pass'] else '[FAIL]'}")
            logger.info("="*80 + "\n")

            if result["errors"]:
                logger.error(f"\nErrors encountered:\n")
                for error in result["errors"]:
                    logger.error(f"  - {error}")

            print("\nTest completed!")
            print(f"Final Result: {'PASS' if result['pass'] else 'FAIL'}")
            print(f"Log file: logs/test_flow.log")

            return result

        finally:
            if instagram_page:
                await instagram_page.close()
                logger.info("Instagram page closed")

            if outlook_page:
                await outlook_page.close()
                logger.info("Outlook page closed")

            if context:
                await context.close()
                logger.info("Browser context closed")

            if browser_manager and browser_manager.playwright:
                await browser_manager.playwright.stop()
                logger.info("Browser playwright stopped")

    except Exception as e:
        error_msg = f"Test failed: {e}"
        logger.error(error_msg, exc_info=True)
        result["end_time"] = datetime.utcnow().isoformat()
        result["errors"].append(str(e))
        result["pass"] = False
        print(f"\n[FAIL] Test FAILED: {error_msg}")
        return result


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("ANDROID FARM - TEST FULL ACCOUNT CREATION FLOW")
    print("Outlook -> Instagram")
    print("="*80 + "\n")

    try:
        result = asyncio.run(test_single_account_creation())

        if result["pass"]:
            print("\n[PASS] TEST PASSED")
            print("\nThe flow is working correctly!")
            print("- Outlook account created")
            print("- Instagram account created")
            print("- Instagram credentials work")
            return 0
        else:
            print("\n[FAIL] TEST FAILED")
            print("\nErrors found:")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 2
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
