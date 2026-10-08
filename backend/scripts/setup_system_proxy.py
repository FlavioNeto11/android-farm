#!/usr/bin/env python3
"""
Configura proxy no nível do sistema para todo o processo Python.
Resolve problema de HTTPS tunneling no Playwright com Bright Data ISP.
"""

import os
import sys
import urllib.parse


def setup_brightdata_system_proxy():
    """Define variáveis de ambiente HTTP_PROXY e HTTPS_PROXY"""
    
    username = os.getenv("PROXY_USER", "brd-customer-hl_569e5ea3-zone-isp_proxy1")
    password = os.getenv("PROXY_PASS", "pmj92phck9qu")
    host = os.getenv("PROXY_HOST", "brd.superproxy.io")
    port = os.getenv("PROXY_PORT", "44445")
    
    safe_user = urllib.parse.quote(username, safe="")
    safe_pass = urllib.parse.quote(password, safe="")
    proxy_url = f"http://{safe_user}:{safe_pass}@{host}:{port}"
    
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url
    
    masked = f"http://{username}:****@{host}:{port}"
    print(f"System proxy configured:")
    print(f"   HTTP_PROXY={masked}")
    print(f"   HTTPS_PROXY={masked}")
    
    return True


if __name__ == "__main__":
    setup_brightdata_system_proxy()
    print("\nProxy configured. Starting server...")
