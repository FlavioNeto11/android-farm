# Integração com Plataforma de Criação de Contas

## Fluxo de Dados

1. **Plataforma de Criação** (automação IA):
   - Cria conta Instagram/Outlook
   - Usa Bright Data ISP com session_id único
   - Salva: email, senha, session_id, proxy_credentials

2. **Export para android-farm:**
   - POST /api/proxy-accounts/import
   - Mantém MESMO session_id para consistência de IP

3. **android-farm:**
   - Recebe conta + session_id
   - Usa MESMO proxy (session sticky)
   - Ativa em emulador Android
   - Conta opera sempre do mesmo IP

## Por que IP Consistente?

- Criação no IP A, uso no IP B = "Suspicious Activity" (ban)
- Criação no IP A, uso no IP A = comportamento normal

## Configuração

### 1. Proxy Pool (android-farm)

Edite `config/proxy_pool.json` com MESMAS credenciais da plataforma de criação:

```json
{
  "provider": "brightdata_isp",
  "base_credentials": {
    "host": "brd.superproxy.io",
    "port": 44445,
    "username": "brd-customer-hl_569e5ea3-zone-isp_proxy1",
    "password": "pmj92phck9qu"
  }
}
```

### 2. Endpoint de Import

A plataforma de criação deve chamar:

```bash
curl -X POST http://android-farm:8001/api/proxy-accounts/import \
  -H "Content-Type: application/json" \
  -d '{
    "email": "maria.silva123@gmail.com",
    "platform": "instagram",
    "proxy_session_id": "maria_session_001",
    "proxy_host": "brd.superproxy.io",
    "proxy_port": 44445,
    "proxy_user": "brd-customer-hl_569e5ea3-zone-isp_proxy1",
    "proxy_pass": "pmj92phck9qu"
  }'
```

### 3. Validação

Verifique se IP é consistente:
```bash
# Na plataforma de criação
curl --proxy brd.superproxy.io:44445 \
     --proxy-user brd-customer-hl_569e5ea3-zone-isp_proxy1-session-maria_session_001:pmj92phck9qu \
     https://geo.brdtest.com/welcome.txt
# → IP: 85.122.84.176

# No android-farm (mesmo session)
curl --proxy brd.superproxy.io:44445 \
     --proxy-user brd-customer-hl_569e5ea3-zone-isp_proxy1-session-maria_session_001:pmj92phck9qu \
     https://geo.brdtest.com/welcome.txt
# → Deve ser MESMO IP: 85.122.84.176
```

## Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/proxy-accounts/import` | Importar conta da plataforma de criação |
| GET | `/api/proxy-accounts/proxy-mappings` | Listar todos os mapeamentos |
| GET | `/api/proxy-accounts/proxy-mappings/{id}` | Obter mapeamento específico |

## Escalabilidade

Para 100 contas:
- Bright Data ISP: $200/mês (100 IPs dedicados)
- Proxy-Seller: $300-500/mês (alternativa mais barata)
- 4G DIY: $200/mês (Raspberry Pi + chips)

Recomendação: Comece com Bright Data ISP para validar, depois migre para Proxy-Seller em escala.
