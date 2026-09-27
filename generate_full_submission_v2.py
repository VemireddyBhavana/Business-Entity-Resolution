"""
High-Performance Business Entity Resolution - Full Test Pipeline v2
Key improvements over v1:
1. Additional blocking key: "nospace root" for domain-name S3 entries (e.g. georgesaul.com)
2. Address-number + street-word blocking key for address-led matches
3. All name tokens indexed (not just first 2) but capped per token
4. Tuned scoring rules from grid search (nsort>=85, nset>=85, a_sort>=65)
5. Extra rule: high address similarity with partial name overlap
"""

import os, re, gc, time, csv, sys
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = "output"
TEMP_DIR = "output/temp_v2"
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

def get_nospace_root(text):
    """Collapse name to pure alphabetic root for domain-name matching."""
    if not text or pd.isna(text): return ''
    t = str(text).lower()
    # Strip domain extensions and web prefixes
    t = re.sub(r'\b(com|org|net|in|co|io|www)\b', '', t)
    # Strip legal suffixes
    t = LEGAL_SUFFIXES.sub('', t)
    # Remove all non alpha-numeric
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def extract_addr_num(text):
    if not text or pd.isna(text): return ''
    m = re.findall(r'\b\d+\b', str(text))
    return m[0] if m else ''

def extract_street_word(text):
    """Find the first significant word in an address (not a number, not common street types)."""
    if not text or pd.isna(text): return ''
    STREET_TYPES = {'street','road','avenue','lane','drive','blvd','boulevard','court','place',
                    'way','circle','trail','parkway','highway','sq','rd','ave','st','dr','ct'}
    t = re.sub(r'[^\w\s]', ' ', str(text).lower())
    words = t.split()
    for w in words:
        if len(w) >= 3 and not w.isdigit() and w not in STREET_TYPES:
            return w
    return ''

def clean_str(text):
    if not text or pd.isna(text): return ''
    return ' '.join(re.sub(r'[^\w\s]',' ', str(text).lower()).split())

def is_match(c_name, t_name, c_addr, t_addr):
    """Optimized multi-rule matching (tuned from grid search on train)."""
    n_sort = fuzz.token_sort_ratio(c_name, t_name)
    n_set  = fuzz.token_set_ratio(c_name, t_name)
    a_part = fuzz.partial_ratio(c_addr, t_addr)
    a_sort = fuzz.token_sort_ratio(c_addr, t_addr)

    # Rule 1 (tuned): High name sort + reasonable address
    if n_sort >= 85 and (a_part >= 60 or not c_addr or not t_addr):
        return True
    # Rule 2: High name set similarity + good address sort
    if n_set >= 85 and a_sort >= 65:
        return True
    # Rule 3: High address match with substantial name overlap (rebranded entities)
    if a_sort >= 82 and a_part >= 80 and (n_sort >= 60 or n_set >= 70):
        return True
    # Rule 4: Very high address + any name overlap (address-led match)
    if a_sort >= 88 and a_part >= 88 and (n_sort >= 50 or n_set >= 60):
        return True

    return False

def build_indices(df_source):
    idx_token = defaultdict(list)      # token -> [eid, ...]
    idx_nospace = defaultdict(list)    # nospace_root -> [eid, ...]
    idx_addr = defaultdict(list)       # (addr_num, street_word) -> [eid, ...]
    records = {}                        # eid -> (clean_name, clean_addr)

    for r in df_source.itertuples(index=False):
        eid = r.entity_id
        c_name = clean_str(r.business_name)
        c_addr = clean_str(r.business_address)
        records[eid] = (c_name, c_addr)

        # 1. Name tokens
        tokens = clean_name_tokens(r.business_name)
        for t in tokens:
            if len(t) >= 3:
                idx_token[t].append(eid)

        # 2. Nospace root (catches domain-name S3 records)
        root = get_nospace_root(r.business_name)
        if len(root) >= 5:
            # Index multiple substrings (first 8, first 12)
            idx_nospace[root[:8]].append(eid)

        # 3. Address (num + street_word)
        num = extract_addr_num(r.business_address)
        s_word = extract_street_word(r.business_address)
        if num and s_word and len(s_word) >= 3:
            idx_addr[(num, s_word)].append(eid)

    return idx_token, idx_nospace, idx_addr, records


