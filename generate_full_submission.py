"""
High-Performance Business Entity Resolution - Full Test Pipeline
Resolves all 1,732,544 Source 1 entities against Source 2 and Source 3.
Processes country-by-country (France, US, India) to maintain < 1.0 GB RAM footprint.
Streams results directly to disk.
Conforms strictly to Unstop competition rules.
"""

import os, re, gc, time, csv, sys
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = "output"
TEMP_DIR = "output/temp_country"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

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

def build_inverted_index(df_source):
    idx_token = defaultdict(list)
    idx_num_prefix = defaultdict(list)
    records = {}

    for r in df_source.itertuples(index=False):
        eid = r.entity_id
        name = str(r.business_name)
        addr = str(r.business_address)
        c_name = clean_str(name)
        c_addr = clean_str(addr)
        records[eid] = (c_name, c_addr)

        tokens = clean_name_tokens(name)
        num = extract_addr_num(addr)

        if tokens:
            t0 = tokens[0]
            if len(t0) >= 3:
                idx_token[t0].append(eid)
            if len(tokens) > 1 and len(tokens[1]) >= 3:
                idx_token[tokens[1]].append(eid)

        if num and tokens and len(tokens[0]) >= 2:
            idx_num_prefix[(num, tokens[0][:3])].append(eid)

    return idx_token, idx_num_prefix, records

