"""
Candidate Graph Linking & Transitive Closure Module.
Uses NetworkX to build connected entity graphs and resolve transitive clusters across disparate sources.
"""

import networkx as nx
import pandas as pd

def build_entity_graph(matched_pairs):
    """
    Constructs an undirected graph where nodes are record IDs and edges represent matched pairs.
    matched_pairs: list of tuples (id_a, id_b) or DataFrame with columns ['id_a', 'id_b']
    """
    G = nx.Graph()
    
    if isinstance(matched_pairs, pd.DataFrame):
        for _, row in matched_pairs.iterrows():
            G.add_edge(row.iloc[0], row.iloc[1])
    else:
        for u, v in matched_pairs:
            G.add_edge(u, v)
            
    return G

def resolve_transitive_clusters(G):
    """
    Extracts connected components and assigns each record to a unified Canonical Entity ID.
    Returns: dict mapping record_id -> canonical_cluster_id
    """
    mapping = {}
    for cluster_id, component in enumerate(nx.connected_components(G), start=1):
        c_id = f"ENTITY_{cluster_id:06d}"
        for record_id in component:
            mapping[record_id] = c_id
    return mapping

def generate_cluster_dataframe(mapping):
    """Converts cluster mapping dictionary into a clean DataFrame."""
    df = pd.DataFrame(list(mapping.items()), columns=['entity_id', 'cluster_id'])
    return df.sort_values(by=['cluster_id', 'entity_id']).reset_index(drop=True)
