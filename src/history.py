import csv
from dataclasses import dataclass
from rich import print


@dataclass
class Person:
    name: str
    email: str


def parse_registry(filename):
    registry: dict[int][Person] = {}
    with open(filename, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 0:
                continue
            elif len(row) != 2:
                print(f":warning: Found odd line (will skip this): {row}")
                continue
            name, email = row
            id_ = len(registry)
            registry[id_] = Person(name=name, email=email)
    return registry


def parse(registry: dict[int][Person], filename):
    identifier_to_id = {}
    for i, person in registry.items():
        if person.name in identifier_to_id:
            raise KeyError(f"duplicate key {person.name} in registry")
        if person.email in identifier_to_id:
            raise KeyError(f"duplicate key {person.email} in registry")

        identifier_to_id[person.name] = i
        identifier_to_id[person.email] = i

    past_meetings = []

    with open(filename, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 0:
                continue
            elif len(row) != 2:
                print(f":warning: Found odd line (will skip this): {row}")
                continue
            person1, person2 = row

            if person1 not in identifier_to_id:
                print(
                    f":warning: Person {person1} appears in history but not in registry, skipping"
                )
                continue
            if person2 not in identifier_to_id:
                print(
                    f":warning: Person {person2} appears in history but not in registry, skipping"
                )
                continue

            id1 = identifier_to_id[person1]
            id2 = identifier_to_id[person2]

            past_meetings.append((id1, id2))

    return past_meetings
