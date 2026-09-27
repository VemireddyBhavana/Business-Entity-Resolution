import sys
import pandas as pd
from rapidfuzz import fuzz
from collections import defaultdict
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

LEGAL_SUFFIXES = re.compile(
    r'\b(pvt|private|limited|ltd|llc|inc|corp|corporation|co|company|plc|gmbh|ag|sa|srl|bv|nv|pty|ug|lp|llp|sarl|sasu|eurl|sci)\b\.?',
    re.I
)
STOP_WORDS = frozenset({
    'the','and','of','for','at','by','a','an','in','on','to','center','group','services','trading',
    'technologies','tech','enterprises','solutions','management','international','india','france'
})

def clean_name_tokens(text):
    if not text or pd.isna(text): return []
    t = LEGAL_SUFFIXES.sub(' ', re.sub(r'[^\w\s]',' ', str(text).lower()))
    return [w for w in t.split() if w not in STOP_WORDS and len(w) > 1]

def clean_str(text):
    if not text or pd.isna(text): return ''
    return ' '.join(re.sub(r'[^\w\s]',' ', str(text).lower()).split())

def extract_addr_features(text):
    if not text or pd.isna(text): return '', ''
    t = re.sub(r'[^\w\s]', ' ', str(text).lower())
    words = t.split()
    nums = [w for w in words if w.isdigit()]
    num = nums[0] if nums else ''
    street_word = ''
    if num and num in words:
        idx = words.index(num)
        for w in words[idx+1:] + words[:idx]:
            if len(w) >= 3 and not w.isdigit() and w not in ('unit', 'suite', 'floor', 'apt', 'apartment', 'flat', 'street', 'road', 'avenue', 'lane', 'drive', 'block'):
                street_word = w
                break
    elif words:
        for w in words:
            if len(w) >= 4 and not w.isdigit():
                street_word = w
                break
    return num, street_word

# Load data
df_s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t', nrows=5000)
s1_ids = set(df_s1['entity_id'])

gt_map = {}
for chunk in pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t', chunksize=100000):
    m = chunk[chunk['source1_entity_id'].isin(s1_ids)]
    for r in m.itertuples(index=False):
        m_str = str(r.matched_entity_ids)
        if m_str != 'nan' and m_str:
            gt_map[r.source1_entity_id] = set(x.strip() for x in m_str.split(',') if x.strip())

all_target_s3 = set()
for s in gt_map.values():
    all_target_s3.update(x for x in s if x.startswith('S3-'))

df_s3 = []
for chunk in pd.read_csv('dataset/train/train_source3.tsv', sep='\t', chunksize=200000):
    m = chunk[chunk['entity_id'].isin(all_target_s3) | (chunk.index < 50000)]
    df_s3.append(m)
    if len(df_s3) > 5: break
df_s3 = pd.concat(df_s3, ignore_index=True)

idx_s3_tok = defaultdict(list)
idx_s3_addr = defaultdict(list)
rec_s3 = {}

for r in df_s3.itertuples(index=False):
    eid = r.entity_id
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    rec_s3[eid] = (c_name, c_addr)
    for t in clean_name_tokens(r.business_name):
        if len(t) >= 3:
            idx_s3_tok[t].append(eid)
    num, s_word = extract_addr_features(r.business_address)
    if num and s_word:
        idx_s3_addr[(num, s_word)].append(eid)

# Precompute candidate pairs and similarity scores
pairs = []
for r in df_s1.itertuples(index=False):
    eid = r.entity_id
    true_s3 = set(x for x in gt_map.get(eid, set()) if x.startswith('S3-') and x in rec_s3)
    if not true_s3: continue
    
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    tokens = clean_name_tokens(r.business_name)
    num, s_word = extract_addr_features(r.business_address)
    
    cands = set()
    for t in tokens:
        if len(t) >= 3 and t in idx_s3_tok:
            cand_list = idx_s3_tok[t]
            cands.update(cand_list[:60])
    if num and s_word and (num, s_word) in idx_s3_addr:
        cands.update(idx_s3_addr[(num, s_word)][:50])
        
    for cid in cands:
        t_name, t_addr = rec_s3[cid]
        n_sort = fuzz.token_sort_ratio(c_name, t_name)
        n_set  = fuzz.token_set_ratio(c_name, t_name)
        a_part = fuzz.partial_ratio(c_addr, t_addr)
        a_sort = fuzz.token_sort_ratio(c_addr, t_addr)
        is_true = cid in true_s3
        pairs.append((n_sort, n_set, a_part, a_sort, bool(c_addr and t_addr), is_true))

total_pos = sum(1 for p in pairs if p[5])
print(f"Total candidate pairs: {len(pairs)}, Total true positives in pool: {total_pos}")

# Grid search / tuning
best_f05 = 0
best_config = None

for min_nsort in [78, 80, 82, 85]:
    for min_apart in [40, 50, 60]:
        for min_nset in [85, 88, 90, 92]:
            for min_asort in [65, 70, 75]:
                tp = 0
                fp = 0
                for n_sort, n_set, a_part, a_sort, has_addr, is_true in pairs:
                    match = False
                    if n_sort >= min_nsort and (a_part >= min_apart or not has_addr):
                        match = True
                    elif n_set >= min_nset and a_sort >= min_asort:
                        match = True
                    elif a_sort >= 82 and a_part >= 80 and n_sort >= 65:
                        match = True
                        
                    if match:
                        if is_true: tp += 1
                        else: fp += 1
                        
                fn = total_pos - tp
                prec = tp / max(tp + fp, 1)
                rec = tp / max(tp + fn, 1)
                f05 = (1 + 0.25) * prec * rec / max(0.25 * prec + rec, 1e-6)
                f1 = 2 * prec * rec / max(prec + rec, 1e-6)
                if f05 > best_f05 and prec >= 0.93:
                    best_f05 = f05
                    best_config = (min_nsort, min_apart, min_nset, min_asort, prec, rec, f1, f05, tp, fp, fn)

print("\n--- OPTIMAL CONFIGURATION ---")
print(f"Config (min_nsort={best_config[0]}, min_apart={best_config[1]}, min_nset={best_config[2]}, min_asort={best_config[3]}):")
print(f"  Precision: {best_config[4]:.4f}")
print(f"  Recall:    {best_config[5]:.4f}")
print(f"  F1:        {best_config[6]:.4f}")
print(f"  F0.5:      {best_config[7]:.4f}")
print(f"  TP: {best_config[8]}, FP: {best_config[9]}, FN: {best_config[10]}")
