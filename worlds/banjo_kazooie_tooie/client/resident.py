"""Which game of the dual-boot image runs, from the Archipelago anchor both hacks publish at physical 0x400000.
Standard library only: tools/bt_dualboot_client.py loads this file by path, and tools/dualboot_roundtrip_check.py
takes resident() from there."""

from typing import Callable, Optional

ANCHOR = 0x400000           # physical RDRAM: BTHACK_ANCHOR_OFFSET (Archipelago-BanjoTooie/.../BTClient.py:30), BK's too
RDRAM_BASE = 0x80000000     # KSEG0; BTClient.py:28
RDRAM_SIZE = 0x800000       # 8 MiB, the Expansion Pak both hacks need; BTClient.py:29
BK_MAGIC = 0x424B4150       # 'BKAP', BKBT_AP_MAGIC (hack/bk/decomp/include/bkbt.h:458)

TOOIE = "tooie"
BK = "bk"


def is_rdram_pointer(word: int) -> bool:
    """A KSEG0 address in the 8 MiB of RDRAM, as the stock client's is_rdram_pointer (BTClient.py:70)."""
    return RDRAM_BASE <= word < RDRAM_BASE + RDRAM_SIZE


def resident(read_u32: Callable[[int], int]) -> Optional[str]:
    """Whose anchor the word at physical 0x400000 points to: TOOIE, BK, or None (0 around a switch, the IPL3's
    0xFFFFFFFF before a publication, anything else that is no RDRAM address). read_u32 takes a physical RDRAM
    address and returns the big-endian word there. Tooie's anchor struct starts with its version (a u16 major and
    two u8, client/state.py ANCHOR_VERSION), BK's with BK_MAGIC: a Tooie major of 0x424B would be version 16971."""
    word = read_u32(ANCHOR)
    if not is_rdram_pointer(word):
        return None
    return BK if read_u32(word - RDRAM_BASE) == BK_MAGIC else TOOIE
