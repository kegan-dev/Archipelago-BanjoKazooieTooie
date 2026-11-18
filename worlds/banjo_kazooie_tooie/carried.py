"""The two worlds this world is built on, carried inside it, so that its apworld is all a player installs (the owner's
wish of 2026-11-15): the Banjo-Kazooie world of the same build, in the subpackage `bk`, and jjjj12212's Banjo-Tooie
world V4.13.1 (MIT, its LICENSE beside it in the apworld), in `bt`. The combined world imports them only from there.

Each subpackage's __init__ calls carry(), which runs that world's own __init__.py, unchanged, as the subpackage's
code: the world's modules become the subpackage's submodules (its relative imports resolve there), and its World
class, settings and client are the subpackage's. Nothing of it is registered: while it runs, Archipelago's world
registry (AutoWorldRegister.world_types) and the Launcher's components and icons are stand-ins, so the world's class
does not take its game's name and its client gets no Launcher entry. The real world can then be installed beside this
one, at any version, or not at all. Its manifest's world_version is given to its World class afterwards, as
Archipelago gives a registered world's (worlds/__init__.py): the stock Tooie client compares the hack's version with
it (BTClient.py:165).

Where the world's files are:
- in a built apworld, in the subpackage's own folder: tools/make_apworlds.py puts them there, the world's __init__.py
  as __world__.py and its archipelago.json as __world__.json beside the subpackage's own __init__.py;
- in the source tree (no __world__.py there), in the world's own folder, Archipelago/worlds/<name>, found without
  importing it, so that the tree holds no copy. The subpackage then takes that folder's path and __init__.py's file
  name (pkgutil.get_data finds the world's assets by them).
The same code runs either way; only where it reads from differs.
"""

import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Tuple

from worlds import LauncherComponents
from worlds.AutoWorld import AutoWorldRegister

WORLD_INIT = "__world__.py"
WORLD_MANIFEST = "__world__.json"


def _within(module: str, package: str) -> bool:
    """Whether the module `module` is the package `package` or one of its submodules."""
    return module == package or module.startswith(package + ".")


def _read(loader: Any, path: str) -> bytes:
    """A file through a package's loader: a folder's or a zip's (zipimporter.get_data takes paths inside it)."""
    return loader.get_data(path)


def _files(package: Any, world: str) -> Tuple[str, str, bytes, Dict[str, Any]]:
    """(folder, path of the world's __init__, its source, its manifest) for the carried world."""
    own = os.path.dirname(package.__file__)
    loader = package.__spec__.loader
    try:
        source = _read(loader, os.path.join(own, WORLD_INIT))
    except OSError:
        pass
    else:
        manifest = json.loads(_read(loader, os.path.join(own, WORLD_MANIFEST)))
        return own, os.path.join(own, WORLD_INIT), source, manifest
    spec = importlib.util.find_spec(f"worlds.{world}")
    if spec is None or not spec.submodule_search_locations:
        raise ImportError(f"{package.__name__}: no carried files and no world worlds.{world} to read them from")
    folder = list(spec.submodule_search_locations)[0]
    source = _read(spec.loader, spec.origin)
    manifest = json.loads(_read(spec.loader, os.path.join(folder, "archipelago.json")))
    return folder, spec.origin, source, manifest


def carry(name: str, world: str, game: str) -> type:
    """Run the world `world` (its folder's name; its game `game`) as the package `name`, which is being imported, and
    give back its World class."""
    package = sys.modules[name]
    folder, init_path, source, manifest = _files(package, world)
    if manifest.get("game") != game:
        raise ImportError(f"{name}: the world carried is {manifest.get('game')!r}, not {game!r}")
    package.__path__ = [folder]
    package.__file__ = init_path
    registry: Dict[str, type] = {}
    components: List[Any] = []
    saved = AutoWorldRegister.world_types, LauncherComponents.components, LauncherComponents.icon_paths
    AutoWorldRegister.world_types = registry
    LauncherComponents.components = components
    LauncherComponents.icon_paths = {}
    try:
        exec(compile(source, init_path, "exec"), package.__dict__)
    finally:
        AutoWorldRegister.world_types, LauncherComponents.components, LauncherComponents.icon_paths = saved
    # A module the carried world imports for the first time registers into the stand-ins too: the generic world
    # ("Archipelago", worlds/generic), which a world's rules import, when no world loaded before this one imported it
    # (Archipelago loads the worlds in name order, and an AP_TEST_WORLDS run may load none of them; an installed
    # apworld loads after every built-in world). That registration is a real one: it goes to Archipelago's registry and
    # Launcher. Only what the carried world's own modules define stays out.
    ours = {key: cls for key, cls in registry.items() if _within(cls.__module__, name)}
    for key, cls in registry.items():
        if key not in ours:
            AutoWorldRegister.world_types.setdefault(key, cls)
    for component in components:
        func = getattr(component, "func", None)
        if func is not None and not _within(getattr(func, "__module__", None) or "", name):
            LauncherComponents.components.append(component)
    if list(ours) != [game]:
        raise ImportError(f"{name}: running {world}'s __init__ made the worlds {sorted(ours)}, not {game!r} alone")
    world_class = ours[game]
    from Utils import tuplize_version
    world_class.world_version = tuplize_version(manifest.get("world_version", "0.0.0"))
    world_class.manifest = manifest
    return world_class
