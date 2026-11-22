"""VOLT Engine - Quantile Gradient Boosting Forecaster.

Responsibilities:
- Tree-based quantile forecasting using HistGradientBoostingRegressor (scikit-learn).
- Fits separate models for P10, P50 (central), and P90 quantiles.
- Non-crossing quantile post-processing (guarantees P10 <= P50 <= P90).
- Physical non-negativity clipping (ensures energy and price >= 0).
- Deterministic training and inference using pinned random seed.
- Persistence to/from disk with comprehensive model metadata.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import pickle
from typing import Any, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from engine.provenance import Provenance


@dataclass
class QuantileModelMetadata:
    """Metadata for a trained quantile forecasting model."""

    target_name: str
    target_unit: str
    cluster_id: str
    feature_names: list[str]
    quantiles: list[float]
    train_date_range: dict[str, str]
    model_family: str = "HistGradientBoostingRegressor"
    package_versions: dict[str, str] = None
    seed: int = 42
    provenance: str = Provenance.SYNTHETIC.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TreeQuantileForecaster:
    """Multi-quantile tree-based regression model with non-crossing guarantees."""

    def __init__(
        self,
        target_name: str,
        target_unit: str = "MWh",
        cluster_id: str = "all",
        quantiles: Optional[list[float]] = None,
        max_iter: int = 60,
        max_leaf_nodes: int = 31,
        min_samples_leaf: int = 20,
        learning_rate: float = 0.1,
        seed: int = 42,
        non_negative: bool = True,
    ):
        self.target_name = target_name
        self.target_unit = target_unit
        self.cluster_id = cluster_id
        self.quantiles = quantiles or [0.10, 0.50, 0.90]
        self.max_iter = max_iter
        self.max_leaf_nodes = max_leaf_nodes
        self.min_samples_leaf = min_samples_leaf
        self.learning_rate = learning_rate
        self.seed = seed
        self.non_negative = non_negative

        self.models: dict[float, HistGradientBoostingRegressor] = {}
        self.metadata: Optional[QuantileModelMetadata] = None
        self.feature_names: list[str] = []

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        train_start: str = "2021-01-01",
        train_end: str = "2023-12-31",
    ) -> "TreeQuantileForecaster":
        """Train independent quantile regressors for P10, P50, and P90.

        Args:
            X: Training features dataframe.
            y: Target values series.
            train_start: String start date of training period.
            train_end: String end date of training period.

        Returns:
            Fitted forecaster instance.
        """
        self.feature_names = list(X.columns)

        for q in self.quantiles:
            reg = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=q,
                max_iter=self.max_iter,
                max_leaf_nodes=self.max_leaf_nodes,
                min_samples_leaf=self.min_samples_leaf,
                learning_rate=self.learning_rate,
                random_state=self.seed,
            )
            reg.fit(X, y)
            self.models[q] = reg

        import sklearn

        self.metadata = QuantileModelMetadata(
            target_name=self.target_name,
            target_unit=self.target_unit,
            cluster_id=self.cluster_id,
            feature_names=self.feature_names,
            quantiles=self.quantiles,
            train_date_range={"start": train_start, "end": train_end},
            model_family="HistGradientBoostingRegressor",
            package_versions={"scikit-learn": sklearn.__version__, "numpy": np.__version__},
            seed=self.seed,
            provenance=Provenance.SYNTHETIC.value,
        )
        return self

    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Generate point (P50) and quantile (P10, P90) predictions with non-crossing correction.

        Args:
            X: Feature matrix containing the expected feature columns.

        Returns:
            Dictionary with keys 'p10', 'p50', 'p90'.
        """
        if not self.models:
            raise RuntimeError("Model has not been fitted yet")

        preds: dict[float, np.ndarray] = {}
        for q, model in self.models.items():
            preds[q] = model.predict(X[self.feature_names])

        p10 = preds[0.10].copy()
        p50 = preds[0.50].copy()
        p90 = preds[0.90].copy()

        # Non-crossing post-processing guarantee:
        # P10 <= P50 <= P90
        # If quantile crossing occurs due to independent estimation, sort pointwise:
        stacked = np.stack([p10, p50, p90], axis=1)
        stacked.sort(axis=1)

        p10_sorted = stacked[:, 0]
        p50_sorted = stacked[:, 1]
        p90_sorted = stacked[:, 2]

        # Non-negativity clipping for physical quantities
        if self.non_negative:
            p10_sorted = np.clip(p10_sorted, 0.0, None)
            p50_sorted = np.clip(p50_sorted, 0.0, None)
            p90_sorted = np.clip(p90_sorted, 0.0, None)

        # Solar night-time cutoff rule: if target_hour is between 19 and 5, solar is strictly 0
        if "solar" in self.target_name.lower() and "target_hour" in X.columns:
            hours = X["target_hour"].values
            is_night = (hours < 6) | (hours > 18)
            p10_sorted[is_night] = 0.0
            p50_sorted[is_night] = 0.0
            p90_sorted[is_night] = 0.0

        return {"p10": p10_sorted, "p50": p50_sorted, "p90": p90_sorted}

    def save(self, directory: Path) -> Path:
        """Persist model and metadata to directory."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        model_file = directory / f"{self.target_name}_{self.cluster_id}.pkl"
        meta_file = directory / f"{self.target_name}_{self.cluster_id}_meta.json"

        with open(model_file, "wb") as f:
            pickle.dump(
                {
                    "models": self.models,
                    "feature_names": self.feature_names,
                    "target_name": self.target_name,
                    "target_unit": self.target_unit,
                    "cluster_id": self.cluster_id,
                    "quantiles": self.quantiles,
                    "non_negative": self.non_negative,
                },
                f,
            )

        if self.metadata:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata.to_dict(), f, indent=2)

        return model_file

    @classmethod
    def load(cls, model_path: Path) -> "TreeQuantileForecaster":
        """Load fitted forecaster from disk."""
        model_path = Path(model_path)
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        instance = cls(
            target_name=data["target_name"],
            target_unit=data["target_unit"],
            cluster_id=data["cluster_id"],
            quantiles=data["quantiles"],
            non_negative=data["non_negative"],
        )
        instance.models = data["models"]
        instance.feature_names = data["feature_names"]

        meta_path = model_path.parent / f"{instance.target_name}_{instance.cluster_id}_meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)
                instance.metadata = QuantileModelMetadata(**meta_dict)

        return instance
