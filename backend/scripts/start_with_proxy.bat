@echo off
echo Configurando proxy do sistema...

set PROXY_USER=brd-customer-hl_569e5ea3-zone-isp_proxy1
set PROXY_PASS=pmj92phck9qu
set PROXY_HOST=brd.superproxy.io
set PROXY_PORT=44445

set HTTP_PROXY=http://%PROXY_USER%:%PROXY_PASS%@%PROXY_HOST%:%PROXY_PORT%
set HTTPS_PROXY=%HTTP_PROXY%

echo Proxy configurado: %PROXY_HOST%:%PROXY_PORT%
echo Iniciando servidor...

cd ..
python -m uvicorn app.main:app --reload

pause
