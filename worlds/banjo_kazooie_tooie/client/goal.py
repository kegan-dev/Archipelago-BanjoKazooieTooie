"""The slot's goal across the two games (the yaml setting goal, Options.Goal): each game's own goal can only be seen
while that game runs, so the client keeps the ones reached in the server's data storage, under storage_key."""

from typing import AbstractSet, FrozenSet

from .resident import BK, TOOIE

# Options.Goal's values -> the games whose goal the slot needs
NEEDED = {0: frozenset({TOOIE}), 1: frozenset({BK}), 2: frozenset({TOOIE, BK})}


def needed(goal: int) -> FrozenSet[str]:
    return NEEDED.get(goal, NEEDED[0])


def met(goal: int, reached: AbstractSet[str]) -> bool:
    return needed(goal) <= reached


def storage_key(team: int, slot: int) -> str:
    return f"BanjoKazooieTooie_{team}_{slot}_goals"
