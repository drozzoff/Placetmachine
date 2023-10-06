from placetmachine.lattice.element import Element


class Quadrupole(Element):
	"""
	A class used to store the quadrupole information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Quadrupole.parameters
	girder: int
		The girder id, the element is on. This parameter is only relevant when being the part of the lattice.
	type: str, default "Quadrupole"
		The type of the element. Defaults to "Quadrupole"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses", "aperture_shape", 
	"tclcall_entrance", "tclcall_exit", "short_range_wake", "strength", "Kn", "type", "hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "aperture_x", "aperture_y", "aperture_losses", "strength", "Kn", "hcorrector_step_size", "vcorrector_step_size"]
	_int_params = ["type", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll']

	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
		super(Quadrupole, self).__init__(in_parameters, girder, index, "Quadrupole")
