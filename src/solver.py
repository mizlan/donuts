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


def _get_past_meetings_count(
    pair: tuple[int, int], meeting_counts: dict[tuple[int, int], int]
) -> int:
    """Get the number of past meetings for a pair.

    Args:
        pair: Tuple of (id1, id2)
        meeting_counts: Dictionary mapping normalized pairs to meeting counts

    Returns:
        Number of past meetings for this pair
    """
    normalized = tuple(sorted(pair))
    return meeting_counts.get(normalized, 0)


def _form_triplet_groups(
    matching: set[tuple[int, int]],
    unmatched_id: int,
    registry: dict[int, Person],
    meeting_counts: dict[tuple[int, int], int],
) -> list[tuple[Person, ...] | tuple[Person, Person]]:
    """Form groups with a triplet for the unmatched person.

    Finds the pair with the lowest total meeting count (with the unmatched person
    and with each other) and forms a triplet with them. Other pairs remain as pairs.

    Args:
        matching: Set of matched pairs (id1, id2)
        unmatched_id: ID of the person without a match
        registry: Dictionary mapping person IDs to Person objects
        meeting_counts: Dictionary mapping pairs to past meeting counts

    Returns:
        List of person groups (pairs or triplets)
    """
    # Find pair with lowest total meeting count to add the unmatched person
    min_pair = min(
        matching,
        key=lambda pair: (
            _get_past_meetings_count(pair, meeting_counts)
            + _get_past_meetings_count((unmatched_id, pair[0]), meeting_counts)
            + _get_past_meetings_count((unmatched_id, pair[1]), meeting_counts)
        ),
    )

    # Build result with triplet for the chosen pair
    groups: list[tuple[Person, ...] | tuple[Person, Person]] = []
    for pair in matching:
        if pair == min_pair:
            groups.append(
                (registry[pair[0]], registry[pair[1]], registry[unmatched_id])
            )
        else:
            groups.append((registry[pair[0]], registry[pair[1]]))

    return groups


def make_assignment(
    registry: dict[int, Person], history: list[tuple[int, int]]
) -> list[tuple[Person, ...] | tuple[Person, Person]]:
    """Generate optimal pairings using maximum weight matching algorithm.

    Uses a graph-based approach where edge weights are negated meeting counts,
    ensuring people who have met fewer times are prioritized.

    For odd numbers of people, the leftover person is added to the pair with
    the lowest total meeting count to form a triplet.

    Args:
        registry: Dictionary mapping person IDs to Person objects
        history: List of past meeting pairs as (id1, id2)

    Returns:
        List of person pair tuples (person1, person2) or triplets (person1, person2, person3)
    """
    # Create graph with all possible edges
    graph = nx.Graph()
    graph.add_nodes_from(registry.keys())

    # Add all possible edges with default weight 0
    for person1_id, person2_id in combinations(graph.nodes, 2):
        graph.add_edge(person1_id, person2_id, weight=0)

    # Build meeting counts dict for later use
    meeting_counts = dict(get_past_meeting_counts(history))

    # Update weights based on past meetings (negate to use max_weight_matching)
    for pair, count in meeting_counts.items():
        graph.add_edge(pair[0], pair[1], weight=-count)

    # Find maximum weight matching
    matching = nx.max_weight_matching(graph, maxcardinality=True)

    # Check if there's an unmatched person (odd number of people)
    unmatched_id = None
    if len(registry) % 2 == 1:
        matched_ids = {id1 for id1, id2 in matching} | {id2 for id1, id2 in matching}
        unmatched_id = (set(registry.keys()) - matched_ids).pop()

    # Convert IDs back to Person objects
    if unmatched_id is not None:
        donut_groups = _form_triplet_groups(
            matching, unmatched_id, registry, meeting_counts
        )
    else:
        # All matched, return pairs as before
        donut_groups = [(registry[id1], registry[id2]) for id1, id2 in matching]

    return donut_groups
