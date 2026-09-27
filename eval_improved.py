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

def extract_addr_features(text):
    if not text or pd.isna(text): return '', ''
    t = re.sub(r'[^\w\s]', ' ', str(text).lower())
    words = t.split()
    nums = [w for w in words if w.isdigit()]
    num = nums[0] if nums else ''
    # Find word right after num, or first substantial word
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

# Load a subset of train S1
print("Loading data...")
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

print(f"Building advanced indices on S3 ({len(df_s3)} records)...")
idx_s3_tok = defaultdict(list)
idx_s3_addr = defaultdict(list)
rec_s3 = {}

for r in df_s3.itertuples(index=False):
    eid = r.entity_id
    c_name = clean_str(r.business_name)
    c_addr = clean_str(r.business_address)
    rec_s3[eid] = (c_name, c_addr)
    
    tokens = clean_name_tokens(r.business_name)
    for t in tokens:
        if len(t) >= 3:
            idx_s3_tok[t].append(eid)
            
    num, s_word = extract_addr_features(r.business_address)
    if num and s_word:
        idx_s3_addr[(num, s_word)].append(eid)

print("Evaluating improved matching pipeline...")
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
    num, s_word = extract_addr_features(r.business_address)
    
    cands = set()
    # 1. Name tokens with smart truncation (only truncate if huge)
    for t in tokens:
        if len(t) >= 3 and t in idx_s3_tok:
            cand_list = idx_s3_tok[t]
            if len(cand_list) <= 100:
                cands.update(cand_list)
            else:
                cands.update(cand_list[:50])
                
    # 2. Address index (num + street word)
    if num and s_word and (num, s_word) in idx_s3_addr:
        cands.update(idx_s3_addr[(num, s_word)][:50])
        
    matched = set()
    for cid in cands:
        t_name, t_addr = rec_s3[cid]
        n_sort = fuzz.token_sort_ratio(c_name, t_name)
        n_set  = fuzz.token_set_ratio(c_name, t_name)
        a_part = fuzz.partial_ratio(c_addr, t_addr)
        a_sort = fuzz.token_sort_ratio(c_addr, t_addr)

        is_match = False
        # Rule 1: High name similarity with reasonable address
        if n_sort >= 80 and (a_part >= 50 or a_sort >= 45 or not c_addr or not t_addr):
            is_match = True
        elif n_set >= 88 and (a_part >= 55 or a_sort >= 50):
            is_match = True
        # Rule 2: High address match with substantial name overlap
        elif a_sort >= 75 and (n_sort >= 60 or n_set >= 70):
            is_match = True
        # Rule 3: Exact address match (e.g. rebranded or altered name)
        elif a_sort >= 88 and a_part >= 90 and (n_sort >= 40 or n_set >= 55):
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
print(f"\n==========================================")
print(f"NEW RESULTS ON TRAIN S3 SUBSET:")
print(f"  TP: {tp} (was 930)")
print(f"  FP: {fp} (was 24)")
print(f"  FN: {fn} (was 1086)")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f} (was 0.4613)")
print(f"  F1-Score:  {f1:.4f} (was 0.6263)")
print(f"  F0.5-Score:{f05:.4f}")
print(f"==========================================")
