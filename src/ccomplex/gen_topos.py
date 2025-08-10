import os
import random
import pandas as pd
import math
import numpy as np
# Compatibility workarounds for NumPy 2.0
np.float_ = np.float64
np.Inf = np.inf
import networkx as nx
import matplotlib.pyplot as plt

# === Graph and Load/Profile Generators ===
def generate_random_graph(num_nodes):
    """Generate random topology mimicking IEEE34: spanning tree + extra edges"""
    length_samples = [100,125,150,175,200,225,250,275,300,325,350,375,400,425,450,475,500,525,550,575,650,700,750,800,825,1000]
    config_options = list(range(1,13))
    nodes = list(range(1, num_nodes+1))
    random.shuffle(nodes)
    edges = []
    # spanning tree
    for i in range(num_nodes-1):
        a, b = nodes[i], nodes[i+1]
        edges.append((a, b, random.choice(length_samples), random.choice(config_options)))
    # extra edges
    extra_edges = int(num_nodes * 1.5)
    while len(edges) < num_nodes - 1 + extra_edges:
        a, b = random.sample(nodes, 2)
        if not any((u==a and v==b) or (u==b and v==a) for u,v,_,_ in edges):
            edges.append((a, b, random.choice(length_samples), random.choice(config_options)))
    return pd.DataFrame(edges, columns=["Node A","Node B","Length (ft.)","Config."])


def generate_random_loads(num_nodes, periods=96):
    """Generate simplified loads uniformly random between -4 and 4 for each node/time"""
    data = {"Bus_no": list(range(1, num_nodes+1))}
    for t in range(periods):
        data[str(15*(t+1))] = [round(random.uniform(-4,4), 6) for _ in range(num_nodes)]
    return pd.DataFrame(data)

# === Plot and Save Functions ===
def save_graph_image(df, filepath):
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(int(row['Node A']), int(row['Node B']))
    pos = nx.spring_layout(G)
    plt.figure(figsize=(6,6))
    nx.draw(G, pos, node_size=50, with_labels=False)
    plt.axis('off')
    plt.tight_layout(pad=0.5)
    plt.savefig(filepath)
    plt.close()

# === Main Batch Generation ===
if __name__ == '__main__':
    os.makedirs('topo', exist_ok=True)
    for num_nodes in range(10, 2501, 10):
        folder = f'topo/topo_{num_nodes}'
        os.makedirs(folder, exist_ok=True)
        # Generate topology
        df_edges = generate_random_graph(num_nodes)
        edges_csv = os.path.join(folder, 'links.csv')
        df_edges.to_csv(edges_csv, index=False)
        # Generate loads
        df_loads = generate_random_loads(num_nodes)
        loads_csv = os.path.join(folder, 'loads.csv')
        df_loads.to_csv(loads_csv, index=False)
        # Save topology image
        img_path = os.path.join(folder, 'topology.png')
        save_graph_image(df_edges, img_path)
        print(f'Generated topo {num_nodes}: edges->{edges_csv}, loads->{loads_csv}, image->{img_path}')
