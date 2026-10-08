from cryptography.fernet import Fernet
import os
import logging
from typing import Optional, Tuple
from .redaction import secrets_similarity

logger = logging.getLogger(__name__)


class SecretStore:
    """Gerenciador de segredos criptografados"""

    def __init__(self, key_file: str, storage_path: str):
        self.key_file = key_file
        self.storage_path = storage_path
        self.fernet = None

        # Criar storage se não existir
        os.makedirs(storage_path, exist_ok=True)

        # Carregar ou gerar chave
        self._load_or_create_key()

    def _load_or_create_key(self):
        """Carregar chave existente ou criar nova"""
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read()
                self.fernet = Fernet(key)
                logger.info(f"Secret store loaded key from {self.key_file}")
            except Exception as e:
                logger.error(f"Failed to load secret store key: {e}")
                raise
        else:
            # Criar nova chave
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            self.fernet = Fernet(key)
            logger.info(f"New secret store key created at {self.key_file}")

    def _get_secret_path(self, secret_ref: str) -> str:
        """Obter caminho do arquivo de segredo"""
        return os.path.join(self.storage_path, f"{secret_ref}.b64")

    def encrypt(self, secret: str) -> str:
        """Criptografar segredo e retornar REF"""
        encrypted = self.fernet.encrypt(secret.encode())
        secret_ref = self._generate_secret_ref()
        path = self._get_secret_path(secret_ref)

        with open(path, "wb") as f:
            f.write(encrypted)

        logger.debug(f"Secret encrypted and stored as REF {secret_ref}")
        return secret_ref

    def decrypt(self, secret_ref: str) -> str:
        """Decifrar segredo da REF"""
        path = self._get_secret_path(secret_ref)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Secret file not found for REF {secret_ref}")

        with open(path, "rb") as f:
            encrypted = f.read()

        decrypted = self.fernet.decrypt(encrypted)
        return decrypted.decode()

    def clone(self, secret_ref: str, for_ref: Optional[str] = None, password: Optional[str] = None) -> str:
        """Clonar segredo criptografado"""
        from .redaction import redact

        secret = self.decrypt(secret_ref)
        new_ref = for_ref if for_ref else self._generate_secret_ref()
        new_path = self._get_secret_path(new_ref)

        # Se for senha, podemos preencher uma senha padrão
        if password and "password" in secret.lower():
            secret = password

        encrypted = self.fernet.encrypt(secret.encode())
        with open(new_path, "wb") as f:
            f.write(encrypted)

        logger.debug(f"Secret cloned from {secret_ref} to REF {new_ref} (for: {for_ref})")
        return new_ref

    def _generate_secret_ref(self) -> str:
        """Gerar REF de segredo"""
        import uuid
        return str(uuid.uuid4())[:12]  # usar só 12 chars para praticidade

    def delete(self, secret_ref: str):
        """Deletar segredo do disco"""
        path = self._get_secret_path(secret_ref)

        if os.path.exists(path):
            os.remove(path)
            logger.debug(f"Secret REF {secret_ref} deleted")

    def is_locked(self) -> bool:
        """Verificar se a loja está travada"""
        return self.key_file is None or self.fernet is None

    def verify_key(self, key_file: str) -> bool:
        """Verificar se uma chave corresponde a esta loja"""
        try:
            with open(key_file, "rb") as f:
                stored_key = f.read()
            test_key = self.fernet.encrypt(b"test")
            self.fernet = Fernet(stored_key)
            test_decrypt = self.fernet.decrypt(test_key)
            return test_decrypt.decode() == "test"
        except Exception:
            return False


# Global secret store instance
secret_store = None


def init_secret_store(key_file: str, storage_path: str):
    """Inicializar secret store global"""
    global secret_store
    secret_store = SecretStore(key_file, storage_path)
    logger.info("Secret store initialized")


def get_secret_store() -> SecretStore:
    """Obter secret store global"""
    if secret_store is None:
        raise RuntimeError("Secret store not initialized. Call init_secret_store() first.")
    return secret_store


def verify_same_store(
    key_file: str
) -> Tuple[bool, Optional[str]]:
    """
    Verificar se uma chave corresponde à loja atual.

    Returns:
        Tuple de (success, reference_to_key_if_different)
    """
    global secret_store

    if secret_store is None:
        return False, None

    if secret_store.verify_key(key_file):
        return True, None

    try:
        new_store = SecretStore(key_file, secret_store.storage_path)
        return False, new_store._generate_secret_ref()
    except Exception as e:
        logger.error(f"Failed to verify secret store key: {e}")
        return False, None
