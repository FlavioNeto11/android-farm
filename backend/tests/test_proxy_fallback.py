"""Tests for layered proxy fallback (Phase 1)"""
import pytest
from unittest.mock import patch, MagicMock
import os

from app.modules.accounts.platforms.instagram.proxy_config import (
    ProxyConfig, ProxyResult, layered_proxy_fallback,
    ProxyAuthenticationError, ProxyConnectionError, _test_proxy_url
)


class TestLayeredFallback:
    
    def test_layered_fallback_tries_native_then_system_then_direct(self):
        """Layer A fails → Layer B fails → Layer C (direct) succeeds"""
        config = ProxyConfig(host="test.proxy.com", port=8080, username="user", password="pass")
        
        call_order = []
        call_num = [0]
        
        def mock_test_proxy_url(proxy_url, test_url="https://geo.brdtest.com/welcome.txt"):
            call_num[0] += 1
            call_idx = call_num[0]
            if proxy_url is not None:
                call_order.append(f"native_{call_idx}")
                raise ProxyConnectionError("Connection failed")
            elif call_idx == 2:
                # Layer B (system_env) also fails
                call_order.append(f"system_env_{call_idx}")
                raise ProxyConnectionError("System env also failed")
            else:
                # Layer C (direct) succeeds
                call_order.append(f"direct_{call_idx}")
                return ProxyResult(method="direct", using_proxy=False, ip="1.2.3.4")
        
        with patch("app.modules.accounts.platforms.instagram.proxy_config._test_proxy_url", side_effect=mock_test_proxy_url):
            result = layered_proxy_fallback(config)
        
        assert len(call_order) == 3  # native, system_env, direct
        assert result.method == "direct"
        assert result.using_proxy is False
        assert result.ip == "1.2.3.4"
    
    def test_only_accepts_layer_with_status_200(self):
        """Layer A succeeds with 200 → returns immediately"""
        config = ProxyConfig(host="test.proxy.com", port=8080, username="user", password="pass")
        
        call_count = 0
        
        def mock_test_proxy_url(proxy_url, test_url="https://geo.brdtest.com/welcome.txt"):
            nonlocal call_count
            call_count += 1
            if proxy_url is not None:
                return ProxyResult(method="native", using_proxy=True, ip="5.6.7.8")
            return ProxyResult(method="direct", using_proxy=False, ip="1.2.3.4")
        
        with patch("app.modules.accounts.platforms.instagram.proxy_config._test_proxy_url", side_effect=mock_test_proxy_url):
            result = layered_proxy_fallback(config)
        
        assert call_count == 1  # Only Layer A was tried
        assert result.method == "native"
        assert result.using_proxy is True
        assert result.ip == "5.6.7.8"
    
    def test_sets_using_proxy_false_on_total_failure(self):
        """All layers fail → returns direct with error"""
        config = ProxyConfig(host="test.proxy.com", port=8080, username="user", password="pass")
        
        def mock_test_proxy_url(proxy_url, test_url="https://geo.brdtest.com/welcome.txt"):
            raise ProxyConnectionError("All connections failed")
        
        with patch("app.modules.accounts.platforms.instagram.proxy_config._test_proxy_url", side_effect=mock_test_proxy_url):
            result = layered_proxy_fallback(config)
        
        assert result.method == "direct"
        assert result.using_proxy is False
        assert result.error != ""
    
    def test_no_config_returns_direct(self):
        """No proxy config → direct mode"""
        result = layered_proxy_fallback(None)
        assert result.method == "direct"
        assert result.using_proxy is False
    
    def test_layer_b_system_env_sets_and_restores_env_vars(self):
        """Layer B sets HTTP_PROXY env vars and restores them"""
        config = ProxyConfig(host="test.proxy.com", port=8080, username="user", password="pass")
        
        old_http = os.environ.get("HTTP_PROXY")
        old_https = os.environ.get("HTTPS_PROXY")
        
        call_order = []
        
        def mock_test_proxy_url(proxy_url, test_url="https://geo.brdtest.com/welcome.txt"):
            if proxy_url is not None:
                call_order.append("native")
                raise ProxyConnectionError("Native failed")
            else:
                call_order.append("system_env")
                return ProxyResult(method="system_env", using_proxy=True, ip="9.10.11.12")
        
        try:
            with patch("app.modules.accounts.platforms.instagram.proxy_config._test_proxy_url", side_effect=mock_test_proxy_url):
                result = layered_proxy_fallback(config)
            
            assert call_order == ["native", "system_env"]
            assert result.method == "system_env"
            assert result.using_proxy is True
        finally:
            # Restore original env vars
            if old_http is not None:
                os.environ["HTTP_PROXY"] = old_http
            else:
                os.environ.pop("HTTP_PROXY", None)
            if old_https is not None:
                os.environ["HTTPS_PROXY"] = old_https
            else:
                os.environ.pop("HTTPS_PROXY", None)
    
    def test_authentication_error_falls_through_to_direct(self):
        """ProxyAuthenticationError should fall through to direct, not stop"""
        config = ProxyConfig(host="test.proxy.com", port=8080, username="user", password="pass")
        
        call_num = [0]
        
        def mock_test_proxy_url(proxy_url, test_url="https://geo.brdtest.com/welcome.txt"):
            call_num[0] += 1
            if proxy_url is not None:
                raise ProxyAuthenticationError("Invalid credentials")
            elif call_num[0] == 2:
                # Layer B also fails
                raise ProxyAuthenticationError("System env also invalid")
            else:
                return ProxyResult(method="direct", using_proxy=False, ip="1.2.3.4")
        
        with patch("app.modules.accounts.platforms.instagram.proxy_config._test_proxy_url", side_effect=mock_test_proxy_url):
            result = layered_proxy_fallback(config)
        
        # Should have fallen through to direct
        assert result.method == "direct"
        assert result.using_proxy is False
        assert result.ip == "1.2.3.4"
