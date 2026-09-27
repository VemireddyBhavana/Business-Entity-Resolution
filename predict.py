"""
Enterprise Business Entity Resolution - Inference Engine
Predicts whether two business records refer to the same real-world entity.

Usage:
  1. CLI arguments:
     python predict.py --name1 "Zephay Labs Inc" --addr1 "100 Main St, Austin, TX" --country1 "US" \
                       --name2 "Zephay Laboratories" --addr2 "100 Main Street, Austin, TX" --country2 "US"
  
  2. Interactive Mode:
     python predict.py

  3. Python API:
     from predict import EntityMatcher
     matcher = EntityMatcher()
     res = matcher.predict(business_a, business_b)
"""

import os
import sys
import argparse
import joblib
import pandas as pd
from src.cleaning import clean_business_name, clean_business_address, extract_city_state
from src.features import extract_feature_vector, feature_names

class EntityMatcher:
    def __init__(self, model_path="models/entity_resolution_champion.pkl"):
        if not os.path.exists(model_path):
            alt_path = "models/entity_resolution_model.pkl"
            if os.path.exists(alt_path):
                model_path = alt_path
            else:
                raise FileNotFoundError(f"Model file not found at {model_path} or {alt_path}")
        
        self.model = joblib.load(model_path)
        self.feature_names = feature_names

    def format_entity(self, name, address, country="US", city=None, state=None):
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

    def predict(self, ent1, ent2, threshold=0.5):
        features = extract_feature_vector(ent1, ent2)
        
        # Predict probability if supported
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba([features])[0]
            match_prob = float(probs[1])
            is_match = bool(match_prob >= threshold)
        else:
            pred = self.model.predict([features])[0]
            is_match = bool(pred == 1)
            match_prob = 1.0 if is_match else 0.0

        feature_dict = dict(zip(self.feature_names, features))

        return {
            "is_match": is_match,
            "match_probability": match_prob,
            "confidence": f"{match_prob * 100:.2f}%",
            "decision": "MATCH (Same Entity)" if is_match else "NO MATCH (Different Entities)",
            "features": feature_dict
        }

def run_interactive(matcher):
    print("=" * 65)
    print(" 🏢 ENTERPRISE BUSINESS ENTITY RESOLUTION - INTERACTIVE DEMO")
    print("=" * 65)
    
    print("\nEnter Business 1 Details:")
    n1 = input("  Name    : ").strip() or "Zephay Labs Inc"
    a1 = input("  Address : ").strip() or "100 Main St, Austin, TX"
    c1 = input("  Country : ").strip() or "US"
    
    print("\nEnter Business 2 Details:")
    n2 = input("  Name    : ").strip() or "Zephay Laboratories"
    a2 = input("  Address : ").strip() or "100 Main Street, Suite 4, Austin, TX"
    c2 = input("  Country : ").strip() or "US"
    
    b1 = matcher.format_entity(n1, a1, c1)
    b2 = matcher.format_entity(n2, a2, c2)
    
    res = matcher.predict(b1, b2)
    
    print("\n" + "=" * 65)
    print(" 🔍 MATCHING VERDICT")
    print("=" * 65)
    print(f"  Decision    : {res['decision']}")
    print(f"  Confidence  : {res['confidence']}")
    print(f"  Threshold   : 50.00%")
    print("\n 📊 Key Feature Signals:")
    print(f"  - Name Similarity Ratio   : {res['features']['name_similarity']:.1f}%")
    print(f"  - Partial Ratio           : {res['features']['partial_ratio']:.1f}%")
    print(f"  - Token Sort Ratio        : {res['features']['token_sort_ratio']:.1f}%")
    print(f"  - Address Similarity Ratio: {res['features']['address_similarity']:.1f}%")
    print(f"  - Country Match           : {'Yes (1)' if res['features']['country_match'] == 1 else 'No (0)'}")
    print(f"  - City Match              : {'Yes (1)' if res['features']['city_match'] == 1 else 'No (0)'}")
    print(f"  - First Word Match        : {'Yes (1)' if res['features']['first_word_match'] == 1 else 'No (0)'}")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Entity Resolution Matcher")
    parser.add_argument("--name1", type=str, help="Business 1 Name")
    parser.add_argument("--addr1", type=str, help="Business 1 Address")
    parser.add_argument("--country1", type=str, default="US", help="Business 1 Country")
    parser.add_argument("--name2", type=str, help="Business 2 Name")
    parser.add_argument("--addr2", type=str, help="Business 2 Address")
    parser.add_argument("--country2", type=str, default="US", help="Business 2 Country")
    parser.add_argument("--threshold", type=float, default=0.5, help="Classification decision threshold")
    
    args = parser.parse_args()
    matcher = EntityMatcher()

    if args.name1 and args.name2:
        b1 = matcher.format_entity(args.name1, args.addr1 or "", args.country1)
        b2 = matcher.format_entity(args.name2, args.addr2 or "", args.country2)
        res = matcher.predict(b1, b2, threshold=args.threshold)
        print(f"\nVerdict: {res['decision']} (Confidence: {res['confidence']})")
        print(f"Name Similarity: {res['features']['name_similarity']}% | Address Sim: {res['features']['address_similarity']}%")
    else:
        run_interactive(matcher)

if __name__ == "__main__":
    main()
