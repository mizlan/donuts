"""Tests for the solver module."""

import pytest

from src.history import Person
from src.solver import make_assignment


@pytest.fixture
def sample_registry():
    """Create a sample registry for testing."""
    return {
        0: Person(name="Alice", email="alice@example.com"),
        1: Person(name="Bob", email="bob@example.com"),
        2: Person(name="Charlie", email="charlie@example.com"),
        3: Person(name="Diana", email="diana@example.com"),
    }


@pytest.fixture
def odd_registry():
    """Create a registry with odd number of people."""
    return {
        0: Person(name="Alice", email="alice@example.com"),
        1: Person(name="Bob", email="bob@example.com"),
        2: Person(name="Charlie", email="charlie@example.com"),
    }


class TestMakeAssignmentEven:
    """Tests for make_assignment with even number of people."""

    def test_even_number_creates_pairs(self, sample_registry):
        """Test that even number of people creates only pairs."""
        history = []
        result = make_assignment(sample_registry, history)

        assert len(result) == 2
        assert all(len(group) == 2 for group in result)

    def test_all_people_matched(self, sample_registry):
        """Test that all people are included in the assignment."""
        history = []
        result = make_assignment(sample_registry, history)

        all_people = set()
        for group in result:
            for person in group:
                all_people.add(person.email)

        expected = {person.email for person in sample_registry.values()}
        assert all_people == expected

    def test_no_one_paired_twice(self, sample_registry):
        """Test that no person is paired with themselves or duplicated."""
        history = []
        result = make_assignment(sample_registry, history)

        for group in result:
            emails = [person.email for person in group]
            assert len(emails) == len(set(emails))

    def test_respects_meeting_history(self, sample_registry):
        """Test that pairs with prior meetings get lower priority."""
        history = [(0, 1), (0, 1)]  # Alice and Bob met twice
        result = make_assignment(sample_registry, history)

        # Alice and Bob should not be together in any group
        for group in result:
            emails = {person.email for person in group}
            assert not (
                "alice@example.com" in emails and "bob@example.com" in emails
            )


class TestMakeAssignmentOdd:
    """Tests for make_assignment with odd number of people."""

    def test_odd_number_creates_triplet(self, odd_registry):
        """Test that odd number of people creates one triplet."""
        history = []
        result = make_assignment(odd_registry, history)

        assert len(result) == 1
        assert len(result[0]) == 3

    def test_all_people_in_triplet(self, odd_registry):
        """Test that all people are included when forming triplet."""
        history = []
        result = make_assignment(odd_registry, history)

        all_people = set()
        for group in result:
            for person in group:
                all_people.add(person.email)

        expected = {person.email for person in odd_registry.values()}
        assert all_people == expected

    def test_triplet_added_to_lowest_meeting_pair(self, odd_registry):
        """Test that unmatched person is added to pair with lowest meeting count."""
        # Alice and Bob met once, Bob and Charlie haven't met
        history = [(0, 1)]
        result = make_assignment(odd_registry, history)

        assert len(result) == 1
        triplet = result[0]
        emails = {person.email for person in triplet}

        # The triplet should contain Charlie (unmatched)
        assert "charlie@example.com" in emails

        # It should be paired with Alice and Bob (who have lowest total meetings)
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails

    def test_triplet_with_fresh_pair(self):
        """Test triplet formation when there's a fresh pair."""
        registry = {
            0: Person(name="Alice", email="alice@example.com"),
            1: Person(name="Bob", email="bob@example.com"),
            2: Person(name="Charlie", email="charlie@example.com"),
            3: Person(name="Diana", email="diana@example.com"),
            4: Person(name="Eve", email="eve@example.com"),
        }
        # Charlie and Diana met once, others haven't met
        history = [(2, 3)]
        result = make_assignment(registry, history)

        # Should have 2 groups total
        assert len(result) == 2

        # One should be a triplet
        triplet = next((g for g in result if len(g) == 3), None)
        pair = next((g for g in result if len(g) == 2), None)

        assert triplet is not None
        assert pair is not None

        # The triplet should contain Eve (unmatched)
        triplet_emails = {person.email for person in triplet}
        assert "eve@example.com" in triplet_emails


class TestMakeAssignmentEdgeCases:
    """Tests for edge cases."""

    def test_single_pair(self):
        """Test with exactly two people."""
        registry = {
            0: Person(name="Alice", email="alice@example.com"),
            1: Person(name="Bob", email="bob@example.com"),
        }
        result = make_assignment(registry, [])

        assert len(result) == 1
        assert len(result[0]) == 2
        assert {p.email for p in result[0]} == {
            "alice@example.com",
            "bob@example.com",
        }

    def test_single_triplet(self, odd_registry):
        """Test with exactly three people."""
        result = make_assignment(odd_registry, [])

        assert len(result) == 1
        assert len(result[0]) == 3
