"""Shared moves (Moves.py, Part.BkPart.bk_place_moves) and randomize_bk_moves, which decides BK's moves too
(Options.RandomizeBKMoves): exactly one item teaches each move, each choice's moves are start items, and BK's rules
ask for the shared item."""

from collections import Counter
from unittest import TestCase

from BaseClasses import CollectionState

from worlds.banjo_kazooie_tooie.bk.Names import itemName as bk_item

from . import CombinedTestBase, items_of, make
from .. import START_MOVES
from ..Moves import SHARED, active_chains, bk_moves_known, grants
from ..Options import RandomizeBKMoves

TOOIE_MOVE_SETTINGS = [
    {"randomize_bk_moves": "none"},
    {"randomize_bk_moves": "mcjiggy_special", "randomize_notes": True},
    {"randomize_bk_moves": "all", "randomize_notes": True},
    # every progressive item that holds a shared move
    {"randomize_bk_moves": "all", "randomize_notes": True, "progressive_beak_buster": True, "progressive_shoes": True,
     "progressive_water_training": "basic", "progressive_flight": True, "progressive_egg_aiming": "basic",
     "progressive_bash_attack": True, "randomize_stop_n_swap": True},
    {"randomize_bk_moves": "all", "randomize_notes": True, "progressive_water_training": "advanced",
     "progressive_egg_aiming": "advanced"},
    # the combined world's two choices, with the moves' own items and with the progressive items that hold them
    {"randomize_bk_moves": "mcjiggy_special_flight_pad", "randomize_notes": True},
    {"randomize_bk_moves": "mcjiggy_special_flight_pad", "randomize_notes": True, "progressive_flight": True},
    {"randomize_bk_moves": "spiral_mountain", "randomize_notes": True},
    {"randomize_bk_moves": "spiral_mountain", "randomize_notes": True, "progressive_water_training": "advanced",
     "progressive_bash_attack": True, "randomize_stop_n_swap": True},
]


class TestEachMoveOnce(TestCase):
    def test_matrix(self):
        for options in TOOIE_MOVE_SETTINGS:
            with self.subTest(**{k: str(v) for k, v in options.items()}):
                multiworld = make(options)
                world = multiworld.worlds[1]
                items = items_of(multiworld)
                chains = world.bk.chains
                self.assertEqual(chains, active_chains(lambda name: world.options.as_dict(name)[name]))
                for bk_name, tooie_name in SHARED.items():
                    by_chain = any(items[name] >= copies for name, copies in grants(tooie_name, chains)[1:])
                    self.assertEqual(items[tooie_name] + by_chain, 1, f"{bk_name} ({tooie_name}): {items[tooie_name]}"
                                                                      f" items, by a progressive item: {by_chain}")
                self.assertEqual(items[bk_item.SHOCK_JUMP], 1)
                # the choice's moves from the start, and no others but Tooie's starting attack, which may be a shared
                # move (Tooie's choose_starter_attack)
                held = Counter(item.name for item in multiworld.precollected_items[1])
                start = set(START_MOVES[RandomizeBKMoves.options[options["randomize_bk_moves"]]])
                known = bk_moves_known(held, chains) | ({bk_item.SHOCK_JUMP} & set(held))
                attack = Counter({world.item_id_to_name[world.starting_attack]: 1}) if world.starting_attack else {}
                self.assertEqual(known - bk_moves_known(attack, chains), start - bk_moves_known(attack, chains))
                self.assertLessEqual(start, known)


class TestBKRuleAsksForTheSharedItem(TestCase):
    def test_flight(self):
        """BK's rule for Flight asks for Tooie's Flight Pad, or for Progressive Flight's first copy."""
        for options, item, copies in ((TOOIE_MOVE_SETTINGS[2], "Flight Pad", 1),
                                      (TOOIE_MOVE_SETTINGS[3], "Progressive Flight", 1)):
            multiworld = make(options, steps=("generate_early", "create_regions", "create_items", "set_rules"))
            world = multiworld.worlds[1]
            rule = world.bk.bk_move(bk_item.FLIGHT)
            state = CollectionState(multiworld)
            check = rule if callable(rule) else (lambda s, name=rule: s.has(name, 1))
            self.assertFalse(check(state))
            for _ in range(copies):
                state.collect(world.create_item(item), True)
            self.assertTrue(check(state), options)

    def test_every_shared_move_of_a_chain(self):
        """BK's rule for a shared move in an active chain asks for the progressive item's copies up to the move's place
        in the chain, one fewer not being enough: Beak Bomb two Progressive Flights, Turbo Talon Trot two Progressive
        Shoes, the others one copy (the basic chains and the advanced)."""
        tried = set()
        for options in (TOOIE_MOVE_SETTINGS[3], TOOIE_MOVE_SETTINGS[4]):
            multiworld = make(options, steps=("generate_early", "create_regions", "create_items", "set_rules"))
            world = multiworld.worlds[1]
            for bk_name, tooie_name in SHARED.items():
                for name, copies in grants(tooie_name, world.bk.chains)[1:]:
                    rule = world.bk.bk_move(bk_name)
                    self.assertTrue(callable(rule), bk_name)
                    state = CollectionState(multiworld)    # with the start items: Tooie's starting attack may be a copy
                    while state.count(name, 1) < copies - 1:
                        state.collect(world.create_item(name), True)
                    if state.count(name, 1) == copies - 1:
                        self.assertFalse(rule(state), f"{bk_name}: {copies - 1} of {name}")
                    while state.count(name, 1) < copies:
                        state.collect(world.create_item(name), True)
                    self.assertTrue(rule(state), f"{bk_name}: {copies} of {name}")
                    tried.add((bk_name, name, copies))
        self.assertIn((bk_item.BEAK_BOMB, "Progressive Flight", 2), tried)
        self.assertIn((bk_item.TURBO_TROT, "Progressive Shoes", 2), tried)
        self.assertIn((bk_item.SWIM, "Progressive Adv. Water Training", 1), tried)
        self.assertIn((bk_item.EGGS, "Progressive Adv. Egg Aiming", 1), tried)


class _ChainsFromTheSlotData:
    """The client's chains, from the slot data as the server sends it (NetUtils' JSON), are the world's
    (Moves.slot_chains)."""

    def test_the_clients_chains(self):
        from NetUtils import decode, encode
        from ..Moves import slot_chains
        data = decode(encode(self.world.fill_slot_data()))
        self.assertEqual(slot_chains(data), self.world.bk.chains)
        self.assertEqual(len(self.world.bk.chains), self.chains)


class TestChainsBasic(_ChainsFromTheSlotData, CombinedTestBase):
    options = TOOIE_MOVE_SETTINGS[3]
    chains = 6


class TestChainsAdvanced(_ChainsFromTheSlotData, CombinedTestBase):
    options = TOOIE_MOVE_SETTINGS[4]
    chains = 2
