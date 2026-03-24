from finance_feedback_engine.data_providers.coinbase_data import CoinbaseDataProvider


def test_normalize_asset_pair_preserves_coinbase_cfm_product_id():
    provider = CoinbaseDataProvider()

    result = provider._normalize_asset_pair("ETP-20DEC30-CDE")

    assert result == "ETP-20DEC30-CDE"


def test_normalize_asset_pair_preserves_coinbase_cfm_product_id_without_case_sensitivity():
    provider = CoinbaseDataProvider()

    result = provider._normalize_asset_pair("bip-20dec30-cde")

    assert result == "BIP-20DEC30-CDE"
