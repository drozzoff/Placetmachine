from typing import Optional
from placetmachine.lattice.element import Element


class Quadrupole(Element):
	"""
	A class used to store the quadrupole information.

	Attributes
	----------
	settings : dict
		Dictionary containing the element settings.
	girder : int
		The girder id, the element is on. This parameter is only relevant when being the part of the lattice.
	type : str
		The type of the element. It is set to "Quadrupole".

	**The list of acceptable settings:**
	```
	["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", 
	"length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", 
	"aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", 
	"short_range_wake", "strength", "Kn", "type", "hcorrector", 
	"hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	```
	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape", 
	"tclcall_entrance", "tclcall_exit", "short_range_wake", "strength", "Kn", "type", "hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "aperture_x", "aperture_y", "aperture_losses", "strength", "Kn", "hcorrector_step_size", "vcorrector_step_size"]
	_int_params = ["type", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll', 'strength']

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
		super(Quadrupole, self).__init__(in_parameters, girder, index, "Quadrupole")
