import json


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

class Quadrupole():
	"""
	A class used to store the quadrupole information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Quadrupole.parameters
	girder: int
		The girder id, the element is on
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

	def __init__(self, in_parameters, girder = None, index = None):
		self.settings = _extract_dict(self.parameters, in_parameters)
		for x in self._float_params:
			if x in self.settings:
				self.settings[x] = float(self.settings[x])
		for x in self._int_params:
			if x in self.settings:
				self.settings[x] = int(self.settings[x])
		if not 'length' in self.settings:
			self.settings['length'] = 0.0
		self.girder, self.index, self.type, self._cached_data = girder, index, "Quadrupole", None

	def __repr__(self):
		return f"Quadrupole({self.settings}, {self.girder}, {self.index}, '{self.type}')"

	def __str__(self):
		return f"Quadrupole({json.dumps(self.settings, indent = 4)})"

	def to_placet(self) -> str:
		res = "Quadrupole"
		_to_str = lambda x: f"\"{x}\"" if isinstance(x, str) else x
		for key in self.settings:
			res += f" -{key} {_to_str(self.settings[key])}"
		return res

	def cache_data(self):
		self._cached_data = {}
		for key in self._cached_parameters:
			self._cached_data[key] = self.settings[key]

	def use_cached_data(self, clear_cache = False):
		assert self._cached_data is not None, "No data in cache"
		for key in self._cached_parameters:
			self.settings[key] = self._cached_data[key]
		if clear_cache:
			self._cached_data = None
