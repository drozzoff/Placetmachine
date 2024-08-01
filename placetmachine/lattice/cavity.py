from numpy import radians, degrees
from typing import Optional
from placetmachine.lattice.element import Element


class Cavity(Element):
	"""
	A class used to store the cavity information.

	Attributes
	----------
	settings : dict
		Dictionary containing the element settings.
	girder : Optional[Girder]
		The girder reference the `Element` is placed on. This parameter is only relevant when being the part of the lattice.
		Upon creation is set to `None`.
	type : str
		The type of the element. It is set to "Cavity".

	**The list of acceptable settings:**
	```
	["name", "comment", "s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", 
	"length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", 
	"aperture_losses", "aperture_shape", "tclcall_entrance", "tclcall_exit", 
	"short_range_wake", "gradient", "phase", "type", "lambda", "frequency", 
	"bookshelf_x", "bookshelf_y", "bookshelf_phase", "bpm_offset_x", "bpm_offset_y", 
	"bpm_reading_x", "bpm_reading_y", "dipole_kick_x", "dipole_kick_y", "pi_mode"]
	```
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

	def __init__(self, in_parameters: Optional[dict] = None, index: Optional[int] = None, **extra_params):
		"""
		Parameters
		----------
		in_parameters
			The dict with input settings.
		girder
			The number of the girder element is placed.
		index
			The index of the element in the lattice.

		Other parameters
		----------------
		angle : bool
			If `True` (default is `True`), the phase is given in degrees, otherwise radians.
		"""
		super(Cavity, self).__init__(in_parameters, index, "Cavity")
		if extra_params.get('angle', True):
			self.settings['phase'] = radians(float(self.settings['phase']))

	def to_placet(self) -> str:
		"""
		Convert the element to a Placet readable format.

		Returns
		-------
		str
			The string containing the element
		"""
		res = "Cavity"
		_to_str = lambda x: f"\"{x}\"" if isinstance(x, str) else x
		for key in self.settings:
			if key == "phase":
				res += f" -{key} {_to_str(degrees(self.settings[key]))}"
			else:
				res += f" -{key} {_to_str(self.settings[key])}"
		return res

	@classmethod
	def duplicate(cls, initial_instance):
		return cls(initial_instance.settings, initial_instance.index, angle = False)