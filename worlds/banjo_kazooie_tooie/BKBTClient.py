"""The Banjo-Kazooie & Tooie client: one slot of the combined world, both games of the dual-boot image
(roms/bkbt2-normal.z64) in one emulator.

One emulator connection, and on it, every 0.2 s, whichever game runs (client/resident.py):
- while Tooie runs, the stock Tooie client's monitor (client/bridge.py) gives Tooie the slot's settings and items
  and sends Tooie's checks;
- while Banjo-Kazooie runs, the Banjo-Kazooie client's poll (worlds/banjo_kazooie/BKClient.py) gives BK its items,
  the shared moves among them (client/items.py), and sends BK's checks;
- between the two, nothing.
Each game's goal is kept on the server as it is reached; the slot's goal (the yaml setting goal) is sent once its
games' goals are in (client/goal.py).

Start it from the Archipelago Launcher ("Banjo-Kazooie & Tooie Client"). docs/DEVELOPMENT.md has how to play.
"""

import asyncio
import json
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Set, Tuple

import Utils
from CommonClient import get_base_parser, gui_enabled, handle_url_arg, logger, server_loop
from NetUtils import ClientStatus
from Utils import async_start

from .bk import BKClient, BanjoKazooieWorld
from .bk.client import hack, ids, rom
from .bk.client.emu import load as load_emu_loader
from .bk.client.link import LinkDriver, Sent
from .bk.patch import make

load_emu_loader()       # before BTClient's `from emu_loader import ...`: without the package, the BK world's copy
from .bt import BTClient, BanjoTooieWorld

from . import Entrances as Doors, Moves
from .client import bridge, goal, items, traps
from .client.resident import BK, TOOIE

POLL = 0.2              # seconds between two looks at the game, as both games' clients
ATTACH_RETRY = 2.0      # seconds between two searches for an emulator running the image
RESCAN_AFTER = 60.0     # seconds of no game at the attached RAM before looking for it again (a ROM reloaded)
ITEMS_GRACE = 1.0       # seconds after Connected to wait for ReceivedItems before BK writes without any
GAME_NAMES = {TOOIE: "Banjo-Tooie", BK: "Banjo-Kazooie", None: "neither game"}


def image_target(version: str) -> rom.Target:
    """The dual-boot image (roms/bkbt2-normal.z64 of a build), from retail Banjo-Kazooie and Banjo-Tooie with the BK
    world's patch and this world's (patch/make.py; tools/make_patches.py writes them)."""
    package = "worlds.banjo_kazooie_tooie"
    bk_patch, bk_info = rom.bk_patch_files()
    tooie_patch = rom.world_asset(package, "tooie.bsdiff4")
    payload = rom.world_asset(package, "bk-payload.bin")
    info_block = rom.world_asset(package, "bkbt-info.bin")
    info = json.loads(rom.world_asset(package, "image-patch.json"))

    def build(roms: Dict[str, bytes]) -> bytes:
        if info["bk_rom_sha1"] != bk_info["rom_sha1"]:
            raise make.PatchError("the Banjo-Kazooie world this world carries is not the one its image was made with "
                                  "(a broken build: tools/make_apworlds.py)")
        bk = make.bk_rom(roms["bk_rom_path"], bk_patch, bk_info)
        tooie = make.tooie_rom(roms["tooie_rom_path"], tooie_patch, info["tooie"])
        return make.dualboot_image(bk, tooie, payload, info_block, info)

    sources = (
        rom.Source("bk_rom_path", "Banjo-Kazooie (USA)", make.bkrom.check_retail,
                   ((BanjoKazooieWorld.settings, "rom_path"),)),
        rom.Source("tooie_rom_path", "Banjo-Tooie (USA)", make.check_tooie_retail,
                   ((BanjoTooieWorld.settings, "rom_path"),)),
    )
    return rom.Target("Banjo-Kazooie & Tooie", f"Banjo-Kazooie & Tooie AP {version}.z64", info["image_sha1"], sources,
                      build, 15)


