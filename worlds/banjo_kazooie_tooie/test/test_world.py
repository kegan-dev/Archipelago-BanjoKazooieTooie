"""The combined world's tables, regions, pool, goal and slot data (worlds/banjo_kazooie_tooie/__init__.py)."""

from collections import Counter
from unittest import TestCase

from BaseClasses import CollectionState, ItemClassification

from worlds.banjo_kazooie_tooie.bk.Items import SM_TUTORIAL_MOVES
from worlds.banjo_kazooie_tooie.bk.Locations import all_location_table as bk_locations
from worlds.banjo_kazooie_tooie.bk.LogicData import GOAL_EVENT as BK_GOAL_EVENT
from worlds.banjo_kazooie_tooie.bk.Names import itemName as bk_item, regionName as bk_region
from worlds.banjo_kazooie.test import check_presets
from worlds.banjo_tooie import BanjoTooieWorld
from worlds.banjo_kazooie_tooie.bt.Names import itemName as bt_item

from . import CombinedTestBase, items_of, make
from .. import BK_ITEMS, BanjoKazooieTooieWorld
from ..Moves import SHARED
from ..Names import BK_LOBBY, CHEATO_HOME, CHEATO_REWARDS, HUB_IN, HUB_OUT, RENAMED, RUINED_LAIR, TOOIE_HUB, TOOIE_SM
from ..Options import Goal, RandomizeBKMoves
from ..Presets import ALPHA


class TestTables(TestCase):
    world = BanjoKazooieTooieWorld

    def test_ids_are_unique(self):
        self.assertEqual(len(set(self.world.item_name_to_id.values())), len(self.world.item_name_to_id))
        self.assertEqual(len(set(self.world.location_name_to_id.values())), len(self.world.location_name_to_id))

    def test_bk_items_keep_bk_ids_and_tooie_keep_theirs(self):
        for name, data in BK_ITEMS.items():
            self.assertEqual(self.world.item_name_to_id[name], data.bkid, name)
        for name, code in BanjoTooieWorld.item_name_to_id.items():
            self.assertEqual(self.world.item_name_to_id[name], code, name)

    def test_renamed_collectables(self):
        for bk_name, name in RENAMED.items():
            self.assertIn(name, self.world.item_name_to_id)
            self.assertNotEqual(self.world.item_name_to_id[name], BanjoTooieWorld.item_name_to_id.get(bk_name))
        self.assertIn(bk_item.NOTE, self.world.item_name_to_id)     # no clash with Tooie's "5 Notes"

    def test_shared_moves_are_tooies_items_only(self):
        for bk_name, tooie in SHARED.items():
            self.assertEqual(self.world.item_name_to_id[tooie], BanjoTooieWorld.item_name_to_id[tooie])
            self.assertFalse(bk_name in BK_ITEMS, bk_name)
        self.assertIn(bk_item.SHOCK_JUMP, BK_ITEMS)

    def test_traps_are_tooies_only(self):
        """BK's five trap items are left out: Tooie's, of the same names, serve both games (client/traps.py)."""
        from worlds.banjo_kazooie_tooie.bk.Items import trap_table as bk_traps
        for name, data in bk_traps.items():
            self.assertEqual(self.world.item_name_to_id[name], BanjoTooieWorld.item_name_to_id[name], name)
            self.assertNotIn(data.bkid, self.world.item_name_to_id.values(), name)

    def test_ruined_lair_not_in_the_table(self):
        for name in RUINED_LAIR:
            self.assertNotIn(name, self.world.location_name_to_id)

    def test_cheatos_rewards_in_the_table(self):
        for name in CHEATO_REWARDS:
            self.assertEqual(self.world.location_name_to_id[name], BanjoTooieWorld.location_name_to_id[name], name)
        self.assertEqual(self.world.location_name_groups["Cheato Rewards"], set(CHEATO_REWARDS))

    def test_every_bk_location_is_in_the_table(self):
        for name, data in bk_locations.items():
            self.assertEqual(self.world.location_name_to_id[name], data.bkid)

    def test_groups_hold_known_names(self):
        for group, names in self.world.item_name_groups.items():
            self.assertTrue(names, group)
            self.assertLessEqual(set(names), set(self.world.item_name_to_id), group)
        for group, names in self.world.location_name_groups.items():
            self.assertTrue(names, group)
            self.assertLessEqual(set(names), set(self.world.location_name_to_id), group)
        self.assertEqual(self.world.item_name_groups["Moves"], BanjoTooieWorld.item_name_groups["Moves"])


