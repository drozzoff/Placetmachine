from .element import Element


class Sbend(Element):
	"""
	A class used to store the sbend information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Sbend.parameters
	girder: int
		The girder id, the element is on
	type: str, default "Sbend"
		The type of the element. Defaults to "Sbend"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape", "angle", "E1",
	"E2", "K", "K2", "tilt", "tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "angle", "E1", "E2", "K", "K2", "tilt"]
	_int_params = ["synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp']

	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
		super(Sbend, self).__init__(in_parameters, girder, index, "Sbend")
