import json


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

class Bpm():
	"""
	A class used to store the bpm information

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. The full list of parameters is Bpm.parameters
	girder: int
		The girder id, the element is on
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

	def __init__(self, in_parameters, girder = None, index = None, elem_type = "Bpm"):
		self.settings = _extract_dict(self.parameters, in_parameters)
		for x in self._float_params:
			if x in self.settings:
				self.settings[x] = float(self.settings[x])
		for x in self._int_params:
			if x in self.settings:
				self.settings[x] = int(self.settings[x])
		if not 'length' in self.settings:
			self.settings['length'] = 0.0
		#setting default values
		for x in self._cached_parameters:
			if not x in self.settings:
				self.settings[x] = 0.0
		self.girder, self.index, self.type, self._cached_data = girder, index, elem_type, None

	def __repr__(self):
		return f"Bpm({self.settings}, {self.girder}, {self.index}, '{self.type}')"

	def __str__(self):
		return f"Bpm({json.dumps(self.settings, indent = 4)})"
	
	def to_placet(self) -> str:
		res = "Bpm"
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
