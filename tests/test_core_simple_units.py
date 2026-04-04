"""Simple unit tests for core.py utility methods.

These tests target specific methods without complex mocking to increase
direct core.py coverage.
"""

from unittest.mock import Mock, patch
import pytest


class TestCoreUtilityMethods:
    """Test utility methods in FinanceFeedbackEngine."""

    def test_select_fallback_provider_first_non_local(self):
        """Test _select_fallback_provider chooses first non-local provider."""
        with patch("finance_feedback_engine.core.DecisionEngine"), \
             patch("finance_feedback_engine.core.AlphaVantageProvider"), \
             patch("finance_feedback_engine.core.HistoricalDataProvider"), \
             patch("finance_feedback_engine.data_providers.unified_data_provider.UnifiedDataProvider"), \
             patch("finance_feedback_engine.core.validate_at_startup"), \
             patch("finance_feedback_engine.core.validate_credentials"), \
             patch("finance_feedback_engine.core.validate_and_warn"), \
             patch("finance_feedback_engine.core.ensure_models_installed"):
            
            from finance_feedback_engine.core import FinanceFeedbackEngine
            
            config = {
                "alpha_vantage_api_key": "test",
                "trading_platform": "mock",
                "platform_credentials": {},
                "persistence": {"backend": "sqlite", "db_path": ":memory:"},
                "is_backtest": False,
            }
            
            engine = FinanceFeedbackEngine(config)
            
            # Test with cloud provider available
            fallback = engine._select_fallback_provider(["local", "claude", "openai"])
            assert fallback == "claude"
            
            # Test with only local
            fallback = engine._select_fallback_provider(["local"])
            assert fallback is None
            
            # Test with empty list
            fallback = engine._select_fallback_provider([])
            assert fallback is None

    def test_collect_circuit_breaker_issues_closed_state(self):
        """Test _collect_circuit_breaker_issues with CLOSED circuits."""
        with patch("finance_feedback_engine.core.DecisionEngine"), \
             patch("finance_feedback_engine.core.AlphaVantageProvider"), \
             patch("finance_feedback_engine.core.HistoricalDataProvider"), \
             patch("finance_feedback_engine.data_providers.unified_data_provider.UnifiedDataProvider"), \
             patch("finance_feedback_engine.core.validate_at_startup"), \
             patch("finance_feedback_engine.core.validate_credentials"), \
             patch("finance_feedback_engine.core.validate_and_warn"), \
             patch("finance_feedback_engine.core.ensure_models_installed"):
            
            from finance_feedback_engine.core import FinanceFeedbackEngine
            
            config = {
                "alpha_vantage_api_key": "test",
                "trading_platform": "mock",
                "platform_credentials": {},
                "persistence": {"backend": "sqlite", "db_path": ":memory:"},
                "is_backtest": False,
            }
            
            engine = FinanceFeedbackEngine(config)
            
            # CLOSED circuits should not generate issues
            stats = {
                "healthy_provider": {
                    "state": "CLOSED",
                    "last_failure_time": None,
                    "failure_count": 0,
                }
            }
            
            issues = []
            engine._collect_circuit_breaker_issues("test", stats, issues)
            
            assert len(issues) == 0
