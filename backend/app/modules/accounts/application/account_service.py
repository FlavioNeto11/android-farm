from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import List, Optional, Dict
from datetime import datetime

from app.models import Account, AccountStatus, Credential, CredentialStatus, PlatformConfig
from app.modules.accounts.domain.account import PlatformProvider, PersonaData, AccountResult
from app.modules.accounts.platforms.outlook.provider import OutlookProvider
from app.modules.accounts.platforms.instagram.provider import InstagramProvider
from app.modules.proxies.domain.proxy import get_proxy_manager
from app.modules.accounts.platforms.full_signup import FullAccountSignup
from app.modules.accounts.platforms.instagram.verifier import InstagramLoginVerifier
from app.security.secret_store import get_secret_store
from app.shared.events import create_event
from app.config import settings
from app.modules.browsers.domain.browser_profile import get_browser_manager
import logging

logger = logging.getLogger(__name__)


class AccountService:
    """Serviço de gerenciamento de contas"""

    def __init__(self):
        self.providers: Dict[str, PlatformProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Inicializar provedores de plataformas"""
        self.providers = {
            "outlook": OutlookProvider(settings.__dict__),
            "instagram": InstagramProvider(settings.__dict__),
        }
        self.full_signup = FullAccountSignup()

    def get_provider(self, platform: str) -> Optional[PlatformProvider]:
        """Obter provedor de plataforma"""
        return self.providers.get(platform)

    async def request_account_creation(
        self,
        db: Session,
        profile_id: str,
        platforms: List[str],
        persona_data: Dict
    ) -> Account:
        """
        Solicitar criação de conta(s) para uma persona.

        Args:
            db: Sessão do banco
            profile_id: ID da persona
            platforms: Lista de plataformas para criar (outlook, instagram)
            persona_data: Dados da persona

        Returns:
           Conta (status = 'creating' e posteriormente atualizado com resultado)
        """
        persona = PersonaData(
            profile_id=profile_id,
            display_name=persona_data.get("display_name"),
            first_name=persona_data.get("first_name"),
            last_name=persona_data.get("last_name"),
            email=persona_data.get("email") or persona_data.get("username"),
            birth_date=persona_data.get("birth_date"),
            gender=persona_data.get("gender"),
            locale=persona_data.get("locale"),
            username=persona_data.get("username"),
            summary=persona_data.get("summary")
        )

        accounts = []
        proxy_config = None

        if settings.proxy_pool_size > 0:
            try:
                proxy = get_proxy_manager().get_proxy(db)
                if proxy:
                    proxy_config = {
                        "host": proxy.host,
                        "port": proxy.port,
                        "username": proxy.username,
                        "password": None
                    }
                    logger.info(f"Using proxy: {proxy.host}:{proxy.port}")
            except Exception as e:
                logger.warning(f"Proxy selection failed: {e}")

        if len(platforms) == 2 and set(platforms) == {"outlook", "instagram"}:
            return await self._create_full_account_sequence(
                db, profile_id, persona, proxy_config, persona_data
            )

        for platform in platforms:
            provider = self.get_provider(platform)
            if not provider:
                continue

            proxy = None
            if platform in ["outlook", "instagram"] and settings.proxy_pool_size > 0:
                proxy = proxy_config

            if not proxy and settings.proxy_pool_size > 0:
                try:
                    proxy = get_proxy_manager().get_proxy(db)
                    if proxy:
                        proxy_config = {
                            "host": proxy.host,
                            "port": proxy.port,
                            "username": proxy.username,
                            "password": None
                        }
                        logger.info(f"Using proxy for {platform}: {proxy.host}:{proxy.port}")
                except Exception as e:
                    logger.warning(f"Proxy selection failed: {e}")

            account = Account(
                platform=platform,
                profile_id=profile_id,
                status=AccountStatus.creating
            )

            db.add(account)
            db.commit()
            db.refresh(account)

            accounts.append(account)

            try:
                logger.info(f"Creating account for {platform} using Playwright provider")
                result = await provider.create_account(
                    persona_data=persona,
                    proxy_host=proxy_config.get("host") if proxy_config else None,
                    proxy_port=proxy_config.get("port") if proxy_config else None,
                    proxy_username=proxy_config.get("username") if proxy_config else None,
                    proxy_password=proxy_config.get("password") if proxy_config else None,
                    timeout=provider.get_config().get("timeout", 90)
                )

                if result.success:
                    account.status = AccountStatus.ready
                    account.handle = result.handle
                    account.proxy_used = proxy_config.get("host") if proxy_config else None

                    credential = db.query(Credential).filter(Credential.account_id == account.id).first()
                    if credential:
                        credential.login_identifier = result.login_identifier
                        credential.secret_ref = result.credential_ref
                    logger.info(f"Account creation successful for {platform}: {result.handle}")
                else:
                    account.status = AccountStatus.failed
                    account.error_message = result.error_message or "Account creation failed"
                    logger.error(f"Account creation failed for {platform}: {result.error_message}")

                    credential = db.query(Credential).filter(Credential.account_id == account.id).first()
                    if credential:
                        credential.status = CredentialStatus.invalid
                        db.add(credential)

                db.commit()

            except Exception as e:
                logger.error(f"Error during account creation for {platform}: {e}", exc_info=True)
                account.status = AccountStatus.failed
                account.error_message = str(e)

                credential = db.get(Credential, accounts[0].credential.id)
                if credential:
                    credential.status = CredentialStatus.invalid
                    db.add(credential)

                db.commit()

        return accounts[0] if accounts else None

    async def _create_full_account_sequence(
        self,
        db: Session,
        profile_id: str,
        persona: PersonaData,
        proxy_config: Optional[dict],
        persona_data: Dict
    ) -> Optional[Account]:
        """Create both Outlook and Instagram accounts in sequence"""
        outlook_account = None
        instagram_account = None

        try:
            logger.info(f"Starting full account creation sequence for {profile_id}")

            full_signup_result = await self.full_signup.create_full_account(
                persona_data=persona,
                proxy_config=proxy_config,
                timeout=120
            )

            if not full_signup_result.get("verified"):
                logger.error("Full account creation verification failed")
                raise Exception("Full account creation verification failed")

            migration_data = {
                "outlook_success": False,
                "instagram_success": False,
                "error_message": None,
                "error_step": None
            }

            success_result = {}

            try:
                if not full_signup_result.get("outlook_email"):
                    raise Exception("Outlook account creation failed")

                logger.info(f"Outlook account created: {full_signup_result['outlook_email']}")
                success_result["outlook_email"] = full_signup_result["outlook_email"]
                success_result["outlook_password"] = full_signup_result["outlook_password"]
                migration_data["outlook_success"] = True
            except Exception as e:
                logger.error(f"Outlook account creation failed: {e}")
                migration_data["error_message"] = f"Outlook creation failed: {e}"
                migration_data["error_step"] = "outlook_signup"
                success_result["outlook_email"] = None
                success_result["outlook_password"] = None

            if not success_result.get("outlook_email"):
                logger.error("Cannot proceed with Instagram without Outlook account")
                migration_data["error_message"] = "Instagram cannot be created without Outlook account"
                raise Exception("Cannot proceed with Instagram: Outlook account not created")

            if not full_signup_result.get("instagram_handle"):
                logger.error("Instagram account creation failed, but Outlook succeeded")
                migration_data["instagram_success"] = False
                migration_data["error_message"] = migration_data.get("error_message", "")
                if migration_data["error_message"]:
                    migration_data["error_message"] += "; Instagram creation failed"
                else:
                    migration_data["error_message"] = "Instagram account creation failed"
                migration_data["error_step"] = "instagram_signup"
            else:
                logger.info(f"Instagram account created: {full_signup_result['instagram_handle']}")
                success_result["instagram_handle"] = full_signup_result["instagram_handle"]
                success_result["instagram_password"] = full_signup_result["instagram_password"]
                migration_data["instagram_success"] = True
                success_result["instagram_verified"] = False

            secret_store = get_secret_store()

            if migration_data["outlook_success"]:
                outlook_account = Account(
                    platform="outlook",
                    profile_id=profile_id,
                    status=AccountStatus.ready,
                    handle=success_result["outlook_email"],
                    proxy_used=proxy_config.get("host") if proxy_config else None
                )
                db.add(outlook_account)
                db.flush()

                outlook_password_data = success_result["outlook_password"]
                outlook_secret_ref = secret_store.encrypt(outlook_password_data)

                outlook_credential = Credential(
                    account_id=outlook_account.id,
                    login_identifier=success_result["outlook_email"],
                    secret_ref=outlook_secret_ref,
                    status=CredentialStatus.active
                )
                db.add(outlook_credential)

            instagram_account_status = AccountStatus.ready

            if success_result.get("instagram_handle"):
                instagram_handle = success_result["instagram_handle"]
                instagram_password_data = success_result["instagram_password"]

                instagram_account = Account(
                    platform="instagram",
                    profile_id=profile_id,
                    status=instagram_account_status,
                    handle=instagram_handle,
                    proxy_used=proxy_config.get("host") if proxy_config else None,
                    error_message=migration_data.get("error_message")
                )
                db.add(instagram_account)
                db.flush()

                instagram_credential = Credential(
                    account_id=instagram_account.id,
                    login_identifier=instagram_handle,
                    secret_ref=secret_store.encrypt(instagram_password_data),
                    status=CredentialStatus.active
                )
                db.add(instagram_credential)

                if success_result.get("instagram_verified"):
                    instagram_account_status = AccountStatus.ready

            db.commit()

            error_summary = migration_data.get("error_message", "Full account creation completed")
            logger.info(f"Full account creation completed for {profile_id}: {error_summary}")

            if instagram_account:
                return instagram_account
            elif outlook_account:
                return outlook_account
            else:
                return None

        except Exception as e:
            logger.error(f"Full account sequence failed: {e}", exc_info=True)
            db.rollback()

            if outlook_account:
                outlook_account.status = AccountStatus.failed
                db.commit()

            return None


    def get_account(self, db: Session, account_id: str) -> Optional[Account]:
        """Obter conta pelo ID"""
        return db.get(Account, account_id)


    def list_accounts(
        self,
        db: Session,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> List[Account]:
        """
        Listar contas com filtros.

        Args:
            db: Sessão do banco
            platform: Filtro por plataforma
            status: Filtro por status
            profile_id: Filtro por profile_id

        Returns:
            Lista de contas
        """
        query = db.query(Account)

        if platform:
            query = query.filter(Account.platform == platform)

        if status:
            query = query.filter(Account.status == status)

        if profile_id:
            query = query.filter(Account.profile_id == profile_id)

        return query.order_by(Account.created_at.desc()).all()


    def assign_account(
        self,
        db: Session,
        account_id: str,
        profile_id: str
    ) -> bool:
        """Atribuir conta a uma persona (se ainda não atribuída)"""
        account = db.get(Account, account_id)
        if not account:
            return False

        existing = db.query(Account).filter(
            Account.profile_id == profile_id,
            Account.status == AccountStatus.ready
        ).first()

        if existing:
            return False  # Persona já tem conta attr

        account.profile_id = profile_id
        account.status = AccountStatus.ready

        db.commit()

        logger.info(f"Assigned account {account_id} to persona {profile_id}")
        return True


    def delete_account(
        self,
        db: Session,
        account_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Deletar conta"""
        account = db.get(Account, account_id)
        if not account:
            return False

        db.delete(account)
        db.commit()

        logger.info(f"Deleted account {account_id}")
        return True


    def update_account_status(
        self,
        db: Session,
        account_id: str,
        status: str
    ) -> bool:
        """Atualizar status de conta"""
        valid_statuses = [s.value for s in AccountStatus]
        if status not in valid_statuses:
            return False

        account = db.get(Account, account_id)
        if not account:
            return False

        account.status = AccountStatus(status)
        db.commit()

        logger.info(f"Updated account {account_id} status to {status}")
        return True


account_service = AccountService()


def get_account_service() -> AccountService:
    """Obter account service global"""
    return account_service
