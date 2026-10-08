"""Generate secret key for secret store"""
import sys
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(key.decode())

sys.exit(0)
