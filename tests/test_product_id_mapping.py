"""
Tests for canonical Coinbase product ID ↔ asset pair mapping.

Track E: Centralize the product ID mapping that's currently duplicated
across 8+ files with slightly different prefix tuples and logic.

The canonical module should be the SINGLE source of truth for:
- product_id → asset_pair (e.g., "BIP-20DEC30-CDE" → "BTCUSD")
- asset_pair → product_id (e.g., "BTCUSD" → "BIP-20DEC30-CDE")
- prefix detection (is this a CFM product?)
- stripping product IDs from mixed asset lists
"""

import pytest


class TestProductIdToAssetPair:
    """Map Coinbase futures product IDs to canonical asset pairs."""

    def test_btc_perpetual(self):
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("BIP-20DEC30-CDE") == "BTCUSD"

    def test_eth_perpetual(self):
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("ETP-20DEC30-CDE") == "ETHUSD"

    def test_case_insensitive(self):
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("bip-20dec30-cde") == "BTCUSD"
        assert product_id_to_asset_pair("Etp-20Dec30-CDE") == "ETHUSD"

    def test_stripped_product_id(self):
        """Handles product IDs without dashes (as seen in log asset_scoped_pairs)."""
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("BIP20DEC30CDE") == "BTCUSD"
        assert product_id_to_asset_pair("ETP20DEC30CDE") == "ETHUSD"

    def test_already_canonical(self):
        """If given a canonical pair, return it unchanged."""
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("BTCUSD") == "BTCUSD"
        assert product_id_to_asset_pair("ETHUSD") == "ETHUSD"

    def test_unknown_returns_none(self):
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("UNKNOWN-PRODUCT") is None

    def test_none_input(self):
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair(None) is None
        assert product_id_to_asset_pair("") is None

    def test_prefix_only(self):
        """Bare prefixes like 'BIP' or 'ETP' should still resolve."""
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("BIP") == "BTCUSD"
        assert product_id_to_asset_pair("ETP") == "ETHUSD"

    def test_bit_prefix_maps_to_btc(self):
        """BIT- is an alternate BTC prefix seen in some contexts."""
        from finance_feedback_engine.utils.product_id import product_id_to_asset_pair
        assert product_id_to_asset_pair("BIT-SOMETHING") == "BTCUSD"


class TestAssetPairToProductId:
    """Map canonical asset pairs to Coinbase futures product IDs."""

    def test_btc_to_product(self):
        from finance_feedback_engine.utils.product_id import asset_pair_to_product_id
        assert asset_pair_to_product_id("BTCUSD") == "BIP-20DEC30-CDE"

    def test_eth_to_product(self):
        from finance_feedback_engine.utils.product_id import asset_pair_to_product_id
        assert asset_pair_to_product_id("ETHUSD") == "ETP-20DEC30-CDE"

    def test_unknown_returns_none(self):
        from finance_feedback_engine.utils.product_id import asset_pair_to_product_id
        assert asset_pair_to_product_id("DOGEUSD") is None

    def test_case_insensitive(self):
        from finance_feedback_engine.utils.product_id import asset_pair_to_product_id
        assert asset_pair_to_product_id("btcusd") == "BIP-20DEC30-CDE"


class TestIsCfmProduct:
    """Detect whether a string is a Coinbase CFM product ID."""

    def test_cfm_products(self):
        from finance_feedback_engine.utils.product_id import is_cfm_product
        assert is_cfm_product("BIP-20DEC30-CDE") is True
        assert is_cfm_product("ETP-20DEC30-CDE") is True
        assert is_cfm_product("BIP20DEC30CDE") is True

    def test_canonical_pairs_are_not_cfm(self):
        from finance_feedback_engine.utils.product_id import is_cfm_product
        assert is_cfm_product("BTCUSD") is False
        assert is_cfm_product("ETHUSD") is False

    def test_empty_and_none(self):
        from finance_feedback_engine.utils.product_id import is_cfm_product
        assert is_cfm_product(None) is False
        assert is_cfm_product("") is False


class TestNormalizeAssetList:
    """Clean mixed lists of product IDs and asset pairs into canonical pairs only."""

    def test_mixed_list(self):
        from finance_feedback_engine.utils.product_id import normalize_asset_list
        mixed = ["BIP20DEC30CDE", "BTCUSD", "ETHUSD", "ETP20DEC30CDE"]
        result = normalize_asset_list(mixed)
        assert result == {"BTCUSD", "ETHUSD"}

    def test_pure_canonical(self):
        from finance_feedback_engine.utils.product_id import normalize_asset_list
        result = normalize_asset_list(["BTCUSD", "ETHUSD"])
        assert result == {"BTCUSD", "ETHUSD"}

    def test_pure_product_ids(self):
        from finance_feedback_engine.utils.product_id import normalize_asset_list
        result = normalize_asset_list(["BIP-20DEC30-CDE", "ETP-20DEC30-CDE"])
        assert result == {"BTCUSD", "ETHUSD"}

    def test_empty(self):
        from finance_feedback_engine.utils.product_id import normalize_asset_list
        assert normalize_asset_list([]) == set()


class TestCfmPrefixMap:
    """Verify the prefix map covers all known Coinbase CFM prefixes."""

    def test_known_prefixes(self):
        from finance_feedback_engine.utils.product_id import CFM_PREFIX_TO_BASE
        # These are the prefixes scattered across the codebase
        assert "BIP" in CFM_PREFIX_TO_BASE
        assert "BIT" in CFM_PREFIX_TO_BASE
        assert "ETP" in CFM_PREFIX_TO_BASE
        assert "ET" in CFM_PREFIX_TO_BASE
        assert "SLP" in CFM_PREFIX_TO_BASE
        assert "SOL" in CFM_PREFIX_TO_BASE

    def test_prefix_values_are_base_currencies(self):
        from finance_feedback_engine.utils.product_id import CFM_PREFIX_TO_BASE
        assert CFM_PREFIX_TO_BASE["BIP"] == "BTC"
        assert CFM_PREFIX_TO_BASE["ETP"] == "ETH"
