import logging
import re

logger = logging.getLogger(__name__)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?P<name>\b(?:password|passwd|pwd|token|api[_-]?key|secret|authorization)\b)"
    r"(?P<separator>\s*[:=]\s*)(?P<bearer>Bearer\s+)?"
    r'(?P<value>"[^"]*"|\'[^\']*\'|[^\s,;&]+)'
)
_EMAIL_CREDENTIAL = re.compile(
    r"(?i)(?P<email>[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}):(?P<password>[^\s,;&]+)"
)


def _is_redacted(value: str) -> bool:
    return value.strip("\"'").lower() in {"[redacted]", "******"}


def looks_secret(text: str) -> bool:
    """Detectar se texto parece conter segredos"""
    if not text or not isinstance(text, str):
        return False

    assignments = _SECRET_ASSIGNMENT.finditer(text)
    credentials = _EMAIL_CREDENTIAL.finditer(text)
    return any(not _is_redacted(match.group("value")) for match in assignments) or any(
        not _is_redacted(match.group("password")) for match in credentials
    )


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

    def redact_assignment(match: re.Match) -> str:
        value = "******" if match.group("bearer") else "[REDACTED]"
        return f"{match.group('name')}{match.group('separator')}{value}"

    text = _SECRET_ASSIGNMENT.sub(redact_assignment, text)
    return _EMAIL_CREDENTIAL.sub(r"\g<email>:[REDACTED]", text)


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
