"""A combined slot beside a standalone Tooie slot in one multiworld: Tooie's class-wide state (its cryptic hints'
caches, its progression flag) must serve both (__init__.py, pre_output and post_fill)."""

from unittest import TestCase

from BaseClasses import ItemClassification
from Fill import distribute_items_restrictive
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from worlds.banjo_tooie import BanjoTooieWorld
from worlds.banjo_kazooie_tooie.bt.Names import itemName as bt_item

from .. import BanjoKazooieTooieWorld

CRYPTIC = {"hint_clarity": "cryptic", "signpost_hints": 10, "randomize_signposts": True}


class TestMixedMultiworld(TestCase):
    def generate(self, worlds):
        # Tooie's post_fill converts its jiggies once per process, behind a flag on its class that nothing resets
        # (Archipelago-BanjoTooie/worlds/banjo_tooie/__init__.py:1045-1047): a generation is one process, so start
        # each as one starts.
        BanjoTooieWorld.has_converted_progression_items = False
        multiworld = setup_multiworld(worlds, ("generate_early", "create_regions", "create_items", "set_rules",
                                               "connect_entrances", "generate_basic", "pre_fill"), 7, CRYPTIC)
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        call_all(multiworld, "pre_output")
        return multiworld

    def check(self, multiworld):
        for world in multiworld.worlds.values():
            self.assertTrue(world.hints, world.game)            # every Tooie-family world made its hints
            for location in multiworld.get_locations(world.player):
                item = location.item
                if item.player == world.player and item.name in (bt_item.JIGGY, bt_item.NOTE, bt_item.DOUBLOON):
                    self.assertEqual(item.classification, ItemClassification.progression, item.name)
        self.assertTrue(multiworld.can_beat_game(multiworld.state))

    def test_combined_first(self):
        self.check(self.generate([BanjoKazooieTooieWorld, BanjoTooieWorld]))

    def test_tooie_first(self):
        self.check(self.generate([BanjoTooieWorld, BanjoKazooieTooieWorld]))
