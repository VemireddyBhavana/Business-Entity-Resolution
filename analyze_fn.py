import sys, time
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

# Load a subset of train S1
df_s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t', nrows=5000)
s1_ids = set(df_s1['entity_id'])

# Load GT
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
rec_s3 = {}
for r in df_s3.itertuples(index=False):
    eid = r.entity_id
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    rec_s3[eid] = (c_name, c_addr, r.business_name, r.business_address)
    for t in clean_name_tokens(r.business_name):
        if len(t) >= 3:
            idx_s3_tok[t].append(eid)

# Analyze False Negatives
missed_in_blocking = 0
missed_in_scoring = 0
scoring_examples = []
blocking_examples = []

for r in df_s1.itertuples(index=False):
    eid = r.entity_id
    true_s3 = set(x for x in gt_map.get(eid, set()) if x.startswith('S3-') and x in rec_s3)
    if not true_s3: continue
    
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    tokens = clean_name_tokens(r.business_name)
    
    cands = set()
    # Test our original blocking vs all tokens
    for t in tokens[:2]:
        if len(t) >= 3 and t in idx_s3_tok:
            cands.update(idx_s3_tok[t][:25])
            
    for true_id in true_s3:
        if true_id not in cands:
            missed_in_blocking += 1
            if len(blocking_examples) < 5:
                blocking_examples.append((r.business_name, r.business_address, rec_s3[true_id][2], rec_s3[true_id][3], tokens))
        else:
            t_name, t_addr, raw_name, raw_addr = rec_s3[true_id]
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
                
            if not is_match:
                missed_in_scoring += 1
                if len(scoring_examples) < 5:
                    scoring_examples.append((r.business_name, raw_name, n_sort, n_set, a_part, a_sort, r.business_address, raw_addr))

print(f"Total True S3 evaluated: {missed_in_blocking + missed_in_scoring + 930}")
print(f"Missed in BLOCKING (never made it to candidates): {missed_in_blocking}")
print(f"Missed in SCORING (was in candidates, but threshold rejected): {missed_in_scoring}")

print("\n--- MISSED IN BLOCKING SAMPLES ---")
for ex in blocking_examples:
    print(f"S1: {ex[0]} | Addr: {ex[1]}")
    print(f"S3: {ex[2]} | Addr: {ex[3]}")
    print(f"S1 Tokens: {ex[4]}\n")

print("\n--- MISSED IN SCORING SAMPLES ---")
for ex in scoring_examples:
    print(f"S1: {ex[0]} vs S3: {ex[1]}")
    print(f"Scores: n_sort={ex[2]}, n_set={ex[3]}, a_part={ex[4]}, a_sort={ex[5]}")
    print(f"Addr1: {ex[6]} vs Addr2: {ex[7]}\n")
