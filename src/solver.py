import networkx as nx
from collections import Counter
from itertools import combinations


def get_past_meeting_counts(history):
    normalized = [tuple(sorted(pair)) for pair in history]
    return Counter(normalized).items()


def make_assignment(registry, history):
    G = nx.Graph()
    G.add_nodes_from(registry.keys())

    # add default edges with weight 0
    for u, v in combinations(G.nodes, 2):
        G.add_edge(u, v, weight=0)

    for pair, count in get_past_meeting_counts(history):
        # negate count to get minimum weight match
        G.add_edge(pair[0], pair[1], weight=-count)

    graph_matching = nx.max_weight_matching(G, maxcardinality=True)

    donut_pairs = [(registry[id1], registry[id2]) for id1, id2 in graph_matching]

    return donut_pairs
