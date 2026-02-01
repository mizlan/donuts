"""Matching algorithm for generating optimal donut pairings."""

from collections import Counter
from itertools import combinations
from typing import Iterable

import networkx as nx

from .history import Person


def get_past_meeting_counts(
    history: list[tuple[int, int]],
) -> Iterable[tuple[tuple[int, int], int]]:
    """Count the number of past meetings for each pair of people.

    Args:
        history: List of past meeting pairs as (id1, id2)

    Returns:
        ItemsView of normalized pairs and their meeting counts
    """
    normalized = [tuple(sorted(pair)) for pair in history]
    return Counter(normalized).items()


def make_assignment(
    registry: dict[int, Person], history: list[tuple[int, int]]
) -> list[tuple[Person, Person]]:
    """Generate optimal pairings using maximum weight matching algorithm.

    Uses a graph-based approach where edge weights are negated meeting counts,
    ensuring people who have met fewer times are prioritized.

    Args:
        registry: Dictionary mapping person IDs to Person objects
        history: List of past meeting pairs as (id1, id2)

    Returns:
        List of person pair tuples (person1, person2)
    """
    # Create graph with all possible edges
    graph = nx.Graph()
    graph.add_nodes_from(registry.keys())

    # Add all possible edges with default weight 0
    for person1_id, person2_id in combinations(graph.nodes, 2):
        graph.add_edge(person1_id, person2_id, weight=0)

    # Update weights based on past meetings (negate to use max_weight_matching)
    for pair, count in get_past_meeting_counts(history):
        graph.add_edge(pair[0], pair[1], weight=-count)

    # Find maximum weight matching
    matching = nx.max_weight_matching(graph, maxcardinality=True)

    # Convert IDs back to Person objects
    donut_pairs = [(registry[id1], registry[id2]) for id1, id2 in matching]

    return donut_pairs