class BanjoKazooieTooieCommandProcessor(rom.RomCommands):
    ctx: "BanjoKazooieTooieContext"

    def _cmd_bk_rom_path(self, path: str = "") -> bool:
        """Set (or, with no argument, unset) the file path of your Banjo-Kazooie (USA) ROM, which /patch makes the
        image from."""
        return self.set_rom_path("bk_rom_path", "Banjo-Kazooie (USA)", path)

    def _cmd_tooie_rom_path(self, path: str = "") -> bool:
        """Set (or, with no argument, unset) the file path of your Banjo-Tooie (USA) ROM, which /patch makes the
        image from."""
        return self.set_rom_path("tooie_rom_path", "Banjo-Tooie (USA)", path)

    def _cmd_deathlink(self) -> bool:
        """Turn death link on or off for this session, in both games (the slot's setting is the start)."""
        ctx = self.ctx
        ctx.deathlink_client_override = True
        ctx.deathlink_enabled = not ctx.deathlink_enabled
        async_start(ctx.update_death_link(ctx.deathlink_enabled), name="death link")
        logger.info(f"Death link {'on' if ctx.deathlink_enabled else 'off'}.")
        return True

    def _cmd_taglink(self) -> bool:
        """Turn tag link on or off for this session, in both games (the slot's setting is the start)."""
        ctx = self.ctx
        ctx.taglink_client_override = True
        ctx.taglink_enabled = not ctx.taglink_enabled
        async_start(ctx.update_tag_link(ctx.taglink_enabled), name="tag link")
        logger.info(f"Tag link {'on' if ctx.taglink_enabled else 'off'}.")
        return True

    def _cmd_game(self) -> bool:
        """Show which game runs and the emulator."""
        logger.info(f"Emulator: {self.ctx.emu_status}; running: {GAME_NAMES[self.ctx.resident_now]}")
        return True

    def _cmd_goal(self) -> bool:
        """Show the slot's goal and the games' goals reached."""
        ctx = self.ctx
        wanted = goal.needed(ctx.slot_data.get("goal", 0)) if ctx.slot_data else frozenset()
        logger.info(f"Goal: {' and '.join(GAME_NAMES[g] for g in sorted(wanted)) or 'not connected'}; "
                    f"reached: {', '.join(GAME_NAMES[g] for g in sorted(ctx.goals())) or 'none'}; "
                    f"sent: {'yes' if ctx.finished_game else 'no'}")
        return True

    def _cmd_bk(self) -> bool:
        """Show what Banjo-Kazooie's hack gets and shows."""
        ctx = self.ctx
        last = ctx.link.last
        logger.info(f"Banjo-Kazooie: {last.state}: {last.reason}; gives: {hack.describe(ctx.wanted_items())}")
        logger.info(f"Checks the game shows: {len(last.checks)}; sent this session: {len(ctx.sent)}")
        cross = (ctx.slot_data or {}).get("cross_world_entrances") or {}
        moved = [f"{door} -> {world}" for door, world in cross.items() if door != world]
        if moved:
            logger.info("World doors of both games: " + "; ".join(moved))
        logger.info(ctx.link_driver.describe())
        shares = ctx.shares.to_storage() if ctx.shares else "not read from the server yet"
        logger.info(f"Traps by kind (trip, slip, transform, squish, tip) given to each game: {shares}")
        return True


