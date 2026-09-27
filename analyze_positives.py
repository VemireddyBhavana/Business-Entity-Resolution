import numpy as np

# We can analyze the pairs directly
from tune_rules import pairs

pos_pairs = [p for p in pairs if p[5]] # is_true == True
neg_pairs = [p for p in pairs if not p[5]]

print(f"Total Positives: {len(pos_pairs)}, Total Negatives: {len(neg_pairs)}")

pos_nsort = [p[0] for p in pos_pairs]
pos_nset  = [p[1] for p in pos_pairs]
pos_apart = [p[2] for p in pos_pairs]
pos_asort = [p[3] for p in pos_pairs]

for name, arr in [('Name Sort', pos_nsort), ('Name Set', pos_nset), ('Addr Part', pos_apart), ('Addr Sort', pos_asort)]:
    print(f"{name:10} | Mean: {np.mean(arr):.1f} | 10th%: {np.percentile(arr, 10):.1f} | 25th%: {np.percentile(arr, 25):.1f} | 50th%: {np.percentile(arr, 50):.1f} | 90th%: {np.percentile(arr, 90):.1f}")
