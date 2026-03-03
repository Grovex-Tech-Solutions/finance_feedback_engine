import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def normalize_decision_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize decision_engine config to handle both nested and flat structures.

    Supports two config formats for backward compatibility:
    1. Nested: config['decision_engine']['ai_provider'] (preferred)
    2. Flat: config['ai_provider'] (legacy fallback for backward compatibility)

    This helper ensures consistent config access across the codebase, eliminating
    duplicate normalization patterns like:
        - config.get("decision_engine", {}).get("key")
        - config.get("decision_engine", config).get("key")

    Args:
        config: Full configuration dictionary or decision_engine sub-dict

    Returns:
        Normalized decision_engine configuration dict. Returns empty dict if neither
        structure is found.

    Example:
        >>> config1 = {"decision_engine": {"ai_provider": "ensemble"}}
        >>> config2 = {"ai_provider": "local"}
        >>> normalize_decision_config(config1).get("ai_provider")
        'ensemble'
        >>> normalize_decision_config(config2).get("ai_provider")
        'local'
    """
    # If config has decision_engine key, use it; otherwise treat config as decision_engine dict
    if "decision_engine" in config:
        return config.get("decision_engine", {})
    else:
        # Legacy: config itself is the decision_engine config
        return config


    _load_dotenv_file()
    # Convert escaped newline sequences in the Coinbase secret to real newlines
    secret = os.getenv('COINBASE_API_SECRET')
    if secret and \n in secret:
        os.environ['COINBASE_API_SECRET'] = secret.replace('\n', '\n')
        logger.info('INFO: Converted escaped newlines in COINBASE_API_SECRET')
    logger.debug('COINBASE_API_SECRET = %s', repr(os.getenv('COINBASE_API_SECRET')))
    logger.debug('OANDA_API_KEY = %s', repr(os.getenv('OANDA_API_KEY')))
