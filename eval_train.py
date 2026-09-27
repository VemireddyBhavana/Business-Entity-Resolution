import sys, time
import pandas as pd
from rapidfuzz import fuzz
from collections import defaultdict
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("Evaluating baseline on Train dataset...")
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

def extract_addr_num(text):
    if not text or pd.isna(text): return ''
    m = re.findall(r'\b\d+\b', str(text))
    return m[0] if m else ''

def clean_str(text):
    if not text or pd.isna(text): return ''
    return ' '.join(re.sub(r'[^\w\s]',' ', str(text).lower()).split())

# Load a subset of train S1 (first 5,000 entities)
print("Loading train S1...")
df_s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t', nrows=5000)
s1_ids = set(df_s1['entity_id'])

# Load GT for these
print("Loading GT...")
gt_map = {}
for chunk in pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t', chunksize=100000):
    m = chunk[chunk['source1_entity_id'].isin(s1_ids)]
    for r in m.itertuples(index=False):
        m_str = str(r.matched_entity_ids)
        if m_str != 'nan' and m_str:
            gt_map[r.source1_entity_id] = set(x.strip() for x in m_str.split(',') if x.strip())
        else:
            gt_map[r.source1_entity_id] = set()

# Load S3
print("Loading train S3...")
all_target_s3 = set()
for s in gt_map.values():
    all_target_s3.update(x for x in s if x.startswith('S3-'))

df_s3 = []
for chunk in pd.read_csv('dataset/train/train_source3.tsv', sep='\t', chunksize=200000):
    # keep rows that are either in GT or first 50k
    m = chunk[chunk['entity_id'].isin(all_target_s3) | (chunk.index < 50000)]
    df_s3.append(m)
    if len(df_s3) > 5: break
df_s3 = pd.concat(df_s3, ignore_index=True)
print(f"Loaded S3: {len(df_s3)} rows, target in S3: {len(all_target_s3.intersection(set(df_s3['entity_id'])))}/{len(all_target_s3)}")

# Build index for S3
idx_s3_tok = defaultdict(list)
rec_s3 = {}
for r in df_s3.itertuples(index=False):
    eid = r.entity_id
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    rec_s3[eid] = (c_name, c_addr)
    for t in clean_name_tokens(r.business_name)[:2]:
        if len(t) >= 3:
            idx_s3_tok[t].append(eid)

# Now test matching on S3
tp = 0
fp = 0
fn = 0

for r in df_s1.itertuples(index=False):
    eid = r.entity_id
    true_s3 = set(x for x in gt_map.get(eid, set()) if x.startswith('S3-') and x in rec_s3)
    if not true_s3: continue
    
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    tokens = clean_name_tokens(r.business_name)
    
    cands = set()
    for t in tokens[:2]:
        if len(t) >= 3 and t in idx_s3_tok:
            cands.update(idx_s3_tok[t][:25])
            
    matched = set()
    for cid in cands:
        t_name, t_addr = rec_s3[cid]
        n_sort = fuzz.token_sort_ratio(c_name, t_name)
        n_set  = fuzz.token_set_ratio(c_name, t_name)
        a_part = fuzz.partial_ratio(c_addr, t_addr)
        a_sort = fuzz.token_sort_ratio(c_addr, t_addr)

        is_match = False
        if n_sort >= 85 and (a_part >= 55 or a_sort >= 50 or not c_addr or not t_addr):
            is_match = True
        elif n_sort >= 72 and a_sort >= 60:
            is_match = True
        elif n_set >= 92 and a_part >= 65:
            is_match = True
            
        if is_match:
            matched.add(cid)
            
    cur_tp = len(matched.intersection(true_s3))
    cur_fp = len(matched - true_s3)
    cur_fn = len(true_s3 - matched)
    tp += cur_tp
    fp += cur_fp
    fn += cur_fn

prec = tp / max(tp + fp, 1)
rec = tp / max(tp + fn, 1)
f1 = 2 * prec * rec / max(prec + rec, 1e-6)
f05 = (1 + 0.5**2) * prec * rec / max(0.5**2 * prec + rec, 1e-6)
print(f"Results on Train S3 subset:")
print(f"  TP: {tp}, FP: {fp}, FN: {fn}")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1-Score:  {f1:.4f}")
print(f"  F0.5-Score:{f05:.4f}")
