"""
ThompsonIntegrator service for Portfolio Memory.

Responsibilities:
- Integrate with Thompson sampling for adaptive learning
- Update provider performance weights based on outcomes
- Track regime-specific performance
- Provide provider recommendations
- Trigger Thompson sampling optimizer callbacks
"""

import logging
from collections import defaultdict
from math import sqrt
from typing import Callable, Dict, List, Optional

from .interfaces import IThompsonIntegrator

# Import from existing module during migration
from .portfolio_memory import TradeOutcome

logger = logging.getLogger(__name__)


class ThompsonIntegrator(IThompsonIntegrator):
    """
    Integrates Portfolio Memory with Thompson sampling.

    Features:
    - Provider performance tracking
    - Regime-specific performance tracking
    - Callback mechanism for external Thompson optimizer
    - Provider weight recommendations
    """

    def __init__(
        self,
        min_samples_for_adjustment: int = 10,
        confidence_z_score: float = 1.96,
    ):
        """Initialize ThompsonIntegrator."""
        self.callbacks: List[Callable] = []
        self.min_samples_for_adjustment = int(min_samples_for_adjustment)
        self.confidence_z_score = float(confidence_z_score)

        # Provider performance tracking
        self.provider_wins: Dict[str, int] = defaultdict(int)
        self.provider_losses: Dict[str, int] = defaultdict(int)

        # Regime performance tracking
        self.regime_wins: Dict[str, int] = defaultdict(int)
        self.regime_losses: Dict[str, int] = defaultdict(int)

        logger.debug("ThompsonIntegrator initialized")

    @staticmethod
    def _wilson_lower_bound(wins: int, total: int, z: float) -> float:
        """Compute Wilson score lower bound for a binomial proportion."""
        if total <= 0:
            return 0.0

        p_hat = wins / total
        z2 = z * z
        denom = 1.0 + (z2 / total)
        center = p_hat + (z2 / (2.0 * total))
        margin = z * sqrt((p_hat * (1.0 - p_hat) + (z2 / (4.0 * total))) / total)
        return max(0.0, (center - margin) / denom)

    def register_callback(self, callback: Callable) -> None:
        """
        Register Thompson sampling update callback.

        Args:
            callback: Function(provider, won, regime) -> None
        """
        if not callable(callback):
            raise TypeError(f"Callback must be callable, got {type(callback)}")

        self.callbacks.append(callback)
        callback_name = getattr(callback, "__name__", repr(callback))
        logger.debug(f"Registered Thompson callback: {callback_name}")

    def update_on_outcome(self, outcome: TradeOutcome) -> None:
        """
        Update Thompson sampling based on trade outcome.

        Args:
            outcome: TradeOutcome instance
        """
        if not isinstance(outcome, TradeOutcome):
            raise TypeError(f"Expected TradeOutcome, got {type(outcome)}")

        # Only update if we have completed trade data
        if outcome.realized_pnl is None:
            logger.debug(
                f"Skipping Thompson update for incomplete trade {outcome.decision_id}"
            )
            return

        provider = outcome.ai_provider
        regime = outcome.market_sentiment
        won = outcome.was_profitable

        # Update provider performance
        if provider:
            self.update_provider_performance(provider, won)

        # Update regime performance
        if regime:
            self.update_regime_performance(regime, won)

        # Trigger callbacks
        if provider and regime:
            self._trigger_callbacks(provider, won, regime)

        logger.info(
            f"Thompson update: provider={provider}, won={won}, regime={regime}"
        )

    def update_provider_performance(self, provider: str, won: bool) -> None:
        """
        Explicitly update provider performance.

        Args:
            provider: Provider name
            won: Whether the trade was profitable
        """
        if not provider:
            raise ValueError("Provider name cannot be empty")

        if won:
            self.provider_wins[provider] += 1
        else:
            self.provider_losses[provider] += 1

        logger.debug(
            f"Provider {provider}: {self.provider_wins[provider]} wins, "
            f"{self.provider_losses[provider]} losses"
        )

    def update_regime_performance(self, regime: str, won: bool) -> None:
        """
        Update performance for a market regime.

        Args:
            regime: Regime identifier
            won: Whether the trade was profitable
        """
        if not regime:
            raise ValueError("Regime name cannot be empty")

        if won:
            self.regime_wins[regime] += 1
        else:
            self.regime_losses[regime] += 1

        logger.debug(
            f"Regime {regime}: {self.regime_wins[regime]} wins, "
            f"{self.regime_losses[regime]} losses"
        )

    def get_provider_recommendations(self) -> Dict[str, float]:
        """
        Get provider weight recommendations.

        Uses simple win rate for recommendations. In production,
        this would integrate with actual Thompson sampling optimizer.

        Returns:
            Dict mapping provider -> recommended weight
        """
        recommendations = {}

        # Get all providers
        all_providers = set(self.provider_wins.keys()) | set(
            self.provider_losses.keys()
        )

        if not all_providers:
            return {}

        # Calculate statistically conservative scores (Wilson lower bounds).
        # Providers below minimum sample size are held at a neutral baseline.
        scores: Dict[str, float] = {}
        reliable_provider_count = 0
        for provider in all_providers:
            wins = self.provider_wins[provider]
            losses = self.provider_losses[provider]
            total = wins + losses

            if total >= self.min_samples_for_adjustment:
                scores[provider] = self._wilson_lower_bound(
                    wins=wins,
                    total=total,
                    z=self.confidence_z_score,
                )
                reliable_provider_count += 1
            else:
                scores[provider] = 0.5

        # If none have enough data, keep neutral equal weights.
        if reliable_provider_count == 0:
            equal_weight = 1.0 / len(all_providers)
            return {provider: equal_weight for provider in all_providers}

        # Normalize to weights.
        total_score = sum(scores.values())

        if total_score > 0:
            for provider, score in scores.items():
                recommendations[provider] = score / total_score
        else:
            # Equal weights if scores are degenerate.
            equal_weight = 1.0 / len(all_providers)
            for provider in all_providers:
                recommendations[provider] = equal_weight

        return recommendations

    def get_provider_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get detailed provider statistics.

        Returns:
            Dict mapping provider -> {wins, losses, total}
        """
        all_providers = set(self.provider_wins.keys()) | set(
            self.provider_losses.keys()
        )

        stats = {}
        for provider in all_providers:
            wins = self.provider_wins[provider]
            losses = self.provider_losses[provider]
            stats[provider] = {
                "wins": wins,
                "losses": losses,
                "total": wins + losses,
                "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0.0,
            }

        return stats

    def get_regime_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get detailed regime statistics.

        Returns:
            Dict mapping regime -> {wins, losses, total}
        """
        all_regimes = set(self.regime_wins.keys()) | set(self.regime_losses.keys())

        stats = {}
        for regime in all_regimes:
            wins = self.regime_wins[regime]
            losses = self.regime_losses[regime]
            stats[regime] = {
                "wins": wins,
                "losses": losses,
                "total": wins + losses,
                "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0.0,
            }

        return stats

    def clear(self) -> None:
        """Clear all tracking data."""
        self.provider_wins.clear()
        self.provider_losses.clear()
        self.regime_wins.clear()
        self.regime_losses.clear()
        logger.debug("ThompsonIntegrator cleared")

    def _trigger_callbacks(self, provider: str, won: bool, regime: str) -> None:
        """
        Trigger all registered callbacks.

        Args:
            provider: Provider name
            won: Whether trade was profitable
            regime: Market regime
        """
        for callback in self.callbacks:
            try:
                callback(provider, won, regime)
            except Exception as e:
                logger.error(
                    f"Thompson callback {getattr(callback, '__name__', repr(callback))} failed: {e}",
                    exc_info=True,
                )

__all__ = ["ThompsonIntegrator"]
