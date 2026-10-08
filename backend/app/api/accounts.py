"""Rotas de gerenciamento de contas"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os

from app.db import get_db_context
from app.modules.accounts.application.account_service import get_account_service
from app.modules.accounts.domain.account import PersonaData
from app.models import Account, AccountStatus, Credential
from app.security.secret_store import get_secret_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreationRequest(BaseModel):
    profile_id: str
    platforms: List[str]
    persona_data: dict


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
async def request_account_creation(request: AccountCreationRequest):
    """Solicitar criação de conta(s) para uma persona"""
    try:
        with get_db_context() as db:
            service = get_account_service()
            account = await service.request_account_creation(
                db=db,
                profile_id=request.profile_id,
                platforms=request.platforms,
                persona_data=request.persona_data
            )

            if not account:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No valid account platforms found"
                )

            return {
                "account_id": account.id,
                "platform": account.platform,
                "status": account.status.value,
                "message": "Account creation request submitted"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account creation request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{account_id}")
async def get_account(account_id: str):
    """Obter status de uma conta"""
    with get_db_context() as db:
        service = get_account_service()
        account = service.get_account(db, account_id)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        return {
            "id": account.id,
            "platform": account.platform,
            "handle": account.handle,
            "status": account.status.value,
            "profile_id": account.profile_id,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            "error_message": account.error_message
        }


@router.get("")
async def list_accounts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    profile_id: Optional[str] = None
):
    """Listar contas com filtros opcionais"""
    with get_db_context() as db:
        service = get_account_service()
        accounts = service.list_accounts(
            db=db,
            platform=platform,
            status=status,
            profile_id=profile_id
        )

        return {
            "accounts": [
                {
                    "id": a.id,
                    "platform": a.platform,
                    "handle": a.handle,
                    "status": a.status.value,
                    "profile_id": a.profile_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in accounts
            ],
            "total": len(accounts)
        }


@router.post("/{account_id}/assign")
async def assign_account(account_id: str, profile_id: str):
    """Atribuir conta a uma persona"""
    try:
        with get_db_context() as db:
            service = get_account_service()
            success = service.assign_account(db=db, account_id=account_id, profile_id=profile_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Persona already has a ready account"
                )

            return {
                "message": "Account assigned successfully",
                "account_id": account_id,
                "profile_id": profile_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """Deletar conta"""
    with get_db_context() as db:
        service = get_account_service()
        success = service.delete_account(db=db, account_id=account_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        return {
            "message": "Account deleted successfully",
            "account_id": account_id
        }


@router.get("/{account_id}/credentials")
async def get_account_credentials(account_id: str):
    """Obter credenciais descriptografadas de uma conta"""
    with get_db_context() as db:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        credential = db.query(Credential).filter(Credential.account_id == account_id).first()
        if not credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

        try:
            secret_store = get_secret_store()
            password = secret_store.decrypt(credential.secret_ref)
            return {
                "email": credential.login_identifier,
                "password": password,
                "platform": account.platform,
            }
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt credential")


@router.get("/{account_id}/evidence")
async def get_account_evidence(account_id: str):
    """Obter evidências de uma conta (screenshots, logs)"""
    evidence_dir = "./data/evidence"
    evidence_files = []

    if os.path.exists(evidence_dir):
        for filename in os.listdir(evidence_dir):
            if account_id in filename:
                file_path = os.path.join(evidence_dir, filename)
                evidence_files.append({
                    "account_id": account_id,
                    "evidence_type": "screenshot" if filename.endswith(('.png', '.jpg', '.jpeg')) else "log",
                    "timestamp": "",
                    "screenshot_url": f"/api/evidence/{filename}",
                    "description": f"Evidência: {filename}",
                })

    return evidence_files
