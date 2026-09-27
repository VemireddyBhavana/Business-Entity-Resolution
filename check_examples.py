import pandas as pd

# Print training data sample with matching examples
train_s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t')
train_s3 = pd.read_csv('dataset/train/train_source3.tsv', sep='\t')
gt = pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t', nrows=200)

print("Train S1 sample:")
print(train_s1.head(3).to_string())
print()
print("Train S3 sample:")
print(train_s3.head(3).to_string())
print()

# For a known match
s1_dict = {row['entity_id']: row for _, row in train_s1.iterrows()}
s3_dict = {row['entity_id']: row for _, row in train_s3.iterrows()}

count = 0
for _, row in gt.iterrows():
    s1_id = row['source1_entity_id']
    if s1_id not in s1_dict:
        continue
    matched = str(row['matched_entity_ids'])
    if matched == 'nan':
        continue
    for mid in matched.split(','):
        mid = mid.strip()
        if mid.startswith('S3-') and mid in s3_dict:
            b1 = s1_dict[s1_id]
            b3 = s3_dict[mid]
            print(f"S1: {b1['business_name']} | {b1['business_address']} | {b1['country']}")
            print(f"S3: {b3['business_name']} | {b3['business_address']} | {b3['country']}")
            print()
            count += 1
            if count >= 8:
                break
    if count >= 8:
        break
