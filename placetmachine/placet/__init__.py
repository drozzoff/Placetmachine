"""
	This is a module to communicate with Placet.

	It provides Python duplicates of the original TCL commands of Placet.

	The number of functions included in the module is constantly extended.

	The module uses [`Pexpect`](https://github.com/pexpect/pexpect).
"""

from placetmachine.placet.communicator import Communicator
from placetmachine.placet.pyplacet import Placetpy, PlacetCommand
from placetmachine.placet.placetwrap import Placet