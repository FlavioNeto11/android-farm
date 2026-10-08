"""Script para identificar e corrigir contas Instagram inválidas no banco"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import logging
import asyncio
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.db import init_db, get_db_session
from app.config import settings
from app.modules.accounts.platforms.instagram.verifier import InstagramAccountVerifier
from sqlalchemy import text


async def verify_and_fix_accounts():
    """Verificar contas Instagram e marcar as inválidas como 'failed'"""
    init_db(settings.database_url)
    session = get_db_session()

    verifier = InstagramAccountVerifier()

    logger.info("="*80)
    logger.info("Verificando contas Instagram no banco de dados")
    logger.info("="*80 + "\n")

    results = session.execute(text(
        "SELECT id, handle, status, created_at FROM accounts WHERE platform = 'instagram' ORDER BY created_at DESC"
    )).fetchall()

    if not results:
        logger.info("Nenhuma conta Instagram encontrada no banco de dados.")
        return

    logger.info(f"Encontradas {len(results)} contas Instagram para verificar.\n")

    fixed = 0
    kept_ready = 0
    kept_existing = 0
    total_verified = 0
    total_not_found = 0

    for account_id, handle, status, created_at in results:
        logger.info(f"\nVerificando: @{handle}")
        logger.info(f"  ID: {account_id}")
        logger.info(f"  Status atual: {status}")
        logger.info(f"  Criada em: {created_at}")

        # Verificar se a conta existe no Instagram
        verification = await verifier.verify_account(handle, timeout=10)
        total_verified += 1

        if verification["verified"]:
            # Verifica conteúdo para confirmar que existe
            verified_content = verification.get("content_sample", "")

            if "available" in verified_content.lower() or "not found" in verified_content.lower():
                logger.info(f"  Resultado: HTTP 200 mas perfil não existe (conteúdo indica indisponível)")
                logger.info(f"  Ação: Marcar como FAILED")
                session.execute(text(
                    "UPDATE accounts SET status = 'failed' WHERE id = :id"
                ), {"id": account_id})
                session.execute(text(
                    "UPDATE accounts SET error_message = :error WHERE id = :id"
                ), {
                    "id": account_id,
                    "error": "Instagram account verification failed - account does not exist or is not accessible"
                })
                fixed += 1
            else:
                logger.info(f"  Resultado: Conta EXISTE")
                if status == "ready":
                    logger.info(f"  Status corrigido de 'ready' para manter consistência")
                    session.execute(text(
                        "UPDATE accounts SET status = 'ready' WHERE id = :id"
                    ), {"id": account_id})
                    kept_ready += 1
                else:
                    kept_existing += 1
        else:
            logger.info(f"  Resultado: Conforme verificação HTTP - perfil NÃO existe")
            logger.info(f"  Ação: Marcar como FAILED")
            session.execute(text(
                "UPDATE accounts SET status = 'failed' WHERE id = :id"
            ), {"id": account_id})
            session.execute(text(
                "UPDATE accounts SET error_message = :error WHERE id = :id"
            ), {
                "id": account_id,
                "error": "Instagram account verification failed - account does not exist"
            })
            fixed += 1

    session.commit()

    # Relatório finall
    logger.info("\n" + "="*80)
    logger.info("RELATÓRIO DE VERIFICAÇÃO")
    logger.info("="*80)
    logger.info(f"Contas verificadas: {total_verified}")
    logger.info(f"Contas que EXISTEM: {kept_ready + kept_existing}")
    logger.info(f" Contas no status 'ready' (existe): {kept_ready}")
    logger.info(f" Contas no status diferente (existe): {kept_existing}")
    logger.info(f"Contas que NÃO EXISTEM (agora FAILED): {fixed}")
    logger.info("")
    logger.info(f"Contas configuradas como READY: {kept_ready}")
    logger.info(f"Contas marcadas como FAILED: {fixed}")
    logger.info("")

    if fixed > 0:
        logger.info(f"Ação recomendada: Os {fixed} perfis não-existentes foram marcados como 'failed'")
        logger.info("Acesse o painel de admin para revisar essas contas e decidir o plano de ação.")

    print("\n" + "="*80)
    print("VERIFICAÇÃO FINALIZADA")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(verify_and_fix_accounts())
