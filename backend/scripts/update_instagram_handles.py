"""Script para capturar handles reais do Instagram para contas existentes."""
import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_context, init_db
from app.models import Account, AccountStatus
from app.modules.browsers.domain.browser_profile import get_browser_manager, init_browser_manager
from app.security.secret_store import get_secret_store, init_secret_store
from app.config import settings


async def extract_instagram_handle(account_id: str, email: str, password: str) -> str | None:
    """Navegar para o Instagram e capturar o handle real."""
    browser_manager = get_browser_manager()
    page = None
    context = None

    try:
        # Criar um contexto de navegador para a conta
        context = await browser_manager.create_context(
            account_id=account_id,
            viewport_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # Login no Instagram com email/senha
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Debug: salvar screenshot
        await page.screenshot(path=f"debug_login_{account_id}_01.png")

        # Preencher login
        username_input = page.locator('input[name="username"]').first
        password_input = page.locator('input[name="password"]').first

        if await username_input.count():
            await username_input.fill(email)
        if await password_input.count():
            await password_input.fill(password)

        await asyncio.sleep(2)

        # Debug: screenshot após preencher
        await page.screenshot(path=f"debug_login_{account_id}_02.png")

        # Clicar em login
        login_btn = page.locator('button:has-text("Log in"), button:has-text("Entrar")').first
        if await login_btn.count():
            await login_btn.click()
            await asyncio.sleep(5)
            await page.screenshot(path=f"debug_login_{account_id}_03.png")

        # Verificar se está logado (redireciona para feed ou pede salvar info)
        try:
            not_now = page.locator('button:has-text("Not now"), button:has-text("Agora não")').first
            if await not_now.count():
                await not_now.click()
                await asyncio.sleep(3)
                await page.screenshot(path=f"debug_login_{account_id}_04.png")
        except:
            pass

        # Debug: screenshot antes de navegar para settings
        await page.screenshot(path=f"debug_login_{account_id}_05.png")

        # Navegar para settings para capturar username
        await page.goto("https://www.instagram.com/accounts/edit/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        await page.screenshot(path=f"debug_login_{account_id}_06.png")

        # Capturar do campo username
        username_input = page.locator('input[name="username"]').first
        if await username_input.count():
            username = await username_input.input_value()
            if username and username.strip() and '@' not in username:
                return username.strip()

        # Tentar capturar da URL
        current_url = page.url
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', current_url)
        if match and match.group(1) not in ('accounts', 'explore', 'reels', 'direct', 'settings'):
            return match.group(1)

        return None

    except Exception as e:
        print(f"  Erro ao extrair handle: {e}")
        return None

    finally:
        if page:
            await page.close()


async def main():
    """Atualizar handles de contas Instagram existentes."""
    print("Capturando handles reais do Instagram para contas existentes...")

    # Inicializar dependências
    init_db(settings.database_url)
    init_browser_manager(headless=True, anti_detect=True)
    init_secret_store(key_file=settings.secret_store_key_file, storage_path=settings.secret_store_storage_path)

    with get_db_context() as db:
        instagram_accounts = (
            db.query(Account)
            .filter(Account.platform == "instagram", Account.status == AccountStatus.ready)
            .all()
        )

        print(f"Encontradas {len(instagram_accounts)} contas Instagram para atualizar.")

        # Buscar credenciais associadas
        from app.models import Credential

        secret_store = get_secret_store()
        updated = 0

        for account in instagram_accounts:
            print(f"\nProcessando conta {account.id} (handle atual: {account.handle})")

            # Buscar credencial
            credential = db.query(Credential).filter(Credential.account_id == account.id).first()
            if not credential:
                print(f"  Sem credencial, pulando.")
                continue

            email = credential.login_identifier or account.handle
            password = None
            if credential.secret_ref:
                try:
                    password = secret_store.decrypt(credential.secret_ref)
                except Exception as e:
                    print(f"  Erro ao descriptografar senha: {e}")
                    continue

            if not password:
                print(f"  Sem senha, pulando.")
                continue

            print(f"  Tentando login com {email}...")
            handle = await extract_instagram_handle(account.id, email, password)

            if handle and '@' not in handle:
                print(f"  Handle capturado: @{handle}")
                account.handle = handle
                db.commit()
                updated += 1
            else:
                print(f"  Não foi possível capturar o handle real.")

        print(f"\n{updated} de {len(instagram_accounts)} contas atualizadas com handles reais.")


if __name__ == "__main__":
    asyncio.run(main())
