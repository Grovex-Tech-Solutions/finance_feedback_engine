import pytest

from finance_feedback_engine.decision_engine.policy_actions import (
    POLICY_ACTION_VERSION,
    PolicyAction,
    get_legacy_action_compatibility,
    get_policy_action_family,
    is_policy_action,
    normalize_policy_action,
)


def test_policy_action_version_is_defined():
    assert POLICY_ACTION_VERSION == 1


def test_policy_action_enum_accepts_bounded_actions():
    assert normalize_policy_action("OPEN_SMALL_LONG") == PolicyAction.OPEN_SMALL_LONG
    assert normalize_policy_action("CLOSE_SHORT") == PolicyAction.CLOSE_SHORT
    assert normalize_policy_action("HOLD") == PolicyAction.HOLD


def test_invalid_policy_action_is_rejected():
    assert is_policy_action("BUY") is False
    with pytest.raises(ValueError):
        normalize_policy_action("BUY")


def test_policy_action_family_classification():
    assert get_policy_action_family("OPEN_SMALL_LONG") == "open_long"
    assert get_policy_action_family("ADD_SMALL_SHORT") == "add_short"
    assert get_policy_action_family("REDUCE_LONG") == "reduce_long"
    assert get_policy_action_family("HOLD") == "hold"


def test_legacy_action_compatibility_mapping_is_explicit():
    assert get_legacy_action_compatibility("OPEN_SMALL_LONG") == "BUY"
    assert get_legacy_action_compatibility("OPEN_MEDIUM_SHORT") == "SELL"
    assert get_legacy_action_compatibility("HOLD") == "HOLD"
    assert get_legacy_action_compatibility("REDUCE_LONG") is None
    assert get_legacy_action_compatibility("CLOSE_SHORT") is None