class TestDefaults(CombinedTestBase):
    """Default options: AP's default tests (everything reachable, the fill), and the shape of the slot."""

    def test_no_ruined_lair_and_no_bk_spiral_mountain(self):
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        for name in RUINED_LAIR:
            self.assertNotIn(name, names)
        regions = {region.name for region in self.multiworld.get_regions(self.player)}
        self.assertIn(TOOIE_SM, regions)        # Tooie's Spiral Mountain, the only one
        for name, data in bk_locations.items():
            self.assertEqual(name in names, data.region != bk_region.SM and data.group != "Note", name)

    def test_lobby_is_reached_through_the_hub_door_only(self):
        from worlds.banjo_kazooie_tooie.bk.LogicData import REGIONS
        bk_regions = {region for region, _level, _map in REGIONS} - {bk_region.SM}     # that name is Tooie's here
        lobby = self.world.get_region(BK_LOBBY)
        outside = [entrance for entrance in lobby.entrances if entrance.parent_region.name not in bk_regions]
        self.assertEqual([entrance.name for entrance in outside], [HUB_IN])
        self.assertEqual(outside[0].parent_region.name, TOOIE_HUB)
        # and no other way from Tooie into BK's regions
        for region in self.multiworld.get_regions(self.player):
            if region.name in bk_regions:
                for entrance in region.entrances:
                    self.assertTrue(entrance.parent_region.name in bk_regions or entrance.name == HUB_IN,
                                    entrance.name)
        self.assertIn(HUB_OUT, [exit_.name for exit_ in lobby.exits])
        thresholds = [location.name for location in lobby.locations if location.name.endswith("Threshold")]
        self.assertEqual(len(thresholds), 8)

    def test_bk_pool(self):
        items = items_of(self.multiworld)
        self.assertEqual(items[RENAMED[bk_item.JIGGY]], 100)
        self.assertEqual(items[RENAMED[bk_item.MUMBO_TOKEN]], 115)
        self.assertEqual(items[RENAMED[bk_item.EMPTY_HONEYCOMB]], 18)
        for door in bk_item.NOTE_DOORS:
            self.assertEqual(items[door], 1, door)
        for jinjo in bk_item.JINJOS:
            self.assertEqual(items[jinjo], 1, jinjo)
        self.assertEqual(items[bk_item.SHOCK_JUMP], 1)

    def test_pool_fills_the_locations(self):
        pool = [item for item in self.multiworld.itempool if item.player == self.player]
        self.assertEqual(len(pool), len(self.multiworld.get_unfilled_locations(self.player)))

    def test_items_and_locations_are_the_combined_game(self):
        for location in self.multiworld.get_locations(self.player):
            self.assertEqual(location.game, self.game, location.name)
            if location.item is not None:
                self.assertEqual(location.item.game, self.game, location.name)
        for item in self.multiworld.precollected_items[self.player]:
            self.assertEqual(item.game, self.game, item.name)

    def test_slot_data(self):
        data = self.world.fill_slot_data()
        self.assertEqual(data["custom_bt_data"]["version"], BanjoTooieWorld.world_version.as_simple_string())
        self.assertEqual(data["bk"]["layout"], [0, 16])
        self.assertTrue(data["bk"]["skip_lair_cutscene"])      # on by default
        self.assertTrue(0 < data["bk"]["seed"] < 1 << 32)
        self.assertEqual(data["goal"], Goal.option_tooie)
        self.assertEqual(data["hub_door"], 1)
        self.assertIn("bk_notesanity", data["options"])
        self.assertNotIn("bk_randomize_moves", data["options"])     # randomize_bk_moves decides them

    def test_version_and_authors(self):
        """Both worlds are 0.1.0, the version the image's title draws (tools/make_patches.py checks the hack's), with
        the owner's tag SpecialK in the authors (the owner's decisions of 2026-11-12)."""
        import json
        import pkgutil
        for world in ("worlds.banjo_kazooie_tooie.bk", "worlds.banjo_kazooie_tooie"):
            data = json.loads(pkgutil.get_data(world, "archipelago.json"))
            self.assertEqual(data["world_version"], "0.1.0", world)
            self.assertTrue(any("SpecialK" in author for author in data["authors"]), world)

    def test_cheatos_rewards_in_the_throne_room(self):
        """Cheato's five rewards are in Jinjo Village, where the throne room is (Names.CHEATO_HOME), and nowhere else;
        reward n asks 5 x n Cheato Pages, Tooie's rule."""
        home = self.world.get_region(CHEATO_HOME)
        for n, name in enumerate(CHEATO_REWARDS, 1):
            location = self.world.get_location(name)
            self.assertIs(location.parent_region, home, name)
            self.assertIn(location, home.locations)
            self.assertNotIn(location, self.world.get_region(TOOIE_HUB).locations)
            state = CollectionState(self.multiworld)
            state.prog_items[self.player][bt_item.PAGES] = 5 * n - 1
            self.assertFalse(location.access_rule(state), name)
            state.prog_items[self.player][bt_item.PAGES] = 5 * n
            self.assertTrue(location.access_rule(state), name)

    def test_cheato_pages_are_progression(self):
        """With cheato_rewards (on by default) Cheato's pages buy his rewards, as in Tooie."""
        pages = [item for item in self.multiworld.get_items() if item.name == bt_item.PAGES]
        self.assertTrue(pages)
        self.assertTrue(all(item.advancement for item in pages))


