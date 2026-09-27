"""
HIGH-PERFORMANCE BUSINESS ENTITY RESOLUTION - MEMORY-EFFICIENT PIPELINE
======================================================================
Redesigned for machines with limited RAM (< 2GB free).
Strategy: Chunked processing + TF-IDF blocking + LightGBM
"""

import os, re, gc, time, joblib
import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODELS_DIR = "models"
OUTPUT_DIR = "output"
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUFFIXES = re.compile(
    r'\b(pvt|private|limited|ltd|llc|inc|corp|corporation|co|company|plc|gmbh|ag|sa|srl|bv|nv|pty|ug|lp|llp)\b\.?',
    re.I
)
STOP_WORDS = frozenset({'the','and','of','for','at','by','a','an','in','on','to'})

def clean_name(text):
    if not text or (isinstance(text, float) and np.isnan(text)):
        return ''
    t = SUFFIXES.sub(' ', re.sub(r'[^\w\s]',' ', str(text).lower()))
    return ' '.join(w for w in t.split() if w not in STOP_WORDS and len(w) > 1)

def clean_address(text):
    if not text or (isinstance(text, float) and np.isnan(text)):
        return ''
    t = re.sub(r'\bno\.\s*','', str(text).lower())
    return ' '.join(re.sub(r'[^\w\s,]',' ', t).split())

def get_country(text):
    if not text or (isinstance(text, float) and np.isnan(text)):
        return 'US'
    return str(text).strip().upper()[:2]

def clean_row(row):
    return (clean_name(row.get('business_name','')),
            clean_address(row.get('business_address','')),
            get_country(row.get('country','')))

def extract_features(n1, n2, a1, a2, c1, c2):
    nr1 = fuzz.ratio(n1, n2)
    np1 = fuzz.partial_ratio(n1, n2)
    nt1 = fuzz.token_sort_ratio(n1, n2)
    nt2 = fuzz.token_set_ratio(n1, n2)
    ar  = fuzz.ratio(a1, a2)
    ap  = fuzz.partial_ratio(a1, a2)
    country_m = int(c1 == c2)
    w1 = set(n1.split()); w2 = set(n2.split())
    common = len(w1 & w2)
    jaccard = common / max(len(w1 | w2), 1)
    fw = int(bool(n1.split() and n2.split() and n1.split()[0]==n2.split()[0]))
    lw = int(bool(n1.split() and n2.split() and n1.split()[-1]==n2.split()[-1]))
    return [nr1, np1, nt1, nt2, ar, ap, country_m, common, jaccard, fw, lw,
            abs(len(n1)-len(n2)), abs(len(a1)-len(a2))]

print("=" * 62)
print("  BUSINESS ENTITY RESOLUTION - MEMORY-EFFICIENT PIPELINE")
print("=" * 62)

# -----------------------------------------------------------------
# STEP 1: Build training data using chunked reads (low memory)
# -----------------------------------------------------------------
print("\n[1/6] Building training pairs (chunked to save RAM)...")
t0 = time.time()

POS_LIMIT  = 150000
NEG_RATIO  = 3
CHUNK_SIZE = 50000

# Load ground truth completely (it's index-only: 2 cols, manageable)
gt = pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t')
gt_dict = {}  # s1_id -> first S3 match
for _, row in gt.iterrows():
    s1_id = row['source1_entity_id']
    matched = str(row['matched_entity_ids'])
    if matched == 'nan': continue
    for mid in matched.split(','):
        mid = mid.strip()
        if mid.startswith('S3-'):
            gt_dict[s1_id] = mid
            break
del gt
gc.collect()
print(f"  GT S1->S3 map: {len(gt_dict):,} entries  ({time.time()-t0:.0f}s)")

# Chunk-read train_source1 to build s1 lookup for GT entries
print("  Reading train_source1 in chunks...")
s1_needed = set(gt_dict.keys())
s1_lookup = {}  # id -> (clean_name, clean_addr, country)
for chunk in pd.read_csv('dataset/train/train_source1.tsv', sep='\t',
                          chunksize=CHUNK_SIZE,
                          usecols=['entity_id','business_name','business_address','country']):
    for _, row in chunk.iterrows():
        if row['entity_id'] in s1_needed:
            s1_lookup[row['entity_id']] = (
                clean_name(row['business_name']),
                clean_address(row['business_address']),
                get_country(row['country'])
            )
    if len(s1_lookup) >= len(s1_needed):
        break
gc.collect()
print(f"  S1 lookup built: {len(s1_lookup):,}  ({time.time()-t0:.0f}s)")

# Determine which S3 IDs are needed
s3_needed = set(gt_dict.values())
s3_lookup = {}
print("  Reading train_source3 in chunks...")
for chunk in pd.read_csv('dataset/train/train_source3.tsv', sep='\t',
                          chunksize=CHUNK_SIZE,
                          usecols=['entity_id','business_name','business_address','country']):
    for _, row in chunk.iterrows():
        if row['entity_id'] in s3_needed:
            s3_lookup[row['entity_id']] = (
                clean_name(row['business_name']),
                clean_address(row['business_address']),
                get_country(row['country'])
            )
    if len(s3_lookup) >= len(s3_needed):
        break
