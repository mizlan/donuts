"""Tracking and history management for donut meetups."""

import csv
from pathlib import Path


def append_to_history(person1: str, person2: str, history_path: str) -> None:
    """Append a donut chat pair to history.csv.

    Args:
        person1: Name or email of first person
        person2: Name or email of second person
        history_path: Path to history.csv file
    """
    try:
        path = Path(history_path)

        # Read existing data
        rows = []
        if path.exists():
            with open(path, "r", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)

        # Append new row
        rows.append([person1, person2])

        # Write back
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"Recorded donut chat: {person1}, {person2}")
    except Exception as e:
        print(f"Error appending to history: {e}")
        raise


def get_history_size(history_path: str) -> int:
    """Get number of donut chat records in history.csv.

    Args:
        history_path: Path to history.csv file

    Returns:
        Number of rows in history file
    """
    try:
        path = Path(history_path)
        if not path.exists():
            return 0

        with open(path, "r", newline="") as f:
            reader = csv.reader(f)
            return sum(1 for _ in reader)
    except Exception as e:
        print(f"Error reading history: {e}")
        return 0
