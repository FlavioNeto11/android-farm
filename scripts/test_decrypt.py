import sys
sys.path.insert(0, 'C:/git/android-farm/backend')

from app.security.secret_store import init_secret_store, get_secret_store

init_secret_store(
    key_file="./data/secret.key",
    storage_path="./data/secrets/"
)

secret_store = get_secret_store()

# Test decrypt
secret_refs = ["9173e500-185", "ec3c1242-0a6"]

for ref in secret_refs:
    try:
        decrypted = secret_store.decrypt(ref)
        print(f"Secret {ref}: {decrypted}")
    except Exception as e:
        print(f"Error decrypting {ref}: {e}")
