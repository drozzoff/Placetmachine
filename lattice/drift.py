import json

_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

class Drift():
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
	_float_params = ["s", "x", "y", "xp", "yp", "roll", "tilt", "tilt_deg", "length", "synrad", "six_dim", "thin_lens", "e0", "aperture_x", "aperture_y", "aperture_losses"]
	_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll']

	def __init__(self, in_parameters, girder = None, index = None):
		self.settings = _extract_dict(self.parameters, in_parameters)
		for x in self._float_params:
			self.settings[x] = float(self.settings[x])
		self.girder, self.index, self.type = girder, index, "Drift"

	def __repr__(self):
		return f"Drift({self.settings}, {self.girder}, {self.index}, '{self.type}')"

	def __str__(self):
		return f"Drift({json.dumps(self.settings, indent = 4)})"

	def to_placet(self) -> str:
		res = "Drift"
		for key in self.settings:
			res += " -" + key + " " + _to_str(self.settings[key])
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
