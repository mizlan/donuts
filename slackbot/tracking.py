"""Tracking and history management for donut meetups."""

import csv
from pathlib import Path


def history_contains_ts(history_path: str, ts: str) -> bool:
    """Check if a Slack message timestamp already exists in history.

    Args:
        history_path: Path to history.csv file
        ts: Slack message timestamp to check

    Returns:
        True if the timestamp exists in history, False otherwise
    """
    path = Path(history_path)
    if not path.exists():
        return False

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3 and row[2] == ts:
                return True
    return False


def append_to_history(
    person1: str, person2: str, history_path: str, slack_ts: str | None = None
) -> None:
    """Append a donut chat pair to history.csv.

    Args:
        person1: Name or email of first person
        person2: Name or email of second person
        history_path: Path to history.csv file
        slack_ts: Optional Slack message timestamp for deduplication
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
        row = [person1, person2]
        if slack_ts:
            row.append(slack_ts)
        rows.append(row)

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
