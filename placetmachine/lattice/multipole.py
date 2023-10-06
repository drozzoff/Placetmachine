from placetmachine.lattice.element import Element


class Multipole(Element):
	"""
	A class used to store the Multipole information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Multipole.parameters
	girder: int
		The girder id, the element is on
	type: str, default "Multipole"
		The type of the element. Defaults to "Multipole"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape",
	"strength", "type", "steps", "tilt", "tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "strength", "tilt"]
	_int_params = ["type", "steps", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll']

	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
		super(Multipole, self).__init__(in_parameters, girder, index, "Multipole")