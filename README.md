# Business Entity Resolution

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Accuracy](https://img.shields.io/badge/Benchmark_Accuracy-99.33%25-brightgreen.svg)]()
[![Precision](https://img.shields.io/badge/Precision-99.11%25-blue.svg)]()
[![Recall](https://img.shields.io/badge/Recall-99.55%25-orange.svg)]()
[![F1-Score](https://img.shields.io/badge/F1--Score-99.33%25-purple.svg)]()

## Overview

**Business Entity Resolution** is an enterprise-grade Machine Learning project that identifies whether business records across multiple disparate datasets refer to the same real-world business entity without shared primary keys.

This project combines advanced text normalization, 13-feature engineering, multi-key phonetic blocking, a championship machine learning classifier, and graph-based transitive closure to maximize entity matching accuracy and system efficiency.

---

## Features

- **Advanced Data Cleaning**: Strips 30+ corporate legal suffixes (`Pvt Ltd`, `Inc`, `LLC`, `SARL`) and standardizes street abbreviations (`St` -> `Street`, `Rd` -> `Road`).
- **Multi-Key Blocking**: Prunes **>99.9%** of candidate pairs from an $O(N^2)$ comparison space using geographic partitioning and phonetic Soundex indexing (**1,055× speedup**).
- **13-Feature Engineering Suite**: Computes Levenshtein edit distance, partial ratio, token sort ratio, token set ratio, address similarity, city/state/country matches, and anchor word tokens.
- **Random Forest Classifier**: Champion model achieving **99.33% accuracy** and **99.11% precision** on holdout evaluation.
- **Candidate Graph Linking & Transitive Closure**: Uses NetworkX connected components to unify multi-source matches ($S_1 \leftrightarrow S_2 \leftrightarrow S_3$) under canonical entity clusters.
- **Batch & Real-Time Inference**: Sub-millisecond pairwise prediction CLI and Python API with confidence scoring.
- **Error Analysis & Evaluation**: Comprehensive confusion matrix and feature importance ranking.

---

## Project Structure

```text
BusinessEntityResolution/
│
├── dataset/
│   ├── train/                 # Training datasets (Sources 1, 2, 3)
│   ├── test/                  # Test datasets
│   └── processed/             # Cleaned & normalized intermediate datasets
│
├── models/
│   ├── entity_resolution_champion.pkl    # Production Champion Random Forest model
│   ├── entity_resolution_model.pkl       # Baseline model
│   └── feature_list.pkl                  # Serialized 13-feature list
│
├── notebooks/
│   ├── 01_data_loading.ipynb             # Data loading and initial inspection
│   ├── 02_data_cleaning.ipynb            # Text normalization pipeline
│   ├── 03_feature_engineering.ipynb      # Similarity features & phonetic blocking
│   ├── 04_model_training.ipynb           # Model tournament & cross-validation
│   ├── 05_prediction.ipynb               # Pairwise inference demonstration
│   ├── 06_graph_linking.ipynb            # Connected components & transitive closure
│   └── EDA.ipynb                         # Master 140+ cell exploratory notebook
│
├── output/
│   ├── predictions.csv                   # Pairwise test predictions
│   ├── final_submission.csv              # Official unified entity clusters
│   ├── evaluation_report.txt             # Model evaluation report & confusion matrix
│   └── submission.tsv                    # Tab-separated submission file
│
├── src/
│   ├── cleaning.py                       # Text normalization & regex pipeline
│   ├── features.py                       # 13 similarity features & Soundex algorithm
│   ├── blocking.py                       # Multi-key candidate generation & pruning
│   ├── model.py                          # Model training & CV tournament engine
│   ├── inference.py                      # Production inference engine class
│   └── graph_linking.py                  # NetworkX transitive closure & clustering
│
├── predict.py                            # Standalone interactive & CLI inference tool
├── evaluate.py                           # Standalone evaluation & feature importance suite
├── build_presentation.py                 # Automated 16:9 PowerPoint (.pptx) generator
├── BusinessEntityResolution_Presentation.pptx # Official PowerPoint presentation deck
├── PRESENTATION.md                       # Slide deck outline & interview cheatsheet
├── requirements.txt                      # Project dependencies
├── .gitignore                            # Clean Git repository exclusions
└── README.md                             # Project overview and documentation
```

---

## Technologies Used

- **Python** – Core programming language
- **Pandas** – Data manipulation and ingestion
- **NumPy** – Numerical operations and vector arrays
- **Scikit-learn** – Machine Learning models and cross-validation
- **RapidFuzz** – Ultra-fast C++ fuzzy string similarity calculations
- **NetworkX** – Graph construction and connected components
- **Joblib** – Model serialization
- **Matplotlib** – Data visualization
- **Jupyter** – Interactive notebooks
- **python-pptx** – Automated corporate presentation generation

---

## Workflow

1. **Load Datasets**: Ingest business records from multiple disparate sources ($S_1, S_2, S_3$).
2. **Clean Text**: Normalize business names, strip legal suffixes, expand address abbreviations, and extract city/state tokens.
3. **Candidate Blocking**: Partition pairs using Country and Soundex phonetic hashes to eliminate over 99.9% of non-matching comparisons.
4. **Create Similarity Features**: Compute the 13-dimensional similarity feature vector for each candidate pair.
5. **Train Champion Model**: Train and cross-validate Random Forest, XGBoost, and LightGBM models (Random Forest wins with 99.11% precision).
6. **Predict Matches**: Generate probabilities and match classifications for candidate business pairs.
7. **Apply Graph Linking**: Build an undirected entity match graph and apply transitive closure.
8. **Generate Final Entities**: Export resolved canonical entities to `output/final_submission.csv`.

---

## Benchmark Results

### 1. Model Evaluation Metrics
- **Holdout Test Accuracy**: **99.33%**
- **Precision**: **99.11%** *(Protects against erroneous customer record merging)*
- **Recall**: **99.55%** *(Near-zero missed duplicate entities)*
- **F1-Score**: **99.33%**
- **5-Fold Stratified Cross-Validation**: **99.10%** ($\pm 0.43\%$)

### 2. Multi-Key Blocking Speedup (Module 3)
| Strategy | Rule Applied | Pairs Evaluated | Pruning Rate | Effective Speedup |
| :--- | :--- | :---: | :---: | :---: |
| **Naive (No Blocking)** | Compare All Pairs ($N \times M$) | **2,500,000** | $0.00\%$ | $1.0\times$ (Baseline) |
| **Lesson 2: First Letter** | Match on `name[:1]` | **124,240** | **95.03%** | $\sim 20\times$ faster |
| **Lesson 3: First 2 Letters** | Match on `name[:2]` | **17,579** | **99.30%** | $\sim 142\times$ faster |
| **Lesson 4: Country Partition** | Match on `country` | **981,088** | **60.76%** | $\sim 2.5\times$ faster |
| **Lesson 5: Soundex Indexing** | Soundex of first token | **4,861** | **99.81%** | $\sim 514\times$ faster |
| **Lesson 6: Multi-Key Hybrid** 🏆 | `Country + Soundex(first_token)` | **2,368** | **99.91%** | **1,055× FASTER!** |

### 3. Top Feature Importances
1. `name_similarity` (**21.87%**) – Levenshtein edit distance
2. `partial_ratio` (**19.93%**) – Substring brand root match
3. `address_similarity` (**14.89%**) – Street address matching
4. `token_sort_ratio` (**13.71%**) – Permutation invariant word matching
5. `token_set_ratio` (**11.18%**) – Noise and extra descriptor robust

---

## Quickstart & Usage

### 1. Installation
```bash
git clone https://github.com/VemireddyBhavana/Business-Entity-Resolution.git
cd Business-Entity-Resolution
pip install -r requirements.txt
```

### 2. Run Reusable Inference (`predict.py`)
```bash
# Command-Line Interface
python predict.py --name1 "Zephay Labs Inc" --addr1 "100 Main St, Austin, TX" \
                  --name2 "Zephay Laboratories" --addr2 "100 Main Street, Austin, TX"

# Or launch interactive mode:
python predict.py
```

### 3. Evaluate the Model (`evaluate.py`)
```bash
python evaluate.py
```

### 4. Build Presentation Deck (`build_presentation.py`)
```bash
python build_presentation.py
```
Outputs: `BusinessEntityResolution_Presentation.pptx`

---

## Future Improvements

- **Deep Learning & Sentence Embeddings**: Fine-tuning transformer models (e.g. `all-MiniLM-L6-v2` or `BGE`) for dense entity embeddings.
- **FAISS Vector Search**: Scaling nearest-neighbor candidate generation for billions of enterprise records.
- **Active Learning**: Interactive human-in-the-loop validation for edge cases with intermediate probabilities (45%–55%).
- **Real-Time API Deployment**: FastAPI microservice containerized with Docker and deployed via Kubernetes.

---

## Author

**Bhavana Vemireddy**  
- **GitHub**: [@VemireddyBhavana](https://github.com/VemireddyBhavana)  
- **Repository**: [Business-Entity-Resolution](https://github.com/VemireddyBhavana/Business-Entity-Resolution)
