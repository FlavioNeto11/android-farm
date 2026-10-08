"""Script para criar contas Instagram para todas as personas sem conta no banco principal.

Este script conecta ao banco de dados do main project e identifica personas que não possuem
contas Instagram, solicitando sua criação através do android-farm.
"""
import sys
import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

# Adicionar o caminho do projecto para importar módulos
sys.path.insert(0, r"C:\git\android")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PersonaAccountCreator:
    """Classe para gerenciar a criação de contas para personas."""

    def __init__(self, main_db_path: str = r"C:\git\android\data\poc.sqlite3"):
        self.main_db_path = main_db_path
        self.main_db_url = f"sqlite:///{main_db_path}"

    def get_personas_without_instagram(self) -> List[Dict]:
        """Obter listagem de personas sem conta Instagram.

        Verifica se a persona não tem username no instagram_profiles ou tem username vazio.
        """
        engine = create_engine(self.main_db_url)

        with engine.connect() as conn:
            # Query para encontrar personas que não possuem conta Instagram
            query = text("""
                SELECT
                    p.id,
                    p.name,
                    p.summary,
                    p.traits
                FROM personas p
                LEFT JOIN instagram_profiles ip ON p.id = ip.persona_id AND ip.username <> ''
                WHERE ip.id IS NULL
                ORDER BY p.created_at DESC
            """)

            result = conn.execute(query)
            personas = []

            for row in result:
                persona_id = row.id
                name = row.name
                summary = row.summary
                traits_str = row.traits

                # Parse traits JSON
                traits = {}
                if traits_str and traits_str != "":
                    try:
                        traits = json.loads(traits_str) if isinstance(traits_str, str) else traits_str
                    except json.JSONDecodeError:
                        pass

                # Extrair informacoes da persona
                persona_info = self._extract_persona_data(name, summary, traits)
                persona_info["id"] = persona_id

                personas.append(persona_info)

        logger.info(f"Found {len(personas)} personas without Instagram accounts")
        return personas

    def _extract_persona_data(self, name: str, summary: str, traits: Dict) -> Dict:
        """Extrair dados estruturados da persona para payload da API."""
        # Extrair partes do nome
        if " " in name:
            parts = name.rsplit(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
        else:
            first_name = name
            last_name = ""

        # Extrair informações básicas do summary
        email = f"{name.lower().replace(' ', '.')}@example.invalid"
        display_name = name

        # Usar traits se disponíveis
        trait_values = list(traits.values()) if traits else []

        data = {
            "display_name": display_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "username": "",  # Sem conta
            "birth_date": "1990-01-01",  # Default se não disponível
            "gender": "other",  # Default se não disponível
            "locale": "pt_BR"  # Default
        }

        # Extrair gênero do summary se disponível
        summary_lower = summary.lower() if summary else ""
        if "masculino" in summary_lower or "homem" in summary_lower:
            data["gender"] = "male"
        elif "feminino" in summary_lower or "mulher" in summary_lower:
            data["gender"] = "female"

        return data

    async def check_existing_account(self, persona_id: str) -> bool:
        """Verificar se persona já tem qualquer conta no android-farm.

        Args:
            persona_id: ID da persona

        Returns:
            True se a persona já possui qualquer conta, False caso contrário
        """
        url = f"http://localhost:8001/api/accounts?profile_id={persona_id}"

        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        accounts = data.get("accounts", [])
                        # Verificar se há qualquer conta existente
                        return len(accounts) > 0

        except Exception as e:
            logger.warning(f"Error checking existing account for persona {persona_id}: {e}")

        return False

    async def create_account_for_persona(self, persona_id: str, persona_data: Dict) -> Dict:
        """Solicitar criação de conta Instagram para uma persona.

        Args:
            persona_id: ID da persona
            persona_data: Dados estruturados da persona

        Returns:
            Dicionário com resultado da criação
        """
        url = "http://localhost:8001/api/accounts/request"

        payload = {
            "profile_id": persona_id,
            "platforms": ["outlook", "instagram"],
            "persona_data": persona_data
        }

        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=120)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()

                    if response.status == 202:
                        return {
                            "persona_id": persona_id,
                            "status": "success",
                            "message": "Account creation requested (Outlook + Instagram)",
                            "account_id": result.get("account_id"),
                            "platform": result.get("platform"),
                            "response": result
                        }
                    else:
                        error_detail = result.get("detail", "Unknown error")
                        return {
                            "persona_id": persona_id,
                            "status": "failed",
                            "message": f"API error: {response.status} - {error_detail}",
                            "response": result
                        }

        except asyncio.TimeoutError:
            logger.error(f"Timeout creating account for persona {persona_id}")
            return {
                "persona_id": persona_id,
                "status": "failed",
                "message": "Timeout creating account (120s)"
            }
        except Exception as e:
            logger.error(f"Error creating account for persona {persona_id}: {e}", exc_info=True)
            return {
                "persona_id": persona_id,
                "status": "failed",
                "message": f"Error: {str(e)}"
            }

    async def process_all_personas(self, delay_seconds: int = 10, max_retries: int = 3) -> Dict:
        """Processar todas as personas sem conta e criar contas Instagram.

        Returns:
            Relatório final com contagem de sucessos e falhas
        """
        result = {
            "total_personas": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "results": []
        }

        # Obter personas
        personas = self.get_personas_without_instagram()
        result["total_personas"] = len(personas)

        # Processar cada persona
        for idx, persona in enumerate(personas, 1):
            persona_id = persona["id"]
            persona_name = persona.get("name", "Unknown")

            logger.info(f"Processing persona {idx}/{len(personas)}: {persona_name} ({persona_id})")

            # Verificar se já existe conta
            if await self.check_existing_account(persona_id):
                logger.info(f"Persona {persona_id} já possui conta ativa, pulando...")
                result["skipped"] += 1
                result["results"].append({
                    "persona_id": persona_id,
                    "status": "skipped",
                    "message": "Persona already has an active account"
                })
                continue

            # Criar conta
            creation_result = await self.create_account_for_persona(
                persona_id=persona_id,
                persona_data=persona
            )

            result["results"].append(creation_result)

            # Atualizar contagem
            if creation_result["status"] == "success":
                result["successful"] += 1
            else:
                result["failed"] += 1

            # Delay após sucesso ou falha
            if delay_seconds > 0:
                logger.info(f"Waiting {delay_seconds} seconds before next persona...")
                await asyncio.sleep(delay_seconds)

            # Tentar novamente em caso de falha
            if creation_result["status"] == "failed" and max_retries > 0:
                logger.info(f"Retry attempt {max_retries} for persona {persona_id}")
                for retry in range(max_retries):
                    await asyncio.sleep(2 * (retry + 1))
                    creation_result = await self.create_account_for_persona(
                        persona_id=persona_id,
                        persona_data=persona
                    )
                    if creation_result["status"] == "success":
                        result["successful"] += 1
                        result["failed"] = max(0, result["failed"] - 1)
                        break
                    result["results"][-1] = creation_result

        return result

    def generate_report(self, results: Dict) -> str:
        """Gerar relatório formatado do processo."""
        report = []
        report.append("=" * 80)
        report.append("RELATÓRIO: CRIAÇÃO DE CONTAS INSTAGRAM PARA PERSONAS")
        report.append("=" * 80)
        report.append(f"Total de personas processadas: {results['total_personas']}")
        report.append(f"Contas criadas com sucesso: {results['successful']}")
        report.append(f"Contas já existentes (puladas): {results['skipped']}")
        report.append(f"Falhas: {results['failed']}")
        report.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)

        # Detalhes de cada pessoa
        report.append("\nDETALHES POR PERSONA:")
        report.append("-" * 80)

        for idx, result in enumerate(results["results"], 1):
            persona_id = result["persona_id"]
            status = result["status"]
            message = result.get("message", "N/A")

            report.append(f"Persona {idx} (ID: {persona_id}):")
            report.append(f"  Status: {status.upper()}")
            report.append(f"  Mensagem: {message}")

            if status == "success":
                account_id = result.get("account_id", "N/A")
                report.append(f"  Account ID: {account_id}")

            report.append("")

        report.append("=" * 80)
        report.append("\n instruções de validação:")
        report.append("  1. Checar android-farm database environ source:")
        report.append("     sqlite3 C:/git/android-farm/data/farm.db 'SELECT id, platform, handle, status FROM accounts;'")
        report.append("\n  2. Checar personas no banco principal:")
        report.append("     sqlite3 C:/git/android/data/poc.sqlite3 'SELECT id, name FROM instagram_profiles WHERE username <> '';'")
        report.append("=" * 80)

        return "\n".join(report)


async def main():
    """Ponto de entrada principal."""
    creator = PersonaAccountCreator()

    print("\nStarting account creation process for personas with full accounts (Outlook + Instagram)...")
    print("\nThis script will:")
    print("  1. Query the main database for personas without either account")
    print("  2. For each persona, call the android-farm API to create both Outlook and Instagram accounts")
    print("  3. Generate a final report with success/failure statistics")
    print("\nPrerequisites:")
    print("  - android-farm server must be running on http://localhost:8001")
    print("  - Both databases must exist and be accessible")
    print()

    # Auto-confirm for non-interactive execution
    print("Auto-confirming for non-interactive execution...")

    # Processar todas as personas
    print("Starting creation process...")
    results = await creator.process_all_personas(delay_seconds=10)

    # Gerar relatório
    report = creator.generate_report(results)
    print("\n" + report)

    # Salvar relatório em arquivo
    report_filename = f"accounts_creation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {report_filename}")

    # Exit code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
