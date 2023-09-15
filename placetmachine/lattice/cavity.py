from numpy import radians, degrees
from .element import Element


class Cavity(Element):
	"""
	A class used to store the cavity information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Cavity.parameters
	girder: int
		The girder id, the element is on
	type: str, default "Cavity"
		The type of the element. Defaults to "Cavity"

	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format

	"""
	parameters = ["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", 
	"aperture_x", "aperture_y", "aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", "short_range_wake", "gradient", "phase", 
	"type", "lambda", "frequency", "bookshelf_x", "bookshelf_y", "bookshelf_phase", "bpm_offset_x", "bpm_offset_y", "bpm_reading_x", 
	"bpm_reading_y", "dipole_kick_x", "dipole_kick_y", "pi_mode"]
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "e0", "aperture_x", "aperture_y", "aperture_losses", 
	"gradient", "phase", "lambda", "frequency", "bookshelf_x", "bookshelf_y", "bookshelf_phase", "bpm_offset_x", "bpm_offset_y",  "bpm_reading_x", 
	"bpm_reading_y", "dipole_kick_x", "dipole_kick_y", "pi_mode"]
	_int_params = ["type", "synrad", "thin_lens", "six_dim"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'bpm_offset_y', 'bpm_offset_x', 'gradient', 'phase']

	def __init__(self, in_parameters = None, girder = None, index = None, **extra_params):
		super(Cavity, self).__init__(in_parameters, girder, index, "Cavity")
		if extra_params.get('angle', True):
			self.settings['phase'] = radians(float(self.settings['phase']))

	def to_placet(self) -> str:
		res = "Cavity"
		_to_str = lambda x: f"\"{x}\"" if isinstance(x, str) else x
		for key in self.settings:
			if key == "phase":
				res += f" -{key} {_to_str(degrees(self.settings[key]))}"
			else:
				res += f" -{key} {_to_str(self.settings[key])}"
		return res
