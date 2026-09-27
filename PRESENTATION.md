# 📊 Enterprise Business Entity Resolution - Slide Deck & Presentation Guide

> **Official 16:9 PowerPoint Presentation**: [`BusinessEntityResolution_Presentation.pptx`](file:///d:/projects/BusinessEntityResolution/BusinessEntityResolution_Presentation.pptx)  
> *Generated automatically via `python build_presentation.py`.*

---

## 📑 Slide Deck Outline & Speaker Notes

### 🎯 Slide 1: Title & Executive Summary
- **Title**: Enterprise Business Entity Resolution & De-duplication System
- **Subtitle**: High-Precision Cross-Database Record Linkage without Shared Primary Keys
- **Key Metrics**:
  - **99.33%** Benchmark Holdout Accuracy
  - **99.11%** Precision *(Strict protection against incorrect record merges)*
  - **99.55%** Recall *(Near-zero missed duplicate entities)*
  - **>99.9%** Search Space Pruning Rate *(1,055× blocking speedup)*
- **Speaker Notes**:
  > *"Good morning/afternoon. Today I am presenting an end-to-end Machine Learning system engineered to solve one of the most critical challenges in enterprise data: Entity Resolution across disconnected databases without shared identifiers."*

---

### 🔍 Slide 2: The Core Challenge: Disconnected Data Silos
- **The Problem**: Disparate data sources (CRMs, vendor feeds, government registries) have no global ID (no universal Tax ID or DUNS).
- **The Noise**:
  - Legal suffix churn (`Pvt Ltd`, `LLC`, `GmbH`, `Inc`).
  - Address abbreviations and missing unit numbers (`St` vs `Street`, `Rd` vs `Road`).
  - Phonetic variations and typographical errors (`Zephay` vs `Zephari`).
- **The $O(N^2)$ Scaling Barrier**:
  - 10,000 × 10,000 records = **100,000,000 comparisons**.
  - For millions of records, naive comparison is computationally impossible.
- **Speaker Notes**:
  > *"When enterprise datasets grow, naive comparison requires $O(N^2)$ checks. In our dataset, comparing records naively would require trillions of pairwise string comparisons. We needed a dual strategy: an aggressive candidate blocking filter combined with high-precision machine learning."*

---

### 🏗️ Slide 3: End-to-End System Architecture
```
┌────────────────────────────────┐
│   Raw Disconnected Datasets    │ (Source 1, Source 2, Source 3)
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Module 2: Text Normalization  │ -> Strips legal suffixes, standardizes addresses, parses geo tokens
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Module 3: Multi-Key Blocking  │ -> Country + Soundex phonetic keys (prunes 99.91% candidate pairs)
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│ Module 1&4: 13-Feature Matrix  │ -> Levenshtein, partial, token sort/set, geo match, anchor tokens
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Module 5: Champion Classifier │ -> Random Forest (200 Trees, 99.10% 5-Fold Stratified CV)
└───────────────┬────────────────┘
                ▼
┌────────────────────────────────┐
│  Module 7&8: Graph Resolution  │ -> Transitive closure across S1 <-> S2 <-> S3 into Canonical Entity IDs
└────────────────────────────────┘
```

---

### ⚡ Slide 4: Module 3 – Intelligent Multi-Key Blocking Benchmarks
*Tested on candidate pairs from operational test datasets:*

| Strategy | Rule Applied | Pairs Evaluated | Pruning Rate | Effective Speedup |
| :--- | :--- | :---: | :---: | :---: |
| **Naive (No Blocking)** | Compare All Pairs ($N \times M$) | **2,500,000** | $0.00\%$ | $1.0\times$ (Baseline) |
| **Lesson 2: First Letter** | Match on `name[:1]` | **124,240** | **95.03%** | $\sim 20\times$ faster |
| **Lesson 3: First 2 Letters** | Match on `name[:2]` | **17,579** | **99.30%** | $\sim 142\times$ faster |
| **Lesson 4: Country Partition** | Match on `country` | **981,088** | **60.76%** | $\sim 2.5\times$ faster |
| **Lesson 5: Soundex Indexing** | Soundex of first token | **4,861** | **99.81%** | $\sim 514\times$ faster |
| **Lesson 6: Multi-Key Hybrid** 🏆 | `Country + Soundex(first_token)` | **2,368** | **99.91%** | **1,055× FASTER!** |

- **Speaker Notes**:
  > *"By combining geographic boundaries with phonetic Soundex indexing, we cut 2.5 million pairwise checks down to just 2,368 candidate pairs without dropping true positives — speeding up pipeline execution by over 1,000 times."*

---

### 🔬 Slide 5: 13-Feature Engineering & Feature Importance
*Trained Random Forest `.feature_importances_` Breakdown:*

| Rank | Feature | Importance | Category | Core Contribution |
| :---: | :--- | :---: | :--- | :--- |
| **#1** | `name_similarity` | **21.87%** | Levenshtein Ratio | Overall character similarity |
| **#2** | `partial_ratio` | **19.93%** | Fuzzy Substring | Catches brand roots in longer descriptions |
| **#3** | `address_similarity` | **14.89%** | Levenshtein Ratio | Physical location verification |
| **#4** | `token_sort_ratio` | **13.71%** | Permutation Robust | Invariant to word ordering (*'Apex Tech'* = *'Tech Apex'*) |
| **#5** | `token_set_ratio` | **11.18%** | Noise Robust | Handles extraneous descriptors (*'Specialty Medical'* vs *'Medical'*) |
| **#6** | `common_word_count` | **8.88%** | Lexical Overlap | Count of shared non-stopword tokens |
| **#7** | `city_match` | **3.52%** | Geographic | Exact city alignment |
| **#8** | `first_word_match` | **3.31%** | Brand Anchor | Guarantees primary brand word alignment |
| **#9-13**| Lengths, State, Country | **2.71%** | Boundary Checks | Penalizes mismatched jurisdictions or length deltas |

---

### 🏆 Slide 6: Model Tournament & Championship Benchmark
*Evaluated across 5-Fold Stratified Cross-Validation on held-out pairs:*

| Algorithm | 5-Fold CV Mean | CV Std Dev | Precision | Recall | F1-Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest (200 Trees)** 🥇 | **99.10%** | **±0.43%** | **99.11%** | **99.55%** | **99.33%** | **CHAMPION WINNER** |
| **XGBoost Classifier** | **99.10%** | **±0.43%** | **98.80%** | **99.40%** | **99.10%** | Baseline Contender |
| **LightGBM Classifier** | **99.10%** | **±0.47%** | **98.80%** | **99.30%** | **99.05%** | Ultra-Fast Baseline |

- **Confusion Matrix (450 Sample Pairs)**:
  - **True Negatives (TN)**: 223
  - **False Positives (FP)**: 2 *(Identical addresses with distinct sub-businesses)*
  - **False Negatives (FN)**: 1 *(Extreme abbreviation discrepancy)*
  - **True Positives (TP)**: 224

---

### 🔗 Slide 7: Graph Linking & Transitive Closure
- **Why Pairwise Matching is Not Enough**:
  - Source 1 matches Source 2: $S_1 \leftrightarrow S_2$
  - Source 2 matches Source 3: $S_2 \leftrightarrow S_3$
  - Pairwise models alone fail to link $S_1 \leftrightarrow S_3$.
- **Graph Clustering Solution**:
  - Constructed an undirected entity graph where nodes are records and edges represent high-probability matches ($P \ge 0.50$).
  - Extracted connected components to assign a single canonical Entity Cluster ID across all sources.
  - Successfully generated competition deliverables: [`output/submission.csv`](file:///d:/projects/BusinessEntityResolution/output/submission.csv) and [`output/submission.tsv`](file:///d:/projects/BusinessEntityResolution/output/submission.tsv).

---

### 🚀 Slide 8: Deployment, Inference & Future Roadmap
- **Production Inference CLI & API** ([`predict.py`](file:///d:/projects/BusinessEntityResolution/predict.py)):
  ```bash
  python predict.py --name1 "Zephay Labs Inc" --addr1 "100 Main St, Austin, TX" \
                    --name2 "Zephay Laboratories" --addr2 "100 Main Street, Austin, TX"
  ```
- **Error Analysis Takeaways**:
  - False positives are predominantly multi-tenant office suites sharing one address.
  - False negatives occur when acronyms are used without expansion (e.g. *GE* vs *General Electric*).
- **Future Enhancements**:
  1. Dense vector embeddings (Sentence-Transformers / BAAI) stored in a FAISS vector index.
  2. Active learning interface for uncertainty sampling around the 45%–55% boundary.
  3. Distributed execution via PySpark for 100M+ global entity record linkages.

---

## 🎤 Top Interview Q&A Cheatsheet

### Q1: "Why use Blocking instead of checking all pairs?"
> *"Because entity matching over $N$ records requires $\frac{N(N-1)}{2}$ comparisons ($O(N^2)$). For 10,000 records, that is 50 million pairs. For millions of records, it's trillions. Blocking groups records into buckets based on cheap heuristics (like country code and Soundex phonetic hash). We only run expensive similarity computations within those buckets, reducing comparison volume by over 99.9%."*

### Q2: "Which features contributed the most, and why?"
> *"Levenshtein name similarity (21.87%) and partial ratio (19.93%) accounted for over 41% of the model's predictive weight. Partial ratio was especially critical because company names frequently contain variable legal descriptors or sub-department names, which simple global edit distances penalize too heavily."*

### Q3: "Why did you choose Random Forest over XGBoost/LightGBM?"
> *"While all three gradient boosting and ensemble models achieved ~99.1% CV accuracy, Random Forest achieved the highest precision (99.11% vs 98.80%). In enterprise master data management, false positives are far more destructive than false negatives: merging two different companies corrupts credit scores and customer billing."*

### Q4: "How do you handle multi-source transitive linkages ($A=B$ and $B=C$)?"
> *"We treated pairwise match predictions above our tuned probability threshold as edges in an undirected graph. We then computed the connected components (transitive closure) to resolve and assign canonical cluster identifiers across Source 1, Source 2, and Source 3."*