class TestEverythingShuffled(CombinedTestBase):
    options = {
        "randomize_bk_moves": "all", "randomize_notes": True,
        "bk_randomize_honeycombs": True, "bk_randomize_jinjos": True, "cheato_rewards": False,
    }

    def test_cheats_at_their_own_rewards(self):
        """Without cheato_rewards Tooie's prefill locks each cheat at its own reward (Items.py:253-257), in the throne
        room."""
        from worlds.banjo_kazooie_tooie.bt.Items import all_item_table as bt_items
        for name in BanjoTooieWorld.item_name_groups["Cheats"]:
            location = self.world.get_location(bt_items[name].default_location)
            self.assertEqual(location.item.name, name)
            self.assertEqual(location.parent_region.name, CHEATO_HOME)


class _StartChoice:
    """A choice of randomize_bk_moves, which decides BK's moves too (Options.RandomizeBKMoves): its moves are start
    items in both games and not in the pool, the hub door is open from the start if they open it, Tooie's half plays
    the choice as one of Tooie's own, and the choice is back for the output."""
    choice: int
    tooie_plays: int
    start: tuple = ()           # the items, by the combined game's names
    hub_open: bool = True

    def test_start_items(self):
        held = Counter(item.name for item in self.multiworld.precollected_items[self.player])
        pool = Counter(item.name for item in self.multiworld.itempool if item.player == self.player)
        items = items_of(self.multiworld)
        for move in self.start:
            self.assertEqual(held[move], 1, move)
            self.assertEqual(pool[move], 0, move)
            self.assertEqual(items[move], 1, move)

    def test_hub_door_from_the_start(self):
        state = CollectionState(self.multiworld)        # the start items only
        self.assertEqual(self.world.get_entrance(HUB_IN).can_reach(state), self.hub_open)
        self.assertEqual(state.can_reach(BK_LOBBY, "Region", self.player), self.hub_open)

    def test_tooies_half_plays_a_choice_of_its_own(self):
        self.assertEqual(self.world.bk_moves_choice, self.choice)
        self.assertEqual(self.world.options.randomize_bk_moves.value, self.tooie_plays)

    def test_the_choice_is_back_for_the_output(self):
        self.world.pre_output()
        self.assertEqual(self.world.options.randomize_bk_moves.value, self.choice)
        data = self.world.fill_slot_data()
        self.assertEqual(data["options"]["randomize_bk_moves"], self.choice)


