"""Options of the combined world: every option of the stock Tooie world under its own name, the goal, and BK's
options under "bk_" names (Tooie already has logic_type, randomize_honeycombs and randomize_jinjos, with Tooie's
meanings). BK's moves have no option of their own: the moves are shared, so Tooie's randomize_bk_moves decides them
for both games (the owner's decision of 2026-11-03; it replaced bk_randomize_moves and
bk_start_with_spiral_mountain_moves)."""

from dataclasses import dataclass
from typing import List

from Options import Choice, DefaultOnToggle, OptionGroup, Toggle

from .bk import Options as BK
from .bt.Options import BanjoTooieOptions, RandomizeBKMoveList, bt_option_groups


class RandomizeBKMoves(RandomizeBKMoveList):
    """Banjo-Kazooie's Movelist are randomized: the moves Bottles teaches, each one item in this slot and learned in
    both games. The choice is the moves you start with, in both games; every other one is shuffled into the pool.
    None - all of them.
    Mcjiggy Special - Talon Trot and Tall Jump.
    Mcjiggy Special Flight Pad - Talon Trot, Tall Jump and Flight Pad.
    Spiral Mountain - Spiral Mountain's nine: Climb, Swim, Feathery Flap, Flap Flip, Rat-a-tat Rap, Beak Barge, Roll,
    Claw Swipe and Tall Jump.
    All - none of them.
    With Flight Pad, or Flap Flip and Climb, the way to Gruntilda's Lair in Spiral Mountain, the door into
    Banjo-Kazooie, is open from the start."""
    display_name = "Randomize Banjo-Kazooie Movelist"
    option_mcjiggy_special_flight_pad = 3
    option_spiral_mountain = 4
    # Tooie's half plays the two choices of the combined world as one of its own, and the world gives each choice's
    # moves as start items (BanjoKazooieTooieWorld: TOOIE_PLAYS, START_MOVES)


class Goal(Choice):
    """What finishes the slot. Tooie: Tooie's victory condition (the setting Victory Condition). Banjo-Kazooie:
    Gruntilda beaten in Banjo-Kazooie. Both: the two together. The client remembers each game's goal on the
    server, since each can only be seen while its game runs."""
    display_name = "Goal"
    option_tooie = 0
    option_banjo_kazooie = 1
    option_both = 2
    default = 0


class BKRandomizeHoneycombs(BK.RandomizeHoneycombs):
    """Banjo-Kazooie: shuffle the Lair Empty Honeycombs into the item pool. Off: each honeycomb is where it lies,
    as in the vanilla game. Spiral Mountain's six are not in the slot (the hub door skips Spiral Mountain)."""
    display_name = "Banjo-Kazooie: Randomize Empty Honeycombs"


class BKRandomizeJinjos(BK.RandomizeJinjos):
    __doc__ = "Banjo-Kazooie: " + BK.RandomizeJinjos.__doc__
    display_name = "Banjo-Kazooie: Randomize Jinjos"


class BKNotesanity(BK.Notesanity):
    __doc__ = "Banjo-Kazooie: " + BK.Notesanity.__doc__
    display_name = "Banjo-Kazooie: Notesanity"


class BKSkipIntro(DefaultOnToggle):
    """Banjo-Kazooie: a game started from Banjo-Kazooie's own file select starts in Spiral Mountain instead of
    playing the intro. A game started through the hub door starts in the Lair either way."""
    display_name = "Banjo-Kazooie: Skip the Intro"


class BKSkipLairCutscene(BK.SkipLairCutscene):
    """Banjo-Kazooie: the first time Banjo enters Gruntilda's Lair (through the hub door, or from Banjo-Kazooie's
    own Spiral Mountain), go straight to its lobby instead of watching the cutscene of Gruntilda's machine room."""
    display_name = "Banjo-Kazooie: Skip the Lair's Cutscene"


class BKRandomizeWorldEntrances(BK.RandomizeWorldEntrances):
    """Banjo-Kazooie: shuffle which world each of the nine world doors in Gruntilda's Lair leads into. A door keeps
    its own picture and podium; leaving a world takes Banjo back out through the door he came in by. Mumbo's forms
    come off on the way into or out of a world: in the Lair, press D-pad left near the door of a world whose Mumbo
    has been paid for that form to take it again (and D-pad left there again to change back). Only the Lair's doors:
    the hub door and Tooie's own entrances stay where they are (Tooie's own option shuffles those)."""
    display_name = "Banjo-Kazooie: Randomize World Entrances"


class CrossGameWorldEntrances(Toggle):
    """Shuffle the world entrances of both games together: the nine world doors of Banjo-Kazooie's Gruntilda's
    Lair and Tooie's nine world entrances on the Isle o' Hags (Cauldron Keep's too). A door in BK's Lair can lead into
    a Tooie world and a Tooie entrance into a BK world; leaving a world takes Banjo back out through the door it is
    behind, in whichever game that is, and the console switches games behind a black screen. Each door keeps its own
    cost: a Lair door its picture and podium, a Tooie entrance its world's unlock. The hub door, Tooie's boss rooms
    and backdoors stay where they are. Mumbo's and Humba Wumba's forms work as they do with each game's own shuffle.
    With this on, Banjo-Kazooie: Randomize World Entrances and Randomize World Entrance Loading Zones are turned off:
    this shuffles both."""
    display_name = "World Entrances Across the Games"


class BKLogicType(BK.LogicType):
    __doc__ = "Banjo-Kazooie: " + BK.LogicType.__doc__
    display_name = "Banjo-Kazooie: Logic Type"


@dataclass
class BanjoKazooieTooieOptions(BanjoTooieOptions):
    randomize_bk_moves: RandomizeBKMoves    # Tooie's, deciding BK's moves too, with two more choices
    goal: Goal
    bk_randomize_honeycombs: BKRandomizeHoneycombs
    bk_randomize_jinjos: BKRandomizeJinjos
    bk_notesanity: BKNotesanity
    bk_skip_intro: BKSkipIntro
    bk_skip_lair_cutscene: BKSkipLairCutscene
    bk_randomize_world_entrances: BKRandomizeWorldEntrances
    bk_logic_type: BKLogicType
    cross_game_world_entrances: CrossGameWorldEntrances


option_groups: List[OptionGroup] = [
    OptionGroup("Goal", [Goal]),
    OptionGroup("Both Games", [CrossGameWorldEntrances]),
    # Tooie's groups, without the "Item & Location Options" that registering Tooie's world appended to its list
    # (worlds/AutoWorld.py, WebWorldRegister): ours gets its own.
    *(OptionGroup(group.name, [RandomizeBKMoves if option is RandomizeBKMoveList else option for option in group.options],
                  group.start_collapsed)
      for group in bt_option_groups if group.name != "Item & Location Options"),
    OptionGroup("Banjo-Kazooie", [
        BKRandomizeHoneycombs, BKRandomizeJinjos, BKNotesanity, BKSkipIntro, BKSkipLairCutscene,
        BKRandomizeWorldEntrances, BKLogicType,
    ]),
]
