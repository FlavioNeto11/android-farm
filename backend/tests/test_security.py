import pytest

from app.security.redaction import looks_secret, redact
from app.security.secret_store import SecretStore


def test_secret_store_encrypts_and_decrypts_secrets(tmp_path):
    store = SecretStore(str(tmp_path / "secret.key"), str(tmp_path / "secrets"))

    secret_ref = store.encrypt("synthetic-password")
    stored_value = (tmp_path / "secrets" / f"{secret_ref}.b64").read_bytes()

    assert b"synthetic-password" not in stored_value
    assert store.decrypt(secret_ref) == "synthetic-password"


def test_secret_store_delete_removes_secret(tmp_path):
    store = SecretStore(str(tmp_path / "secret.key"), str(tmp_path / "secrets"))
    secret_ref = store.encrypt("synthetic-password")

    store.delete(secret_ref)

    with pytest.raises(FileNotFoundError):
        store.decrypt(secret_ref)


@pytest.mark.parametrize(
    "text",
    [
        "api_key: abc123",
        "Authorization: ******",
        "person@example.test:synthetic-password",
    ],
)
def test_redact_removes_secret_values(text):
    redacted = redact(text)

    assert "abc123" not in redacted
    assert "synthetic-password" not in redacted
    assert "[REDACTED]" in redacted or "******" in redacted
    assert not looks_secret(redacted)


def test_redact_preserves_non_secret_text():
    text = "Application started successfully"

    assert redact(text) == text
    assert not looks_secret(text)


def test_looks_secret_detects_common_secret_formats():
    assert looks_secret("token=synthetic-token")
    assert looks_secret("user@example.test:synthetic-password")
    assert not looks_secret("ordinary application message")
