import argparse
from rich import print
import history
import solver


def main():
    parser = argparse.ArgumentParser(description="Generate random donut pairings")
    parser.add_argument(
        "--registry",
        default="./registry.csv",
        help="Path to registry CSV file (default: %(default)s)",
    )
    parser.add_argument(
        "--history",
        default="./history.csv",
        help="Path to history CSV file (default: %(default)s)",
    )
    args = parser.parse_args()

    print(":doughnut: [bold magenta]donuts[/bold magenta] is running!")

    registry = history.parse_registry(args.registry)
    print(f"{len(registry)} members to match")

    past_meetings = history.parse(registry, args.history)

    pairs = solver.make_assignment(registry, past_meetings)

    print("···")
    print(f"Generated {len(pairs)} chats")
    for person1, person2 in pairs:
        print(f"{person1.name},{person2.name}")


if __name__ == "__main__":
    main()
