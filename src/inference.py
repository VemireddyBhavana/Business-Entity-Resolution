"""
Entity Resolution Real-Time & Batch Inference Module.
Performs pairwise comparison and scoring for candidate business entity pairs.
"""

import os
import joblib
from .cleaning import clean_business_name, clean_business_address, extract_city_state
from .features import extract_feature_vector, feature_names

class EntityInference:
    """Production inference engine for business entity resolution."""
    
    def __init__(self, model_path="models/entity_resolution_model.pkl"):
        if not os.path.exists(model_path):
            alt_path = "models/entity_resolution_champion.pkl"
            if os.path.exists(alt_path):
                model_path = alt_path
            else:
                raise FileNotFoundError(f"Model file not found at {model_path} or {alt_path}")
                
        self.model = joblib.load(model_path)
        self.feature_names = feature_names

    def format_entity(self, name, address, country="US", city=None, state=None):
        """Cleans and structures raw entity fields for inference."""
        clean_name = clean_business_name(name)
        clean_addr = clean_business_address(address)
        ext_city, ext_state = extract_city_state(address)
        
        return {
            "raw_name": name,
            "raw_address": address,
            "clean_business_name": clean_name,
            "clean_business_address": clean_addr,
            "country": country.upper().strip() if country else "US",
            "city": city.strip() if city else ext_city,
            "state": state.strip() if state else ext_state
        }

    def predict_pair(self, entity_a, entity_b, threshold=0.5):
        """Calculates features and returns prediction, probability, and key signal metrics."""
        feat_vec = extract_feature_vector(entity_a, entity_b)
        
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba([feat_vec])[0]
            prob = float(probs[1])
            is_match = bool(prob >= threshold)
        else:
            pred = self.model.predict([feat_vec])[0]
            is_match = bool(pred == 1)
            prob = 1.0 if is_match else 0.0

        return {
            "is_match": is_match,
            "match_probability": prob,
            "confidence": f"{prob * 100:.2f}%",
            "decision": "MATCH" if is_match else "NO MATCH",
            "feature_vector": feat_vec,
            "feature_breakdown": dict(zip(self.feature_names, feat_vec))
        }
