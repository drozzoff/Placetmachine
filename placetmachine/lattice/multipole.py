from typing import Optional
from placetmachine.lattice.element import Element


class Multipole(Element):
	"""
	A class used to store the Multipole information.

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings.
	girder : Optional[Girder]
		The girder reference the `Element` is placed on. This parameter is only relevant when being the part of the lattice.
		Upon creation is set to `None`.
	type: str
		The type of the element. It is set to "Multipole".

	**The list of acceptable settings:**
	```
	["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", 
	"thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"aperture_shape", "strength", "type", "steps", "tilt", "tclcall_entrance", 
	"tclcall_exit", "short_range_wake"]
	```
	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape",
	"strength", "type", "steps", "tilt", "tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "strength", "tilt"]
	_int_params = ["type", "steps", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll']

	def __init__(self, in_parameters: Optional[dict] = None, index: Optional[int] = None):
		"""
		Parameters
		----------
		in_parameters
			The dict with input settings.
		girder
			The number of the girder element is placed.
		index
			The index of the element in the lattice.
		"""
		super(Multipole, self).__init__(in_parameters, index, "Multipole")