class BanjoKazooieTooieContext(BTClient.BanjoTooieContext):
    command_processor = BanjoKazooieTooieCommandProcessor

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)
        from .Names import GAME
        self.game = GAME
        self.tab_items = SimpleNamespace(content=SimpleNamespace(data=[]))  # the GUI's Items tab replaces it
        self.loader: Optional[bridge.SharedLoader] = None
        self.resident_now: Optional[str] = None
        self.tooie_task: Optional[asyncio.Task] = None
        self.emulator_task: Optional[asyncio.Task] = None
        self.reached: Set[str] = set()          # goals seen this session (the server keeps them, goal.storage_key)
        self.chains: Moves.Chains = {}
        # what BKClient.poll uses
        self.link = hack.Link()
        self.last_state: Optional[str] = None
        self.told: Set[Any] = set()
        self.sent: Set[int] = set()
        self.connected_at = 0.0
        self.items_ready = False
        # BK's half of the link (deaths, tags, traps: client/link.py), and the traps' split between the games
        # (client/traps.py), read from the server at Connected
        self.link_driver = LinkDriver()
        self.shares: Optional[traps.TrapShares] = None
        bridge.install(lambda: self.loader, lambda: async_start(self.reach_goal(TOOIE)), self.tooie_items)

    @property
    def rom_settings(self) -> Any:
        """This world's settings in host.yaml (its BanjoKazooieTooieSettings), read when first needed."""
        from . import BanjoKazooieTooieWorld
        return BanjoKazooieTooieWorld.settings

    def rom_target(self) -> rom.Target:
        from . import BanjoKazooieTooieWorld
        return image_target(BanjoKazooieTooieWorld.world_version.as_simple_string())

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super(BTClient.BanjoTooieContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: Dict[str, Any]) -> None:
        super().on_package(cmd, args)       # Tooie's: its version check, the tracker, death link
        if cmd == "Connected":
            self.connected_at = time.monotonic()
            self.items_ready = False
            self.sent.clear()
            self.chains = Moves.slot_chains(self.slot_data)
            bk = self.slot_data.get("bk") or {}
            if not isinstance(bk.get("seed"), int):
                logger.error("This slot has no Banjo-Kazooie data: it was not generated by the Banjo-Kazooie & "
                             "Tooie world.")
            layout = tuple(bk.get("layout") or ())
            if layout and layout > hack.WANT:
                logger.warning(f"This slot was generated for layout {'.'.join(map(str, layout))} of the BK hack; "
                               f"this client knows {hack.WANT[0]}.{hack.WANT[1]}. Update the apworld.")
            self.shares = None
            self.set_notify(self.goal_key(), self.trap_key())
            async_start(self.check_goal())
        elif cmd == "ReceivedItems":
            self.items_ready = True
        elif cmd in ("Retrieved", "SetReply"):
            if self.shares is None and self.slot is not None:
                key = self.trap_key()
                if cmd == "Retrieved":
                    keys = args.get("keys") or {}
                    known, stored = key in keys, keys.get(key)      # None: nothing stored yet
                else:
                    known, stored = args.get("key") == key, args.get("value")
                if known:
                    self.shares = traps.TrapShares(stored)
                    self.emu_last_items_count = -1     # the stock code writes Tooie's items again, with its share
            async_start(self.check_goal())

    def run_gui(self) -> None:
        from kvui import GameManager, UILog

        class BanjoKazooieTooieManager(GameManager):
            logging_pairs = [("Client", "Archipelago")]
            base_title = "Archipelago Banjo-Kazooie & Tooie Client"

            def build(self):
                built = super().build()
                self.ctx.tab_items = self.add_client_tab("Items", UILog())
                return built

        self.ui = BanjoKazooieTooieManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    # -- the goal ---------------------------------------------------------------------------------------------

    def goal_key(self) -> str:
        return goal.storage_key(self.team, self.slot)

    def goals(self) -> Set[str]:
        stored = self.stored_data.get(self.goal_key()) if self.slot is not None else None
        return self.reached | {game for game, done in (stored or {}).items() if done}

    async def reach_goal(self, game: str) -> None:
        if game in self.reached:
            return
        self.reached.add(game)
        logger.info(f"{GAME_NAMES[game]}'s goal is reached.")
        if self.slot is not None:
            await super().send_msgs([{"cmd": "Set", "key": self.goal_key(), "default": {}, "want_reply": True,
                                      "operations": [{"operation": "update", "value": {game: True}}]}])
        await self.check_goal()

    def goal_met(self) -> bool:
        return bool(self.slot_data) and goal.met(self.slot_data.get("goal", 0), self.goals())

    async def check_goal(self) -> None:
        if self.slot is not None and not self.finished_game and self.goal_met():
            self.finished_game = True
            await super().send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            logger.info("The slot's goal is reached: goal sent.")

    async def send_msgs(self, msgs) -> None:
        # Only check_goal sends the goal: hold back any other (the stock Tooie code's, CommonClient's) before.
        msgs = [msg for msg in msgs if not (msg.get("cmd") == "StatusUpdate"
                                            and msg.get("status") == ClientStatus.CLIENT_GOAL and not self.goal_met())]
        if msgs:
            await super().send_msgs(msgs)

    # -- what BKClient.poll asks -------------------------------------------------------------------------------

    def bk_data(self) -> Dict[str, Any]:
        return self.slot_data.get("bk") or {} if self.slot_data else {}

    def slot_seed(self) -> Optional[int]:
        if self.slot is None or not self.slot_data:
            return None
        if not self.items_ready and time.monotonic() - self.connected_at < ITEMS_GRACE:
            return None
        seed = self.bk_data().get("seed")
        return seed if isinstance(seed, int) and 0 < seed <= 0xFFFFFFFF else None

    def wanted_items(self) -> hack.Items:
        """BK's items, with BK's share of Tooie's nests as refills: an Egg Nest fills the blue eggs, a Feather Nest the
        less full feather (client/traps.py). Only reads the shares (bk_traps, in BK's poll, takes the nests no game
        has yet): /bk asks for this while Tooie runs too. Before the shares are read the refills are 0, which the hack
        takes as behind its count and ignores."""
        wanted, _skipped = items.bk_items((item.item for item in self.items_received), self.chains)
        if self.shares is not None:
            share = self.shares.share("bk")
            wanted = wanted._replace(refills=(share[traps.EGG_NEST], 0, 0, share[traps.FEATHER_NEST]))
        return wanted

    def bk_settings(self) -> Tuple[bool, bool, bool]:
        bk = self.bk_data()
        return (bool(bk.get("skip_intro", True)), bool(bk.get("notesanity", False)),
                bool(bk.get("skip_lair_cutscene", True)))

    def bk_exits(self) -> Optional[List[hack.Exit]]:
        """The exit map for BK's world doors: with the doors across the games (the slot data's
        "cross_world_entrances"), BK's half of their exit maps, entries into Tooie included (Entrances.py); else BK's
        own doors (its slot data's "world_entrances"), as BKClient's."""
        try:
            cross = (self.slot_data or {}).get("cross_world_entrances")
            if cross:
                return [hack.Exit(*entry) for entry in Doors.cross_exit_maps(cross)[0]]
            return ids.exits_of(self.bk_data().get("world_entrances"))
        except ValueError as exc:
            if ("exits", str(exc)) not in self.told:
                self.told.add(("exits", str(exc)))
                logger.error(f"This slot's Banjo-Kazooie world doors are not a world behind each door ({exc}): "
                             f"generate it again.")
            return None

    async def bk_goal(self) -> None:
        await self.reach_goal(BK)

    # -- the link: deaths and tags go to the game running, traps and nests are split (client/traps.py) -------

    def trap_key(self) -> str:
        return traps.storage_key(self.team, self.slot)

    def _save_shares(self) -> None:
        async_start(super().send_msgs([{"cmd": "Set", "key": self.trap_key(), "default": {}, "want_reply": False,
                                        "operations": [{"operation": "replace", "value": self.shares.to_storage()}]}]))

    def _take_traps(self, game: str, item_ids) -> bool:
        if self.shares is not None and self.shares.take(game, traps.received(item_ids)):
            self._save_shares()
        return self.shares is not None

    def tooie_items(self, items_received) -> Optional[List[Any]]:
        """The items as the stock Tooie code should write them: with Tooie's share of the traps and nests (those no
        game has yet become Tooie's). None until the shares are read."""
        items_received = list(items_received)
        if not self._take_traps("tooie", (item.item for item in items_received)):
            return None
        return self.shares.for_tooie(items_received)

    def bk_traps(self) -> Optional[Tuple[int, ...]]:
        """BK's share of the traps, the traps and nests no game has yet becoming BK's (BK's poll asks only while BK
        runs; the nests reach the game through wanted_items). None until the shares are read."""
        if not self._take_traps("bk", (item.item for item in self.items_received)):
            return None
        return self.shares.share("bk")[:traps.TRAP_KINDS]

    def bk_link_inbox(self) -> None:
        """A death or tag received (Tooie's code keeps them, BTClient.py:476-481, :593-601) goes to BK while BK runs."""
        if getattr(self, "deathlink_enabled", False) and self.deathlink_pending:
            self.deathlink_pending = False
            self.link_driver.owe(deaths=1)
        if getattr(self, "taglink_enabled", False) and getattr(self, "pending_tag_link", False):
            self.pending_tag_link = False
            self.link_driver.owe(tags=1)

    async def bk_link_sent(self, sent: Sent) -> None:
        """Banjo's deaths and his D-pad left swaps in BK, sent as Tooie's code sends its own."""
        for _ in range(sent.deaths):
            if getattr(self, "deathlink_enabled", False):
                await self.send_death(f"{self.player_names.get(self.slot, 'Banjo')} fell in Banjo-Kazooie.")
        for _ in range(sent.tags):
            if getattr(self, "taglink_enabled", False):
                await self.send_tag_link()

    def bk_left(self) -> None:
        """BK is not running: what it was given and did not apply goes to whichever game runs next (Tooie's code
        takes its pending death or tag)."""
        deaths, tags = self.link_driver.leave()
        if deaths:
            self.deathlink_pending = True
        if tags:
            self.pending_tag_link = True

    # -- the two halves ----------------------------------------------------------------------------------------

    def start_tooie(self) -> None:
        if self.version_warning:
            return      # the stock monitor stopped on a Tooie ROM of another version, and said so
        if self.tooie_task is None or self.tooie_task.done():
            self.tooie_task = asyncio.create_task(BTClient.emu_loader_monitor_task(self), name="Tooie half")

    async def stop_tooie(self) -> None:
        task, self.tooie_task = self.tooie_task, None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


