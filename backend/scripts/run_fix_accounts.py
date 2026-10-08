"""Execute the Instagram account fix script"""
import sys
import os
import asyncio

# Adicionar backend ao path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    from scripts.fix_invalid_accounts import fix_invalid_accounts
    asyncio.run(fix_invalid_accounts())
