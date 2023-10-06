from placetmachine.lattice.element import Element


class Bpm(Element):
	"""
	A class used to store the bpm information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Bpm.parameters
	girder: int
		The girder id, the element is on. This parameter is only relevant when being the part of the lattice.
	type: str, default "Bpm"
		The type of the element. Defaults to "Bpm"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", 
	"aperture_x", "aperture_y", "aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", "short_range_wake", "resolution", 
	"reading_x", "reading_y", "transmitted_charge", "scale_x", "scale_y", "store_bunches", "hcorrector", "hcorrector_step_size", "vcorrector", 
	"vcorrector_step_size"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"resolution", "reading_x", "reading_y", "transmitted_charge", "scale_x", "scale_y", "hcorrector_step_size", "vcorrector_step_size"]
	_int_params = ["store_bunches", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp']

	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
		super(Bpm, self).__init__(in_parameters, girder, index, "Bpm")
