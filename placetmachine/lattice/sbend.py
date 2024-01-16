from typing import Optional

from placetmachine.lattice.element import Element


class Sbend(Element):
	"""
	A class used to store the sbend information

	Attributes
	----------
	settings : dict
		Dictionary containing the element settings.
	girder : int
		The girder id, the element is on.
	type : str
		The type of the element. It is set to "Sbend".

	**The list of acceptable settings:**
	```
	["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", 
	"thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"aperture_shape", "angle", "E1", "E2", "K", "K2", "tilt", "tclcall_entrance", 
	"tclcall_exit", "short_range_wake"]
	```
	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape", "angle", "E1",
	"E2", "K", "K2", "tilt", "tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "angle", "E1", "E2", "K", "K2", "tilt"]
	_int_params = ["synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp']

	def __init__(self, in_parameters: Optional[dict] = None, girder: Optional[int] = None, index: Optional[int] = None):
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
		super(Sbend, self).__init__(in_parameters, girder, index, "Sbend")
