from typing import Optional
from placetmachine.lattice.element import Element


class Dipole(Element):
	"""
	A class used to store the dipole information.

	Attributes
	----------
	settings : dict
		Dictionary containing the element settings.
	girder : int
		The girder id, the element is on.
	type: str
		The type of the element. It is set to "Dipole".

	**The list of acceptable settings:**
	```
	["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dum", 
	"thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"aperture_shape", "strength_x", "strength_y", "hcorrector", 
	"hcorrector_step_size", "vcorrector", "vcorrector_step_size", "tclcall_entrance", 
	"tclcall_exit", "short_range_wake"]
	```
	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dum", "thin_lens", "e0", "aperture_x", "aperture_y", 
	"aperture_losses", "aperture_shape", "strength_x", "strength_y", "hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size", 
	"tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "strength_x", "strength_y", 
	"hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	_int_params = ["synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['strength_x', 'strength_y']

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
		super(Dipole, self).__init__(in_parameters, girder, index, "Dipole")
