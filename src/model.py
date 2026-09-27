"""
Entity Resolution Model Training & Cross-Validation Module.
Provides model tournament comparison across Random Forest, XGBoost, and LightGBM.
"""

from .models import EntityResolutionModelTrainer

__all__ = ["EntityResolutionModelTrainer"]
