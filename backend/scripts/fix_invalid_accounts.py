"""Correção de contas Instagram existentes inválidas"""
import sys
import os
import asyncio
from sqlalchemy import create_engine, text
import logging

# Configurar caminhos absolutos
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "farm.db")

# Adicionar backend ao path
sys.path.insert(0, PROJECT_ROOT)

# Verificar se o banco existe
if not os.path.exists(DB_PATH):
    print(f"ERRO: Banco de dados não encontrado em: {DB_PATH}")
    sys.exit(1)

# Configurar logging
log_dir = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "fix_invalid_accounts.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar verificador após configurar o path
from app.modules.accounts.platforms.instagram.verifier import InstagramAccountVerifier

async def fix_invalid_accounts():
    """Verificar e corrigir contas Instagram existentes"""
    
    logger.info(f"Usando banco de dados: {DB_PATH}")
    
    # Conectar diretamente ao banco
    engine = create_engine(f"sqlite:///{DB_PATH}")
    verifier = InstagramAccountVerifier()
    
    with engine.connect() as conn:
        # Buscar contas Instagram com status "ready"
        result = conn.execute(text(
            "SELECT id, handle FROM accounts WHERE platform = 'instagram' AND status = 'ready'"
        ))
        instagram_accounts = result.fetchall()
        
        accounts_to_fix = []
        
        logger.info(f"Encontradas {len(instagram_accounts)} contas Instagram com status 'ready'")
        
        for account in instagram_accounts:
            account_id = account.id
            handle = account.handle
            
            if not handle:
                logger.info(f"Conta {account_id} sem handle - pulando")
                continue
            
            logger.info(f"\nVerificando conta {account_id} (handle: @{handle})")
            
            try:
                verification_result = await verifier.verify_account(handle, timeout=15)
                
                if verification_result.get("verified"):
                    logger.info(f"[OK] Conta @{handle} está válida")
                    continue
                else:
                    error_message = verification_result.get("error", "Verification failed")
                    logger.info(f"[FAIL] Conta @{handle} inválida: {error_message}")
                    accounts_to_fix.append({
                        "account_id": account_id,
                        "handle": handle,
                        "error": error_message
                    })
            except Exception as e:
                logger.error(f"[ERROR] Erro ao verificar @{handle}: {e}")
                accounts_to_fix.append({
                    "account_id": account_id,
                    "handle": handle,
                    "error": f"Erro na verificação: {str(e)}"
                })
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Total de contas inválidas a corrigir: {len(accounts_to_fix)}")
    logger.info(f"{'='*60}")
    
    if not accounts_to_fix:
        logger.info("Nenhuma conta inválida encontrada!")
        return
    
    fixed_count = 0
    
    for account_info in accounts_to_fix:
        account_id = account_info["account_id"]
        handle = account_info["handle"]
        error = account_info["error"]
        
        logger.info(f"\nCorrigindo conta {account_id} (@{handle})")
        
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE accounts SET status = 'failed', error_message = :error WHERE id = :account_id"
            ), {"error": error, "account_id": account_id})
            conn.commit()
            
            logger.info(f"[FIXED] Conta @{handle} marcada como FAILED")
        
        fixed_count += 1
    
    logger.info(f"\n{'='*60}")
    logger.info("Revisão concluída:")
    logger.info(f"  - Contas corrigidas: {fixed_count}")
    logger.info(f"  - Contas válidas: {len(instagram_accounts) - fixed_count}")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    try:
        asyncio.run(fix_invalid_accounts())
    except KeyboardInterrupt:
        logger.info("Interrupção pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
