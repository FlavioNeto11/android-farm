"""Script para corrigir handles do Instagram existentes no banco"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.db import init_db, get_db_session
from app.config import settings
from sqlalchemy import text
import re


def fix_existing_handles():
    """Corrigir handles do Instagram que estão salvos como email"""
    init_db(settings.database_url)
    session = get_db_session()

    logger.info("Buscando contas Instagram com handle = email...")

    results = session.execute(text(
        "SELECT id, handle FROM accounts WHERE platform = 'instagram' AND handle LIKE '%@%'"
    )).fetchall()

    if not results:
        logger.info("Nenhuma conta Instagram com handle=email encontrada.")
        return

    logger.info(f"Encontradas {len(results)} contas para corrigir.")

    fixed = 0
    for row in results:
        account_id = row[0]
        email_handle = row[1]

        # Extrair prefixo do email (antes do @)
        match = re.match(r'^([^@]+)@', email_handle)
        if match:
            new_handle = match.group(1).lower()
            # Remover caracteres inválidos para Instagram
            new_handle = re.sub(r'[^a-zA-Z0-9_.]', '', new_handle)

            logger.info(f"Corrigindo {account_id}: {email_handle} -> @{new_handle}")

            session.execute(text(
                "UPDATE accounts SET handle = :handle WHERE id = :id"
            ), {"handle": new_handle, "id": account_id})

            fixed += 1
        else:
            logger.warning(f"Não conseguiu extrair handle de: {email_handle}")

    session.commit()
    logger.info(f"Corrigidas {fixed} de {len(results)} contas.")

    # Verificar resultados
    remaining = session.execute(text(
        "SELECT COUNT(*) FROM accounts WHERE platform = 'instagram' AND handle LIKE '%@%'"
    )).scalar()
    logger.info(f"Restantes com handle=email: {remaining}")


if __name__ == "__main__":
    fix_existing_handles()