gc.collect()
print(f"  S3 lookup built: {len(s3_lookup):,}  ({time.time()-t0:.0f}s)")

# Build positive pairs
pos_pairs = []
for s1_id, s3_id in gt_dict.items():
    if s1_id in s1_lookup and s3_id in s3_lookup:
        pos_pairs.append((s1_id, s3_id, 1))
    if len(pos_pairs) >= POS_LIMIT:
        break

del gt_dict, s3_needed
gc.collect()
print(f"  Positive pairs: {len(pos_pairs):,}")

# Build negatives by random pairing from already-loaded lookups
rng = np.random.default_rng(42)
s1_arr = np.array(list(s1_lookup.keys()))
s3_arr = np.array(list(s3_lookup.keys()))
n_neg = min(len(pos_pairs) * NEG_RATIO, 400000)
pos_set = {(a, b) for a, b, _ in pos_pairs}
neg_pairs = []
for _ in range(n_neg * 2):
    a = rng.choice(s1_arr)
    b = rng.choice(s3_arr)
    if (a, b) not in pos_set:
        neg_pairs.append((a, b, 0))
    if len(neg_pairs) >= n_neg:
        break
print(f"  Negative pairs: {len(neg_pairs):,}")

# Extract features
print("  Extracting features...")
all_pairs = pos_pairs + neg_pairs
rng.shuffle(all_pairs)
X_rows, y_labels = [], []
for s1_id, s3_id, label in all_pairs:
    n1, a1, c1 = s1_lookup[s1_id]
    n2, a2, c2 = s3_lookup[s3_id]
    X_rows.append(extract_features(n1, n2, a1, a2, c1, c2))
    y_labels.append(label)

X = np.array(X_rows, dtype=np.float32)
y = np.array(y_labels, dtype=np.int32)
print(f"  Feature matrix: {X.shape}  ({time.time()-t0:.0f}s)")

del s1_lookup, s3_lookup, all_pairs, pos_pairs, neg_pairs, X_rows, y_labels
gc.collect()

# -----------------------------------------------------------------
# STEP 2: Train LightGBM
# -----------------------------------------------------------------
print("\n[2/6] Training LightGBM...")
t0 = time.time()
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, random_state=42, stratify=y)

model = lgb.LGBMClassifier(
    n_estimators=400, max_depth=7, learning_rate=0.06,
    num_leaves=63, min_child_samples=20,
    subsample=0.8, colsample_bytree=0.8,
    class_weight='balanced', random_state=42, verbose=-1,
    n_jobs=4
)
model.fit(X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(period=50)]
)
val_preds = model.predict(X_val)
print(classification_report(y_val, val_preds, target_names=['Non-Match','Match']))
model_path = f"{MODELS_DIR}/entity_resolution_champion.pkl"
joblib.dump(model, model_path)
print(f"  Saved model: {model_path}  ({time.time()-t0:.0f}s)")
del X, y, X_train, X_val, y_train, y_val
gc.collect()

# -----------------------------------------------------------------
# STEP 3: Build TF-IDF index PER SOURCE (not combined) to save RAM
# -----------------------------------------------------------------
print("\n[3/6] Building TF-IDF indices for test S2 and S3...")
t0 = time.time()

def load_and_clean_source(filepath, chunksize=100000):
    """Load a test source in chunks, returning cleaned DataFrame."""
    dfs = []
    for chunk in pd.read_csv(filepath, sep='\t', chunksize=chunksize,
                              usecols=['entity_id','business_name','business_address','country']):
        chunk['clean_name'] = chunk['business_name'].apply(clean_name)
        chunk['clean_addr'] = chunk['business_address'].apply(clean_address)
        chunk['clean_country'] = chunk['country'].apply(get_country)
        dfs.append(chunk[['entity_id','clean_name','clean_addr','clean_country']])
    return pd.concat(dfs, ignore_index=True)

print("  Loading test S2...")
ts2 = load_and_clean_source('dataset/test/test_source2.tsv')
print(f"  S2: {len(ts2):,}  ({time.time()-t0:.0f}s)")

print("  Loading test S3...")
ts3 = load_and_clean_source('dataset/test/test_source3.tsv')
print(f"  S3: {len(ts3):,}  ({time.time()-t0:.0f}s)")

# Fit TF-IDF on a sample of both sources combined, then transform each
print("  Fitting TF-IDF vectorizer...")
# Sample 500K names from each for fitting vocab
s2_sample = ts2['clean_name'].sample(min(500000, len(ts2)), random_state=42).tolist()
s3_sample = ts3['clean_name'].sample(min(500000, len(ts3)), random_state=42).tolist()
tfidf = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4), min_df=3, max_features=100000)
tfidf.fit(s2_sample + s3_sample)
del s2_sample, s3_sample
gc.collect()

