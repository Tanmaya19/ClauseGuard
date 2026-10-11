"""Clause-type classification (REQ-3.1 to REQ-3.4)."""

from app.services.classification.labels import (
    BY_KEY,
    CLAUSE_TYPES,
    LABEL_KEYS,
    NUM_LABELS,
    UNCATEGORIZED,
    ClauseType,
    display_name,
    thin_classes,
)
from app.services.classification.model import (
    BaselineClassifier,
    Classifier,
    Prediction,
    TransformerClassifier,
    get_classifier,
)

__all__ = [
    "BY_KEY",
    "CLAUSE_TYPES",
    "LABEL_KEYS",
    "NUM_LABELS",
    "UNCATEGORIZED",
    "BaselineClassifier",
    "ClauseType",
    "Classifier",
    "Prediction",
    "TransformerClassifier",
    "display_name",
    "get_classifier",
    "thin_classes",
]
