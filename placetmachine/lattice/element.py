import json


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

class Element():
	"""
	Generic class for element handling in the beamline

	Attributes
	----------
	settings: dict
		Dictionary containing the element settings. 
	girder: int
		The girder id, the element is on. This parameter is only relevant when being the part of the lattice.
	type: str, optional
		The type of the element.
	Methods
	-------
	to_placet()
		Produce the string of the element in Placet readable format
	"""
	parameters = []
	_float_params = []
	_int_params = []
	_cached_parameters = []
	
	def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None, elem_type: str = None):
		"""
		Parameters
		----------
		in_parameters: dict
			The dict with input Element parameters
		girder: int, optional
			The number of the girder element is placed
		index: int, optional
			The index of the element in the lattice
		"""
		if in_parameters is None:
			in_parameters = {}
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
		return f"{self.type}({self.settings}, {self.girder}, {self.index}, '{self.type}')"

	def __str__(self):
		return f"{self.type}({json.dumps(self.settings, indent = 4)})"

	def __getitem__(self, key: str):
		if key not in self.parameters:
			raise KeyError(f"Element does not have a '{key}' property!")
		
		return self.settings[key]

	def __setitem__(self, key:str, value):
		if key not in self.parameters:
			raise KeyError(f"Element does not have a '{key}' property!")
		
		self.settings[key] = value

	def to_placet(self) -> str:
		res = self.type
		_to_str = lambda x: f"\"{x}\"" if isinstance(x, str) else x
		for key in self.settings:
			res += f" -{key} {_to_str(self.settings[key])}"
		return res

	def cache_data(self):
		"""
		Cache the cachable parameters.

		Note: the parameters that can be cached are forcely initiated and assigned to 0.0 when the Element is created.
		"""
		self._cached_data = {}
		for key in self._cached_parameters:
			self._cached_data[key] = self.settings[key]

	def use_cached_data(self, clear_cache: bool = False):
		"""
		Use the data stored in cache.

		Parameters
		----------
		clear_cache: bool, default False
			If True clears the cache after uploading
		"""
		if self._cached_data is None:
			raise ValueError("No data in cache")
		for key in self._cached_parameters:
			self.settings[key] = self._cached_data[key]
		if clear_cache:
			self._cached_data = None
	
	@classmethod
	def duplicate(cls, initial_instance):
		return cls(initial_instance.settings, initial_instance.girder, initial_instance.index)