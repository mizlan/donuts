"""Registry and history parsing for donut pairings."""

import csv
from dataclasses import dataclass
from pathlib import Path
from rich import print

# Constants
MIN_CSV_COLUMNS = 2
MAX_CSV_COLUMNS = 3
IDENTIFIER_MAPPING_ERROR_TEMPLATE = "duplicate key {identifier} in registry"
PERSON_NOT_IN_REGISTRY_WARNING = (
    "Person {person} appears in history but not in registry, skipping"
)
INVALID_CSV_LINE_WARNING = "Found odd line (will skip this): {line}"


@dataclass
class Person:
    """Represents a person in the registry."""

    name: str
    email: str


def _parse_csv_row(row: list[str]) -> tuple[str, str, str | None] | None:
    """Parse and validate a CSV row with person1, person2, and optional slack_ts.

    Args:
        row: A CSV row

    Returns:
        Tuple of (person1, person2, slack_ts) if valid, None otherwise.
        slack_ts is None for rows without a timestamp.
    """
    if len(row) < MIN_CSV_COLUMNS or len(row) > MAX_CSV_COLUMNS:
        if row:  # Only warn if row is not empty
            print(f":warning: {INVALID_CSV_LINE_WARNING.format(line=row)}")
        return None
    person1, person2 = row[0], row[1]
    slack_ts = row[2] if len(row) == MAX_CSV_COLUMNS else None
    return person1, person2, slack_ts


def parse_registry(filename: str | Path) -> dict[int, Person]:
    """Parse a registry CSV file and return a mapping of ID to Person.

    Args:
        filename: Path to the registry CSV file with columns (name, email)

    Returns:
        Dictionary mapping person IDs to Person objects

    Raises:
        FileNotFoundError: If the registry file does not exist
    """
    try:
        registry: dict[int, Person] = {}
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                parsed = _parse_csv_row(row)
                if parsed is None:
                    continue

                name, email, _ = parsed
                person_id = len(registry)
                registry[person_id] = Person(name=name, email=email)

        return registry
    except FileNotFoundError:
        raise FileNotFoundError(f"Registry file not found: {filename}")


def _warn_unknown_person(person: str) -> None:
    """Print warning for a person not found in registry."""
    print(f":warning: {PERSON_NOT_IN_REGISTRY_WARNING.format(person=person)}")


def _build_identifier_mapping(registry: dict[int, Person]) -> dict[str, int]:
    """Build a mapping from identifiers (name/email) to person IDs.

    Args:
        registry: Dictionary of person IDs to Person objects

    Returns:
        Dictionary mapping identifiers to person IDs

    Raises:
        KeyError: If duplicate identifiers are found in the registry
    """
    identifier_to_id: dict[str, int] = {}

    for person_id, person in registry.items():
        for identifier in [person.name, person.email]:
            if identifier in identifier_to_id:
                raise KeyError(
                    IDENTIFIER_MAPPING_ERROR_TEMPLATE.format(identifier=identifier)
                )
            identifier_to_id[identifier] = person_id

    return identifier_to_id


def parse_history(
    registry: dict[int, Person], filename: str | Path
) -> list[tuple[int, int]]:
    """Parse a history CSV file and return past meeting pairs.

    Args:
        registry: Dictionary mapping person IDs to Person objects
        filename: Path to the history CSV file with columns (person1, person2)

    Returns:
        List of tuples containing past meeting pairs as (id1, id2)

    Raises:
        FileNotFoundError: If the history file does not exist
    """
    identifier_to_id = _build_identifier_mapping(registry)
    past_meetings: list[tuple[int, int]] = []

    try:
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                parsed = _parse_csv_row(row)
                if parsed is None:
                    continue

                person1, person2, _ = parsed

                if person1 not in identifier_to_id:
                    _warn_unknown_person(person1)
                    continue
                if person2 not in identifier_to_id:
                    _warn_unknown_person(person2)
                    continue

                id1 = identifier_to_id[person1]
                id2 = identifier_to_id[person2]

                past_meetings.append((id1, id2))

        return past_meetings
    except FileNotFoundError:
        raise FileNotFoundError(f"History file not found: {filename}")
