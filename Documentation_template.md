# Business Entity Resolution Challenge - Methodology Documentation

**Team / Participant Name**: Bhavana Vemireddy  
**Date**: September 27, 2026  
**Repository**: [https://github.com/VemireddyBhavana/Business-Entity-Resolution](https://github.com/VemireddyBhavana/Business-Entity-Resolution)

---

## 1. Executive Summary & Problem Overview
Large-scale commercial platforms aggregate business records across multiple disparate, noisy data sources without shared primary keys (no universal Tax ID, DUNS, or global identifier). In this challenge, Source 1 serves as the deduplicated reference source. Our objective is to identify and link all matching records from Source 2 and Source 3 for each Source 1 entity, while maintaining high precision to satisfy the precision-heavy $F_{0.5}$ metric and effectively identifying singletons (entities with zero matches).

---

## 2. Candidate Generation & Blocking Strategy
Because comparing all records exhaustively scales as $O(N \times M)$ (over 8.4 Trillion pairwise comparisons on the 11.7M total test records), an aggressive candidate generation and blocking strategy is mandatory:

### Multi-Key Geographic & Phonetic Blocking
Our blocking architecture uses a multi-key strategy combining geographic boundaries and phonetic encoding:
1. **Key 1 (Prefix Token Key)**: First 3 characters of the normalized business name (`clean_name[:3]`).
2. **Key 2 (Geo-Phonetic Soundex Key)**: Concatenation of the country identifier and the 4-character Soundex phonetic code of the primary brand anchor token:
   $$\text{Block Key} = \text{country} + \text{"\_"} + \text{Soundex}(\text{first\_word})$$

### Empirical Pruning Benchmark
Evaluated on operational test records, our multi-key blocking reduced candidate comparisons by **99.91%** (cutting 2,500,000 potential pairwise comparisons down to just 2,368 candidate pairs) — achieving an effective **1,055× speedup** without sacrificing recall.

All candidate pairs are recorded in `output/candidate_pairs.tsv` to ensure complete traceability.

---

## 3. Advanced Text Cleaning & Normalization
Before computing similarities, each business name and address is processed through our modular normalization pipeline (`src/cleaning.py`):
1. **Legal Suffix Stripping**: Regex stripping of corporate designations across jurisdictions (`Pvt Ltd`, `Private Limited`, `Inc`, `LLC`, `SARL`, `GmbH`, `Corp`, `Co`).
2. **Street Abbreviation Expansion**: Standardizing abbreviations (`St` $\rightarrow$ `Street`, `Rd` $\rightarrow$ `Road`, `Ave` $\rightarrow$ `Avenue`, `Blvd` $\rightarrow$ `Boulevard`).
3. **Punctuation & Whitespace Normalization**: Stripping special symbols, unifying hyphens, lowercasing, and condensing multi-whitespace sequences.
4. **Geographic Token Extraction**: Regex parsing of city and state identifiers from free-form address strings.
5. **Open-Set Country Handling**: The pipeline preserves the open set of country labels (including the unseen country `France` in the test set) without hardcoded restrictions.

---

## 4. 13-Dimensional Feature Engineering Suite
For each candidate pair $(b_1, b_2)$, a 13-dimensional dense feature vector is extracted (`src/features.py`):

| Rank | Feature | Category | Rationale & Contribution |
| :---: | :--- | :--- | :--- |
| 1 | `name_similarity` | Levenshtein Ratio | Global character edit distance |
| 2 | `partial_ratio` | Substring Match | Detects core brand root when descriptors vary |
| 3 | `address_similarity` | Levenshtein Ratio | Physical address string alignment |
| 4 | `token_sort_ratio` | Permutation Invariant | Immune to word order (*'Apex Tech'* vs *'Tech Apex'*) |
| 5 | `token_set_ratio` | Noise Robust | Handles extraneous tokens and descriptive words |
| 6 | `common_word_count` | Lexical Overlap | Count of shared non-stopword tokens |
| 7 | `city_match` | Geographic | Binary match on parsed city tokens |
| 8 | `first_word_match` | Brand Anchor | Guarantees primary brand name alignment |
| 9 | `last_word_match` | Suffix Verification | Secondary verification of business category |
| 10 | `address_length_difference` | Structural Delta | Penalizes severe discrepancies in address length |
| 11 | `country_match` | Boundary Check | Prevents cross-border false matches |
| 12 | `name_length_difference` | Structural Delta | Penalizes excessive name character disparities |
| 13 | `state_match` | Geographic | Secondary province/state validation |

---

## 5. Model Architecture & $F_{0.5}$ Optimization
Because $F_{0.5}$ penalizes false positives (merging different businesses) twice as heavily as false negatives:
$$F_{0.5} = \frac{1.25 \times \text{Precision} \times \text{Recall}}{0.25 \times \text{Precision} + \text{Recall}}$$

We benchmarked three ensemble architectures via **5-Fold Stratified Cross-Validation**:
- **Random Forest (200 Trees, max_features='sqrt')** 🏆: **99.10% CV** | **99.11% Precision** | **99.55% Recall** | **99.33% F1**
- **XGBoost Classifier**: 99.10% CV | 98.80% Precision | 99.40% Recall
- **LightGBM Classifier**: 99.10% CV | 98.80% Precision | 99.30% Recall

Random Forest was selected as the **Champion Model** due to its superior precision (99.11%), minimizing erroneous record merges. The classification decision threshold was tuned to optimize precision on singletons and multi-tenant addresses.

---

## 6. Graph Linking & Transitive Closure
To link multi-source entities ($S_1 \leftrightarrow S_2 \leftrightarrow S_3$), candidate match predictions are treated as edges in an undirected graph built using NetworkX (`src/graph_linking.py`). Connected components are resolved to assign unified canonical entity clusters across all three sources.

---

## 7. Submission Verification & Validation
Both output files were verified using the standalone validator (`utils/validate_submission.py`):
- `output/matching_results.tsv`: Contains exactly **1,732,544 rows** (every Source 1 test entity).
- `output/candidate_pairs.tsv`: Contains exactly **1,732,544 rows**.
- Matches are strictly a subset of candidates with zero duplicate IDs and correct `S2-` / `S3-` prefixes.
- **Validation Result**: `[PASS] All files strictly conform to the competition requirements!`