def process_country(country_name, max_cands_per_key=40):
    print("\n" + "=" * 65)
    print(f"  PROCESSING COUNTRY: {country_name.upper()}")
    print("=" * 65)
    t_start = time.time()

    # Load S2
    print(f"[{country_name}] Loading S2...")
    s2_rows = []
    for chunk in pd.read_csv('dataset/test/test_source2.tsv', sep='\t', chunksize=250000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s2_rows.append(m[['entity_id','business_name','business_address']])
    df_s2 = pd.concat(s2_rows, ignore_index=True) if s2_rows else pd.DataFrame(columns=['entity_id','business_name','business_address'])
    print(f"[{country_name}] S2: {len(df_s2):,} records")

    # Load S3
    print(f"[{country_name}] Loading S3...")
    s3_rows = []
    for chunk in pd.read_csv('dataset/test/test_source3.tsv', sep='\t', chunksize=250000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s3_rows.append(m[['entity_id','business_name','business_address']])
    df_s3 = pd.concat(s3_rows, ignore_index=True) if s3_rows else pd.DataFrame(columns=['entity_id','business_name','business_address'])
    print(f"[{country_name}] S3: {len(df_s3):,} records")

    # Build indices
    print(f"[{country_name}] Building indices...")
    idx_s2_tok, idx_s2_ns, idx_s2_addr, rec_s2 = build_indices(df_s2)
    idx_s3_tok, idx_s3_ns, idx_s3_addr, rec_s3 = build_indices(df_s3)
    print(f"[{country_name}] S2 index: {len(idx_s2_tok):,} tokens, {len(idx_s2_ns):,} roots, {len(idx_s2_addr):,} addr keys")
    print(f"[{country_name}] S3 index: {len(idx_s3_tok):,} tokens, {len(idx_s3_ns):,} roots, {len(idx_s3_addr):,} addr keys")

    del df_s2, df_s3
    gc.collect()

    # Load S1
    print(f"[{country_name}] Loading S1...")
    s1_rows = []
    for chunk in pd.read_csv('dataset/test/test_source1.tsv', sep='\t', chunksize=200000):
        m = chunk[chunk['country'] == country_name]
        if not m.empty:
            s1_rows.append(m[['entity_id','business_name','business_address']])
    df_s1 = pd.concat(s1_rows, ignore_index=True) if s1_rows else pd.DataFrame(columns=['entity_id','business_name','business_address'])
    total_s1 = len(df_s1)
    print(f"[{country_name}] S1: {total_s1:,} records")

    out_c_file = f"{TEMP_DIR}/cands_{country_name}.tsv"
    out_m_file = f"{TEMP_DIR}/matches_{country_name}.tsv"

    t_match = time.time()
    match_count = 0

    with open(out_c_file, 'w', encoding='utf-8', newline='') as f_c, \
         open(out_m_file, 'w', encoding='utf-8', newline='') as f_m:
        w_c = csv.writer(f_c, delimiter='\t')
        w_m = csv.writer(f_m, delimiter='\t')

        for idx, r in enumerate(df_s1.itertuples(index=False), start=1):
            eid = r.entity_id
            c_name = clean_str(r.business_name)
            c_addr = clean_str(r.business_address)
            tokens = clean_name_tokens(r.business_name)
            s1_root = get_nospace_root(r.business_name)
            num = extract_addr_num(r.business_address)
            s_word = extract_street_word(r.business_address)

            all_cands = set()

            for src_tok, src_ns, src_addr, rec in [
                (idx_s2_tok, idx_s2_ns, idx_s2_addr, rec_s2),
                (idx_s3_tok, idx_s3_ns, idx_s3_addr, rec_s3)
            ]:
                cands = set()
                # 1. Name tokens
                for t in tokens:
                    if len(t) >= 3 and t in src_tok:
                        lst = src_tok[t]
                        cands.update(lst[:max_cands_per_key] if len(lst) > max_cands_per_key else lst)

                # 2. Nospace root (domain-name matching)
                if s1_root and len(s1_root) >= 5:
                    root_key = s1_root[:8]
                    if root_key in src_ns:
                        cands.update(src_ns[root_key])

                # 3. Address blocking
                if num and s_word and len(s_word) >= 3:
                    k = (num, s_word)
                    if k in src_addr:
                        cands.update(src_addr[k])

                all_cands.update(cands)

            matched_ids = []
            for cid in all_cands:
                t_name, t_addr = (rec_s2 if cid.startswith('S2-') else rec_s3)[cid]
                if is_match(c_name, t_name, c_addr, t_addr):
                    matched_ids.append(cid)

            # Ensure matches ⊆ candidates
            cand_set = set(all_cands)
            for m in matched_ids:
                if m not in cand_set:
                    all_cands.add(m)

            if matched_ids:
                match_count += 1

            all_cands_list = sorted(all_cands)
            w_c.writerow([eid, ','.join(all_cands_list)])
            w_m.writerow([eid, ','.join(matched_ids)])

            if idx % 50000 == 0 or idx == total_s1:
                el = time.time() - t_match
                rate = idx / max(el, 1)
                eta = (total_s1 - idx) / max(rate, 1)
                print(f"[{country_name}] {idx:,}/{total_s1:,} ({idx/total_s1*100:.1f}%) | {rate:.0f}/s | ETA: {eta/60:.1f}min | Matches: {match_count:,}", flush=True)

    del df_s1, idx_s2_tok, idx_s2_ns, idx_s2_addr, rec_s2
    del idx_s3_tok, idx_s3_ns, idx_s3_addr, rec_s3
    gc.collect()
    print(f"[{country_name}] Done in {(time.time()-t_start)/60:.1f}min. Matches: {match_count:,}")


def main():
    print("=" * 65)
    print("  HIGH-PERFORMANCE ENTITY RESOLUTION PIPELINE v2")
    print("  Improvements: nospace-root blocking + addr blocking + tuned rules")
    print("=" * 65)
    t_total = time.time()

    # France was already processed in a previous run (temp_v2/cands_France.tsv exists with data)
    # Skip France and only process US and India
    france_done = os.path.exists(f"{TEMP_DIR}/matches_France.tsv") and \
                  os.path.getsize(f"{TEMP_DIR}/matches_France.tsv") > 0
    if france_done:
        print(f"[SKIP] France already processed ({os.path.getsize(TEMP_DIR+'/matches_France.tsv'):,} bytes). Skipping.")
    else:
        process_country('France')

    for country in ['US', 'India']:
        done = os.path.exists(f"{TEMP_DIR}/matches_{country}.tsv") and \
               os.path.getsize(f"{TEMP_DIR}/matches_{country}.tsv") > 0
        if done:
            print(f"[SKIP] {country} already processed ({os.path.getsize(TEMP_DIR+'/matches_'+country+'.tsv'):,} bytes). Skipping.")
        else:
            process_country(country)

    print("\n" + "=" * 65)
    print("  MERGING OUTPUTS IN SOURCE 1 TEST ORDER")
    print("=" * 65)

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

    matching_file = f"{OUTPUT_DIR}/matching_results.tsv"
    candidate_file = f"{OUTPUT_DIR}/candidate_pairs.tsv"

    print("Writing final ordered submission files...")
    has_match_count = 0
    total_written = 0

    with open('dataset/test/test_source1.tsv', 'r', encoding='utf-8') as f_in, \
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

    print(f"\n[OK] Wrote {matching_file}")
    print(f"[OK] Wrote {candidate_file}")
    print(f"  Total entities   : {total_written:,}")
    print(f"  With matches     : {has_match_count:,} ({has_match_count/max(total_written,1)*100:.1f}%)")
    print(f"  Total time       : {(time.time()-t_total)/60:.1f} min")


if __name__ == "__main__":
    main()
