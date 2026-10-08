"""Teste rápido de criação de conta"""
import asyncio
import aiohttp
import json

async def test():
    persona_id = "persona-jK7q7X9O-Y3PGRMk"
    payload = {
        "profile_id": persona_id,
        "platforms": ["outlook", "instagram"],
        "persona_data": {
            "display_name": "Marcos Vinicius Leal",
            "first_name": "Marcos",
            "last_name": "Leal",
            "email": "marcos.leal@example.invalid",
            "birth_date": "1990-01-01",
            "gender": "male",
            "locale": "pt_BR"
        }
    }
    
    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print(f"Creating accounts for {persona_id}...")
        async with session.post("http://localhost:8001/api/accounts/request", json=payload) as resp:
            print(f"Status: {resp.status}")
            content = await resp.text()
            print(content)

asyncio.run(test())
