from typing import Optional
from placetmachine.lattice.element import Element


class Bpm(Element):
	"""
	A class used to store the BPM information.

	Attributes
	----------
	settings : dict
		Dictionary containing the element settings.
	girder : int
		The girder id, the element is on. This parameter is only relevant when being the part of the lattice..
	type : str
		The type of the element. It is set to "Bpm".

	**The list of acceptable settings:**
	```
	["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", 
	"length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", 
	"aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", 
	"short_range_wake", "resolution", "reading_x", "reading_y", 
	"transmitted_charge", "scale_x", "scale_y", "store_bunches", "hcorrector", 
	"hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	```
	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", 
	"aperture_x", "aperture_y", "aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", "short_range_wake", "resolution", 
	"reading_x", "reading_y", "transmitted_charge", "scale_x", "scale_y", "store_bunches", "hcorrector", "hcorrector_step_size", "vcorrector", 
	"vcorrector_step_size"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"resolution", "reading_x", "reading_y", "transmitted_charge", "scale_x", "scale_y", "hcorrector_step_size", "vcorrector_step_size"]
	_int_params = ["store_bunches", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp']

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
		super(Bpm, self).__init__(in_parameters, index, "Bpm")
