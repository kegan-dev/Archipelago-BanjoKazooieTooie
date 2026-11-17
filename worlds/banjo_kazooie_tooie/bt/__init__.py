"""jjjj12212's Banjo-Tooie world V4.13.1, carried: its own __init__.py runs here as this package's code, and its
modules are this package's (carried.py). The combined world imports Tooie's code only from here."""

from ..carried import carry

carry(__name__, "banjo_tooie", "Banjo-Tooie")