class TestNoneStart(_StartChoice, CombinedTestBase):
    """None: every BK move from the start, in BK too (Tooie knows them for free besides)."""
    options = {"randomize_bk_moves": "none"}
    choice = tooie_plays = RandomizeBKMoves.option_none
    start = (*SHARED.values(), bk_item.SHOCK_JUMP)


class TestMcJiggyStart(_StartChoice, CombinedTestBase):
    """The McJiggy special: Talon Trot and Tall Jump from the start, in BK too; they do not open the hub door."""
    options = {"randomize_bk_moves": "mcjiggy_special", "randomize_notes": True}
    choice = tooie_plays = RandomizeBKMoves.option_mcjiggy_special
    start = (bt_item.TTROT, bt_item.TJUMP)
    hub_open = False


class TestFlightPadStart(_StartChoice, CombinedTestBase):
    """The McJiggy special's Flight Pad choice: Talon Trot, Tall Jump and Flight Pad from the start; Tooie's half
    plays the McJiggy special."""
    options = {"randomize_bk_moves": "mcjiggy_special_flight_pad", "randomize_notes": True}
    choice = RandomizeBKMoves.option_mcjiggy_special_flight_pad
    tooie_plays = RandomizeBKMoves.option_mcjiggy_special
    start = (bt_item.TTROT, bt_item.TJUMP, bt_item.FPAD)


class TestSpiralMountainStart(_StartChoice, CombinedTestBase):
    """Spiral Mountain's nine from the start (Flap Flip and Climb open the hub door); Tooie's half plays All."""
    options = {"randomize_bk_moves": "spiral_mountain", "randomize_notes": True}
    choice = RandomizeBKMoves.option_spiral_mountain
    tooie_plays = RandomizeBKMoves.option_all
    start = tuple(SHARED[move] for move in SM_TUTORIAL_MOVES)


class TestAllStart(_StartChoice, CombinedTestBase):
    """All: no BK move from the start but Tooie's starting attack, so the hub door is shut at the start (Tooie's
    SM_to_GL wants Flight Pad, or Flap Flip and Climb)."""
    options = {"randomize_bk_moves": "all", "randomize_notes": True}
    choice = tooie_plays = RandomizeBKMoves.option_all
    hub_open = False


class TestAlphaPreset(_StartChoice, CombinedTestBase):
    """The alpha's template (Presets.ALPHA): a full seed on it (Archipelago's default tests), both goals, Spiral
    Mountain's nine BK moves from the start (the hub door open), Tooie's note nests shuffled, no entrance shuffled,
    Tooie's normal costs."""
    options = ALPHA
    choice = RandomizeBKMoves.option_spiral_mountain
    tooie_plays = RandomizeBKMoves.option_all
    start = tuple(SHARED[move] for move in SM_TUTORIAL_MOVES)

    def test_the_alphas_choices(self):
        options = self.world.options
        self.assertEqual(options.goal.value, Goal.option_both)
        self.assertFalse(options.cross_game_world_entrances or options.bk_randomize_world_entrances
                         or options.randomize_world_entrance_loading_zones)
        self.assertEqual(options.world_requirements.current_key, "normal")
        self.assertTrue(options.randomize_notes)    # Tooie refuses spiral_mountain (its all) without it (Presets.py)


class TestPresets(TestCase):
    def test_presets_are_options(self):
        check_presets(self, BanjoKazooieTooieWorld)


class TestBKNotesanity(CombinedTestBase):
    options = {"bk_notesanity": True}

    def test_notes(self):
        items = items_of(self.multiworld)
        self.assertEqual(items[bk_item.NOTE], 900 - sum(  # BK's Spiral Mountain has no notes
            1 for data in bk_locations.values() if data.group == "Note" and data.region == bk_region.SM))


class TestTooieNestsanity(CombinedTestBase):
    options = {"nestsanity": True}


