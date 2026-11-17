"""The world's option presets (WebWorld.options_presets): Archipelago's Launcher ("Generate Template Options") and
tools/make_apworlds.py write a template yaml for each, with every option and these values chosen."""

from typing import Any, Dict

# The alpha with friends in a multiworld (docs/ROADMAP.md, "The owner's next items", 8; the owner's choices of
# 2026-11-15): both games to finish, Spiral Mountain's nine BK moves at the start in both games and the other nine
# shuffled (which opens the hub door from the start: Flap Flip and Climb), no entrance shuffled, Tooie's normal world
# costs. And Tooie's note nests shuffled: with any of BK's moves shuffled the stock Tooie world refuses a seed without
# its notes, signposts or nests shuffled (Archipelago-BanjoTooie/worlds/banjo_tooie/__init__.py:593-598; its half
# plays spiral_mountain as all), and the owner chose the notes, which the tests pair with spiral_mountain and the
# progressive moves' hand test played (docs/tutorials/32-progressive-moves.md). Every other option is the world's
# default. The values the defaults already have are written out, so that the alpha's template keeps them if a
# default changes.
ALPHA: Dict[str, Any] = {
    "goal": "both",
    "randomize_bk_moves": "spiral_mountain",
    "randomize_notes": True,
    "cross_game_world_entrances": False,
    "bk_randomize_world_entrances": False,
    "randomize_world_entrance_loading_zones": False,
    "world_requirements": "normal",
}

options_presets: Dict[str, Dict[str, Any]] = {
    "Alpha": ALPHA,
}
