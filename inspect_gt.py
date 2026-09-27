import sys
import pandas as pd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("Loading data...")
df_s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t', nrows=100000).set_index('entity_id')
df_s3 = pd.read_csv('dataset/train/train_source3.tsv', sep='\t', nrows=100000).set_index('entity_id')
gt = pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t', nrows=20000)

print(f"Loaded {len(df_s1)} S1, {len(df_s3)} S3, {len(gt)} GT")

multi_found = 0
for r in gt.itertuples(index=False):
    s1_id = r.source1_entity_id
    m_ids = str(r.matched_entity_ids)
    if s1_id in df_s1.index and m_ids != 'nan':
        s1_row = df_s1.loc[s1_id]
        s3_ids = [x.strip() for x in m_ids.split(',') if x.strip().startswith('S3-') and x.strip() in df_s3.index]
        if len(s3_ids) >= 2:
            print(f"\n=======================================================")
            print(f"S1 Entity ({s1_id}):")
            print(f"  Name: {s1_row['business_name']}")
            print(f"  Addr: {s1_row['business_address']}")
            print(f"  Matches ({len(s3_ids)} S3 records):")
            for mid in s3_ids:
                row = df_s3.loc[mid]
                print(f"   [{mid}] Name: {row['business_name']} | Addr: {row['business_address']}")
            multi_found += 1
            if multi_found >= 5:
                break