class TestGoals(TestCase):
    def goal_holds(self, goal: str, *events: str) -> bool:
        multiworld = make({"goal": goal}, steps=("generate_early", "create_regions", "create_items", "set_rules"))
        world = multiworld.worlds[1]
        state = CollectionState(multiworld)
        for event in events:
            state.collect(world.create_event_item(event), True)
        return multiworld.completion_condition[1](state)

    def test_tooie(self):
        self.assertTrue(self.goal_holds("tooie", bt_item.VICTORY))
        self.assertFalse(self.goal_holds("tooie", BK_GOAL_EVENT))

    def test_banjo_kazooie(self):
        self.assertTrue(self.goal_holds("banjo_kazooie", BK_GOAL_EVENT))
        self.assertFalse(self.goal_holds("banjo_kazooie", bt_item.VICTORY))

    def test_both(self):
        self.assertFalse(self.goal_holds("both", bt_item.VICTORY))
        self.assertFalse(self.goal_holds("both", BK_GOAL_EVENT))
        self.assertTrue(self.goal_holds("both", bt_item.VICTORY, BK_GOAL_EVENT))


class TestTooieHalfUnchanged(TestCase):
    """For the same seed and Tooie options, Tooie's half is what a standalone Tooie world makes: its world order and
    costs, and its progression items but the shared moves (BK adds those Tooie lacks). Filler can differ: the
    standalone world has the ruined Lair's seven nests more to pad, and its rolls can be useful jiggies, notes and
    doubloons; BK's half takes some filler's places."""

    def test_same_seed(self):
        from test.general import setup_multiworld
        for seed in (1, 2, 3):
            combined = make(seed=seed)
            alone = setup_multiworld(BanjoTooieWorld, ("generate_early", "create_regions", "create_items"), seed)
            ours, theirs = combined.worlds[1], alone.worlds[1]
            self.assertEqual(ours.world_order, theirs.world_order)
            self.assertEqual(ours.world_requirements, theirs.world_requirements)
            self.assertEqual(ours.loading_zones, theirs.loading_zones)
            self.assertEqual(ours.jamjars_silo_costs, theirs.jamjars_silo_costs)
            skip = set(SHARED.values())

            def progression(multiworld):
                items = [item for item in multiworld.itempool if item.player == 1]
                items += multiworld.precollected_items[1]
                items += [location.item for location in multiworld.get_locations(1)
                          if location.item is not None and location.item.code is not None]
                return Counter(item.name for item in items if item.advancement
                               and item.name in BanjoTooieWorld.item_name_to_id and item.name not in skip)

            self.assertEqual(progression(combined), progression(alone), seed)


class TestBKWorldEntrances(CombinedTestBase):
    """bk_randomize_world_entrances: BK's Lair doors drawn as the BK world draws them (worlds/banjo_kazooie/Regions.py,
    draw_world_entrances), with a stream of their own, the hub door untouched. On seed 1, which fills (none of thirty
    combined seeds failed, 2026-11-05)."""
    options = {"bk_randomize_world_entrances": True}

    def setUp(self) -> None:
        if self.auto_construct:
            self.world_setup(1)

    def test_doors_drawn(self):
        from worlds.banjo_kazooie_tooie.bk import Entrances
        from worlds.banjo_kazooie_tooie.bk.Regions import door_name
        mapping = self.world.bk.world_entrances
        self.assertTrue(Entrances.is_permutation(mapping))
        self.assertGreaterEqual(self.world.bk.entrance_draws, 1)
        for door in Entrances.DOORS:
            self.assertEqual(self.world.get_entrance(door_name(door.level)).connected_region.name,
                             Entrances.DOOR_OF[mapping[door.level]].entry_region)
        self.assertEqual(self.world.fill_slot_data()["bk"]["world_entrances"], mapping)

    def test_lobby_still_only_through_the_hub_door(self):
        from worlds.banjo_kazooie_tooie.bk.LogicData import REGIONS
        bk_regions = {region for region, _level, _map in REGIONS} - {bk_region.SM}
        lobby = self.world.get_region(BK_LOBBY)
        self.assertEqual([e.name for e in lobby.entrances if e.parent_region.name not in bk_regions], [HUB_IN])

    def test_tooie_half_draws_the_same(self):
        from test.general import gen_steps
        on = make({"bk_randomize_world_entrances": True}, seed=2, steps=gen_steps)
        off = make({}, seed=2, steps=gen_steps)
        self.assertEqual(on.worlds[1].random.getstate(), off.worlds[1].random.getstate(),
                         "the doors' draw takes nothing from the world's random")