ts2_names_full = (ts2['clean_country'] + ' ' + ts2['clean_name']).tolist()
ts3_names_full = (ts3['clean_country'] + ' ' + ts3['clean_name']).tolist()

print("  Transforming S2...")
s2_matrix = tfidf.transform(ts2_names_full)
del ts2_names_full
print(f"  S2 matrix: {s2_matrix.shape}  ({time.time()-t0:.0f}s)")

print("  Transforming S3...")
s3_matrix = tfidf.transform(ts3_names_full)
del ts3_names_full
print(f"  S3 matrix: {s3_matrix.shape}  ({time.time()-t0:.0f}s)")
gc.collect()

# -----------------------------------------------------------------
# STEP 4: Load test S1 in chunks, predict matches
# -----------------------------------------------------------------
print("\n[4/6] Predicting for all S1 entities...")
t0 = time.time()

ts2_dict = ts2.set_index('entity_id')[['clean_name','clean_addr','clean_country']].to_dict('index')
ts3_dict = ts3.set_index('entity_id')[['clean_name','clean_addr','clean_country']].to_dict('index')
ts2_ids  = ts2['entity_id'].values
ts3_ids  = ts3['entity_id'].values
del ts2, ts3
gc.collect()

TOP_K     = 8
THRESHOLD = 0.45
BATCH_S1  = 2000
results   = []

# Count total S1 rows first
total_s1 = sum(len(chunk) for chunk in pd.read_csv(
    'dataset/test/test_source1.tsv', sep='\t', chunksize=10000, usecols=['entity_id']))

print(f"  Total S1 entities: {total_s1:,}")

done = 0
for chunk in pd.read_csv('dataset/test/test_source1.tsv', sep='\t',
                          chunksize=BATCH_S1,
                          usecols=['entity_id','business_name','business_address','country']):
    chunk['clean_name']    = chunk['business_name'].apply(clean_name)
    chunk['clean_addr']    = chunk['business_address'].apply(clean_address)
    chunk['clean_country'] = chunk['country'].apply(get_country)

    q_names = (chunk['clean_country'] + ' ' + chunk['clean_name']).tolist()
    q_mat   = tfidf.transform(q_names)

    sim_s2 = cosine_similarity(q_mat, s2_matrix, dense_output=False)
    sim_s3 = cosine_similarity(q_mat, s3_matrix, dense_output=False)

    for i, (_, s1_row) in enumerate(chunk.iterrows()):
        e1 = (s1_row['clean_name'], s1_row['clean_addr'], s1_row['clean_country'])
        matched_ids = []

        for sim_mat, id_arr, cand_dict in [(sim_s2, ts2_ids, ts2_dict),
                                            (sim_s3, ts3_ids, ts3_dict)]:
            sims    = np.asarray(sim_mat[i].todense()).flatten()
            top_idx = np.argsort(sims)[-TOP_K:][::-1]
            top_idx = [j for j in top_idx if sims[j] > 0.25]
            if not top_idx: continue
            feats, cids = [], []
            for j in top_idx:
                cid = id_arr[j]
                if cid not in cand_dict: continue
                e2 = cand_dict[cid]
                feats.append(extract_features(e1[0],e2['clean_name'],
                                              e1[1],e2['clean_addr'],
                                              e1[2],e2['clean_country']))
                cids.append(cid)
            if feats:
                probs = model.predict_proba(np.array(feats, dtype=np.float32))[:,1]
                matched_ids += [c for c, p in zip(cids, probs) if p >= THRESHOLD]

        results.append({
            'source1_entity_id': s1_row['entity_id'],
            'matched_entity_ids': ','.join(sorted(set(matched_ids))) if matched_ids else ''
        })

    done += len(chunk)
    elapsed = time.time() - t0
    rate    = done / max(elapsed, 1)
    eta     = (total_s1 - done) / max(rate, 1)
    print(f"  [{done:,}/{total_s1:,}] {done/total_s1*100:.1f}% | {rate:.0f}/s | ETA:{eta/60:.1f}min")

print(f"\n  Prediction done in {time.time()-t0:.0f}s")

# -----------------------------------------------------------------
# STEP 5: Save outputs
# -----------------------------------------------------------------
print("\n[5/6] Saving outputs...")
result_df = pd.DataFrame(results)
has_match = result_df['matched_entity_ids'].str.len() > 0
print(f"  With matches : {has_match.sum():,}")
print(f"  No matches   : {(~has_match).sum():,}")

result_df.to_csv(f"{OUTPUT_DIR}/matching_results.tsv", sep='\t', index=False)
result_df.to_csv(f"{OUTPUT_DIR}/submission.csv", index=False)
result_df.to_csv(f"{OUTPUT_DIR}/final_submission.csv", index=False)
print(f"  Saved to {OUTPUT_DIR}/")

print("\n" + "=" * 62)
print(f"  DONE! {len(result_df):,} entities processed | {has_match.sum():,} matches")
print("=" * 62)
