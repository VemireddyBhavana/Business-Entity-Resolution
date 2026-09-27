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
    rec_s3[eid] = (c_name, c_addr, r.business_name, r.business_address)
    for t in clean_name_tokens(r.business_name):
        if len(t) >= 3:
            idx_s3_tok[t].append(eid)
    num, s_word = extract_addr_features(r.business_address)
    if num and s_word:
        idx_s3_addr[(num, s_word)].append(eid)

missed = []
for r in df_s1.itertuples(index=False):
    eid = r.entity_id
    true_s3 = set(x for x in gt_map.get(eid, set()) if x.startswith('S3-') and x in rec_s3)
    if not true_s3: continue
    
    tokens = clean_name_tokens(r.business_name)
    num, s_word = extract_addr_features(r.business_address)
    
    cands = set()
    for t in tokens:
        if len(t) >= 3 and t in idx_s3_tok:
            cands.update(idx_s3_tok[t][:60])
    if num and s_word and (num, s_word) in idx_s3_addr:
        cands.update(idx_s3_addr[(num, s_word)][:50])
        
    for tid in true_s3:
        if tid not in cands:
            missed.append((r.business_name, r.business_address, rec_s3[tid][2], rec_s3[tid][3], tokens))

print(f"Total Missed from candidate pool: {len(missed)}")
print("\n--- SAMPLE MISSED MATCHES ---")
for ex in missed[:10]:
    print(f"S1: {ex[0]}  ||  Addr: {ex[1]}")
    print(f"S3: {ex[2]}  ||  Addr: {ex[3]}")
    print(f"S1 Tokens: {ex[4]}")
    print("-" * 50)
