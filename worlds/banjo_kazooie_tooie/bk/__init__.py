"""The Banjo-Kazooie world, carried: its own __init__.py runs here as this package's code, and its modules are this
package's (carried.py). The combined world imports BK's code only from here."""

from ..carried import carry

carry(__name__, "banjo_kazooie", "Banjo-Kazooie")
