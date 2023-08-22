from .element import Element


class Drift(Element):
	"""
	A class used to store the drift information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Drift.parameters
	girder: int
		The girder id, the element is on
	type: str, default "Drift"
		The type of the element. Defaults to "Drift"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape", 
	"tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "e0", "aperture_x", "aperture_y", "aperture_losses"]
	_int_params = ["synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp']

	def __init__(self, in_parameters: dict, girder: int = None, index: int = None):
		super(Drift, self).__init__(in_parameters, girder, index, "Drift")
