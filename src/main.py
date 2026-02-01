"""Main entry point for donut pairing generation."""

import argparse
from rich import print

from . import history, solver

# Constants
DEFAULT_REGISTRY_PATH = "./registry.csv"
DEFAULT_HISTORY_PATH = "./history.csv"


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and return the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate optimal donut pairings based on registry and history"
    )
    parser.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_PATH,
        help=f"Path to registry CSV file (default: {DEFAULT_REGISTRY_PATH})",
    )
    parser.add_argument(
        "--history",
        default=DEFAULT_HISTORY_PATH,
        help=f"Path to history CSV file (default: {DEFAULT_HISTORY_PATH})",
    )
    return parser


def main() -> None:
    """Main entry point for the donut pairing application."""
    parser = create_argument_parser()
    args = parser.parse_args()

    print(":doughnut: [bold magenta]donuts[/bold magenta] is running!")

    # Load registry and history
    registry = history.parse_registry(args.registry)
    print(f"{len(registry)} members to match")

    past_meetings = history.parse_history(registry, args.history)

    # Generate pairings
    pairs = solver.make_assignment(registry, past_meetings)

    # Output results
    print("···")
    print(f"Generated {len(pairs)} chats")
    for group in pairs:
        names = ",".join(person.name for person in group)
        print(names)


if __name__ == "__main__":
    main()
