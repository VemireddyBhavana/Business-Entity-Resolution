import pandas as pd
from .features import soundex

def generate_multi_blocking_keys(df):
    """Adds multi-strategy blocking keys to a pre-cleaned dataframe."""
    df['block_key1'] = df['clean_business_name'].str[:3]
    df['block_key2'] = df['country'].astype(str) + "_" + df['clean_business_name'].apply(
        lambda n: soundex(n.split()[0] if n.split() else '')
    )
    return df

def find_candidate_pairs(b1, lookup_groups_k1, lookup_groups_k2):
    """Finds candidate entity matches using union of multiple blocking keys."""
    k1 = b1.get('block_key1')
    k2 = b1.get('block_key2')
    candidates = []
    
    if k1 in lookup_groups_k1.groups:
        candidates.append(lookup_groups_k1.get_group(k1))
    if k2 in lookup_groups_k2.groups:
        candidates.append(lookup_groups_k2.get_group(k2))
        
    if candidates:
        return pd.concat(candidates).drop_duplicates(subset=['entity_id'])
    return pd.DataFrame()
