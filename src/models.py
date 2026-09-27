import os, joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
import xgboost as xgb
import lightgbm as lgb

class EntityResolutionModelTrainer:
    """Handles multi-algorithm training, cross-validation, and model selection."""
    
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {
            "Random Forest": RandomForestClassifier(n_estimators=200, random_state=random_state),
            "XGBoost": xgb.XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.08, random_state=random_state, eval_metric="logloss"),
            "LightGBM": lgb.LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.08, random_state=random_state, verbose=-1)
        }
        self.best_model_name = None
        self.champion_model = None

    def benchmark_cross_validation(self, X, y, n_splits=5):
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)
        results = {}
        for name, clf in self.models.items():
            scores = cross_val_score(clf, X, y, cv=cv, scoring='accuracy')
            results[name] = (scores.mean(), scores.std())
        
        self.best_model_name = max(results, key=lambda k: results[k][0])
        return results, self.best_model_name

    def fit_champion(self, X, y):
        if not self.best_model_name:
            self.best_model_name = "LightGBM"
        self.champion_model = self.models[self.best_model_name]
        self.champion_model.fit(X, y)
        return self.champion_model

    def save(self, filepath="models/entity_resolution_champion.pkl"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.champion_model, filepath)
