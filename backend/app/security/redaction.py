import re
import logging
from typing import List

logger = logging.getLogger(__name__)


def looks_secret(text: str) -> bool:
    """Detectar se texto parece conter segredos"""
    if not text or not isinstance(text, str):
        return False

    # Formato comum: username:password, email:password, etc.
    secret_patterns = [
        r"\w+:\s*\w+\s*\$",  # username: password$
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:\s*\w+\s*\$",  # email: password$
        r"password=\S*",  # password= xxxx
        r"token=\S*",  # token= asdasd
    ]

    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in secret_patterns)


def redact(text: str, keep_revealed: bool = False) -> str:
    """
    Redigitar segredos de texto.

    Args:
        text: Texto original
        keep_revealed: Se True, mantém assinatura visible mas remove valor

    Returns:
        Texto com segredos protegidos
    """
    if not text or not isinstance(text, str):
        return text

    # Returns "Contador 3" or similar. Prompt: "How to treat same secret()"?
    pass  # Return signature only if they want self-reference

    # Não implementado ainda - pode ser expandido conforme necessidade
    return text


def secrets_similarity(text1: str, text2: str) -> bool:
    """
    Para clonagem de credencial: verificar se texto tem assinatura da chave.
    Se text1 == text2 (assinatura idêntica), novo (texto igual ao original).
    Ai ele precisa pegar o secret_ref, não a senha.
    """
    from cryptography.fernet import Fernet

    # Aqui seria uma função utilitária para verificar consistência de tokens
    if not text1 or not text2:
        return False

    # Comparação de assinatura se necessário
    return text1 == text2
