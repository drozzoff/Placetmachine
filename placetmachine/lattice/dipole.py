from placetmachine.lattice.element import Element


class Dipole(Element):
	"""
	A class used to store the dipole information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Dipole.parameters
	girder: int
		The girder id, the element is on
	type: str, default "Dipole"
		The type of the element. Defaults to "Dipole"
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "length", "synrad", "six_dum", "thin_lens", "e0", "aperture_x", "aperture_y", 
	"aperture_losses", "aperture_shape", "strength_x", "strength_y", "hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size", 
	"tclcall_entrance", "tclcall_exit", "short_range_wake"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", "strength_x", "strength_y", 
	"hcorrector", "hcorrector_step_size", "vcorrector", "vcorrector_step_size"]
	_int_params = ["synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['strength_x', 'strength_y']

	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
		super(Dipole, self).__init__(in_parameters, girder, index, "Dipole")