def process_country(country_name, max_candidates_per_source=25):
    print("\n" + "=" * 65)
    print(f"  PROCESSING COUNTRY: {country_name.upper()}")
    print("=" * 65)
    t_start = time.time()

    # 1. Load S2
    print(f"[{country_name}] Loading test Source 2...")
    t0 = time.time()
    s2_rows = []
    for chunk in pd.read_csv('dataset/test/test_source2.tsv', sep='\t', chunksize=250000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s2_rows.append(m[['entity_id', 'business_name', 'business_address']])
    df_s2 = pd.concat(s2_rows, ignore_index=True)
    print(f"[{country_name}] S2 loaded: {len(df_s2):,} records in {time.time()-t0:.1f}s")

    # 2. Load S3
    print(f"[{country_name}] Loading test Source 3...")
    t0 = time.time()
    s3_rows = []
    for chunk in pd.read_csv('dataset/test/test_source3.tsv', sep='\t', chunksize=250000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s3_rows.append(m[['entity_id', 'business_name', 'business_address']])
    df_s3 = pd.concat(s3_rows, ignore_index=True)
    print(f"[{country_name}] S3 loaded: {len(df_s3):,} records in {time.time()-t0:.1f}s")

    # 3. Build Indices
    print(f"[{country_name}] Building inverted indices...")
    t0 = time.time()
    idx_s2_tok, idx_s2_num, rec_s2 = build_inverted_index(df_s2)
    print(f"[{country_name}] S2 index built ({len(idx_s2_tok):,} tokens) in {time.time()-t0:.1f}s")

    t0 = time.time()
    idx_s3_tok, idx_s3_num, rec_s3 = build_inverted_index(df_s3)
    print(f"[{country_name}] S3 index built ({len(idx_s3_tok):,} tokens) in {time.time()-t0:.1f}s")

    del df_s2, df_s3
    gc.collect()

    # 4. Load S1 for this country
    print(f"[{country_name}] Loading test Source 1...")
    t0 = time.time()
    s1_rows = []
    for chunk in pd.read_csv('dataset/test/test_source1.tsv', sep='\t', chunksize=200000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s1_rows.append(m[['entity_id', 'business_name', 'business_address']])
    df_s1 = pd.concat(s1_rows, ignore_index=True)
    total_s1 = len(df_s1)
    print(f"[{country_name}] S1 loaded: {total_s1:,} records in {time.time()-t0:.1f}s")

    # 5. Matching Loop with streaming write to disk
    out_c_file = f"{TEMP_DIR}/cands_{country_name}.tsv"
    out_m_file = f"{TEMP_DIR}/matches_{country_name}.tsv"
    print(f"[{country_name}] Resolving entities and streaming to {TEMP_DIR}/...")

    t_match = time.time()
    match_count = 0

    with open(out_c_file, 'w', encoding='utf-8', newline='') as f_c, \
         open(out_m_file, 'w', encoding='utf-8', newline='') as f_m:
        w_c = csv.writer(f_c, delimiter='\t')
        w_m = csv.writer(f_m, delimiter='\t')

        for idx, r in enumerate(df_s1.itertuples(index=False), start=1):
            eid = r.entity_id
            name = str(r.business_name)
            addr = str(r.business_address)
            c_name = clean_str(name)
            c_addr = clean_str(addr)
            tokens = clean_name_tokens(name)
            num = extract_addr_num(addr)

            # Retrieve candidates from S2
            cands_s2 = set()
            for t in tokens[:2]:
                if len(t) >= 3 and t in idx_s2_tok:
                    cands_s2.update(idx_s2_tok[t][:max_candidates_per_source])
            if num and tokens and len(tokens[0]) >= 2:
                k = (num, tokens[0][:3])
                if k in idx_s2_num:
                    cands_s2.update(idx_s2_num[k][:max_candidates_per_source])

            # Retrieve candidates from S3
            cands_s3 = set()
            for t in tokens[:2]:
                if len(t) >= 3 and t in idx_s3_tok:
                    cands_s3.update(idx_s3_tok[t][:max_candidates_per_source])
            if num and tokens and len(tokens[0]) >= 2:
                k = (num, tokens[0][:3])
                if k in idx_s3_num:
                    cands_s3.update(idx_s3_num[k][:max_candidates_per_source])

            # Precision-oriented scoring
            all_cands = sorted(cands_s2) + sorted(cands_s3)
            matched_ids = []
            for cid in all_cands:
                t_name, t_addr = rec_s2[cid] if cid.startswith('S2-') else rec_s3[cid]
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
                    matched_ids.append(cid)

            # Ensure matches is a subset of candidates
            cand_set = set(all_cands)
            for m in matched_ids:
                if m not in cand_set:
                    all_cands.append(m)
                    cand_set.add(m)

            if matched_ids:
                match_count += 1

            w_c.writerow([eid, ','.join(all_cands)])
            w_m.writerow([eid, ','.join(matched_ids)])

            if idx % 50000 == 0 or idx == total_s1:
                el = time.time() - t_match
                rate = idx / max(el, 1)
                eta = (total_s1 - idx) / max(rate, 1)
                print(f"[{country_name}] {idx:,}/{total_s1:,} ({idx/total_s1*100:.1f}%) | {rate:.0f}/s | ETA: {eta/60:.1f} min | Matches: {match_count:,}", flush=True)

    del df_s1, idx_s2_tok, idx_s2_num, rec_s2, idx_s3_tok, idx_s3_num, rec_s3
    gc.collect()

    print(f"[{country_name}] Completed in {(time.time()-t_start)/60:.1f} min. Total matches: {match_count:,}")

def main():
    print("=" * 65)
    print("  HIGH-PERFORMANCE BUSINESS ENTITY RESOLUTION PIPELINE")
    print("=" * 65)
    t_total = time.time()

    for country in ['France', 'US', 'India']:
        process_country(country)

    print("\n" + "=" * 65)
    print("  MERGING COUNTRY OUTPUTS (STRICT SOURCE 1 TEST ORDER)")
    print("=" * 65)

    # Load country temp outputs into dictionary mapping eid -> string
    cands_map = {}
    matches_map = {}

    for country in ['France', 'US', 'India']:
        print(f"Loading temp files for {country}...")
        with open(f"{TEMP_DIR}/cands_{country}.tsv", 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                cands_map[parts[0]] = parts[1] if len(parts) > 1 else ''
        with open(f"{TEMP_DIR}/matches_{country}.tsv", 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                matches_map[parts[0]] = parts[1] if len(parts) > 1 else ''

    test_s1_path = 'dataset/test/test_source1.tsv'
    matching_file = f"{OUTPUT_DIR}/matching_results.tsv"
    candidate_file = f"{OUTPUT_DIR}/candidate_pairs.tsv"

    print("Writing final ordered submission files...")
    has_match_count = 0
    total_written = 0

    with open(test_s1_path, 'r', encoding='utf-8') as f_in, \
         open(matching_file, 'w', encoding='utf-8', newline='') as f_m, \
         open(candidate_file, 'w', encoding='utf-8', newline='') as f_c:
        
        reader = csv.reader(f_in, delimiter='\t')
        header = next(reader)
        id_idx = header.index('entity_id')

        m_writer = csv.writer(f_m, delimiter='\t')
        c_writer = csv.writer(f_c, delimiter='\t')

        m_writer.writerow(['source1_entity_id', 'matched_entity_ids'])
        c_writer.writerow(['source1_entity_id', 'candidate_entity_ids'])

        for row in reader:
            if not row: continue
            sid = row[id_idx]
            m_str = matches_map.get(sid, '')
            c_str = cands_map.get(sid, '')

            if m_str:
                has_match_count += 1
            total_written += 1

            m_writer.writerow([sid, m_str])
            c_writer.writerow([sid, c_str])

    print(f"\n[OK] Successfully wrote {matching_file}")
    print(f"[OK] Successfully wrote {candidate_file}")
    print(f"  Total entities written     : {total_written:,}")
    print(f"  Total entities with matches: {has_match_count:,} ({has_match_count/total_written*100:.1f}%)")
    print(f"  Total pipeline time        : {(time.time()-t_total)/60:.1f} minutes")

if __name__ == "__main__":
    main()
