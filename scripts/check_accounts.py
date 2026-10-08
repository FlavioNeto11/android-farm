import requests

handles = ['beatriz.rocha902', 'thiago.moreira800', 'camila.duarte772', 'rafael.pires866', 'larissa.fontes557']

for h in handles:
    try:
        r = requests.get(f'https://www.instagram.com/{h}/', timeout=10)
        print(f'{h}: {r.status_code}')
    except Exception as e:
        print(f'{h}: Error - {e}')
