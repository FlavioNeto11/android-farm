## Android Farm - Account Factory

Fábrica de contas para Outlook, Instagram e futuras plataformas através de automação de browser Playwright.

## Configuração

1. Criar ambiente virtual
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. Instalar dependências
```bash
pip install -r backend/requirements.txt
```

3. Configurar `.env` baseando-se em `config/config.example.yaml`

4. Gerar chaves de criptografia (se não existirem)
```bash
python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key(); open('./data/secret.key', 'wb').write(key)"
```

5. Iniciar a aplicação
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health
- `GET /api/health` - Health check

### Accounts
- `POST /api/accounts/request` - Solicitar criação de conta
- `GET /api/accounts/{id}` - Obter status da conta
- `GET /api/accounts` - Listar contas
- `POST /api/accounts/{id}/assign` - Atribuir conta a persona
- `DELETE /api/accounts/{id}` - Deletar conta (soft delete)

### Credentials
- `GET /api/accounts/{id}/credential` - Obter metadados da credencial
- `POST /api/accounts/{id}/credential/consent` - Marcar consentimento
- `POST /api/accounts/{id}/credential/clone` - Clonar credencial

### Proxies
- `GET /api/proxies` - Listar proxies

## Principais Funcionalidades

### Criação de Contas Autônoma
- Automação via Playwright simulando signup real
- Suporte a Outlook e Instagram
- Rotação de proxies incluída
- Anti-detecção (fingerprint randomization, delays realistas)

### Gerenciamento de Segurança
- Armazenamento criptografado de credenciais
- Redação de segredos em logs
- Checkout e vote de consentimento

### Escalabilidade
- Design baseado em plugins para novas plataformas
- Proxy pool configurável
- Concorrência controlada

## Integração com Projeto Principal

O projeto principal (`c:\git\android`) pode integrar-se através do endpoint de criação de contas e consumo via API.

## Documentação

Para documentação detalhada de design, ver `.kilo/plans/1791398818153-android-farm-account-factory.md`

## Desenvolvimento

Para rodar testes:
```bash
cd backend
pytest tests/
```

Para conferir contratos API:
```bash
cd tests/test_contracts
python test_api.py
```