async def emulator_loop(ctx: BanjoKazooieTooieContext) -> None:
    loop = asyncio.get_running_loop()
    logger.info("Looking for an emulator running the dual-boot image (Project64 or ares).")
    while not ctx.exit_event.is_set():
        ctx.emu_status = "looking for an emulator running the image"
        loader = await loop.run_in_executor(None, bridge.SharedLoader)
        while not loader.is_connected() and not ctx.exit_event.is_set():
            await asyncio.sleep(ATTACH_RETRY)
            await loop.run_in_executor(None, loader.connect)
        if ctx.exit_event.is_set():
            break
        ctx.loader = ctx.emu_loader = loader
        name = getattr(loader.emulator_info, "readable_emulator_name", "an emulator")
        ctx.emu_status = f"attached to {name}"
        logger.info(f"Attached to {name}.")
        ctx.link = hack.Link()
        ctx.last_state = None
        away_since = None
        try:
            while not ctx.exit_event.is_set() and loader.is_connected():
                who = loader.resident()
                if who != ctx.resident_now:
                    ctx.resident_now = who
                    logger.info(f"Running: {GAME_NAMES[who]}.")
                if who != BK:
                    ctx.bk_left()
                if who == TOOIE:
                    ctx.start_tooie()
                else:
                    await ctx.stop_tooie()
                if who == BK:
                    await BKClient.poll(ctx, loader)
                now = time.monotonic()
                away_since = (away_since or now) if who is None else None
                if away_since is not None and now - away_since > RESCAN_AFTER:
                    logger.info("Neither game at the attached memory for a minute: looking for the emulator again.")
                    break
                await asyncio.sleep(POLL)
        except Exception as e:
            logger.exception(f"Lost the emulator ({e}); looking for it again.", extra={"compact_gui": True})
        await ctx.stop_tooie()
        try:
            loader.disconnect()
        except Exception:
            pass
        ctx.loader = ctx.emu_loader = None
        ctx.resident_now = None
        ctx.emu_status = "not attached"
        ctx.link = hack.Link()
        await asyncio.sleep(1.0)


def main(*args: str) -> None:
    Utils.init_logging("BanjoKazooieTooieClient", exception_logger="Client")
    parser = get_base_parser(description="Banjo-Kazooie & Tooie client: the dual-boot image in an emulator.")
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    parsed = handle_url_arg(parser.parse_args(args), parser=parser)

    async def _main() -> None:
        ctx = BanjoKazooieTooieContext(parsed.connect, parsed.password)
        ctx.auth = parsed.name
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        ctx.emulator_task = asyncio.create_task(emulator_loop(ctx), name="emulator loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        async_start(rom.patch_and_run(ctx.rom_settings, ctx.rom_target()), name="patch")
        await ctx.exit_event.wait()
        ctx.server_address = None
        await ctx.shutdown()
        for task in (ctx.emulator_task, ctx.n64_sync_task):
            if task is not None:
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(_main())
    colorama.deinit()


if __name__ == "__main__":
    main()
