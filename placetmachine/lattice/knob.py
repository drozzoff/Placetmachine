from typing import List
from pandas import DataFrame
from placetmachine.lattice import Element


class Knob:
	"""
	A class used to create a Knob.

	A knob is a certain change in the beamline (elements offsets, strengths change, etc.)
	that is applied to modify change conditions like beam waist, dispersion or something
	more complex.

	So far the elements' types accepted for the knobs creation are [`Quadrupole`][placetmachine.lattice.quadrupole.Quadrupole]
	and [`Cavity`][placetmachine.lattice.cavity.Cavity].

	The `Knob` is going to store the references of the [`Element`][placetmachine.lattice.element.Element]s provided and use them to 
	apply the changes. Thus changes to the elements here are going to change the originals.
	
	If parameter ``step_size'' is provided, the coordinates modifications when using [`apply_knob'][placetmachine.lattice.knob.Knob.apply_knob]
	are adjusted towards the closest  number full of steps.

	Attributes
	----------
	elements : List[Element]
		List of the elements that used in this Knob.
	coord : str
		Coordinate that is going to be modified.
	values : List[float]
		List of the coordinates changes for each [`Element`][placetmachine.lattice.element.Element] in `elements`.
	step_size : Optional[float]
		The smallest step that can be implemented when applying the knob
	mismatch : List[float]
		A mismatch between the actual coordinates changes given by `changes` and the ones given by the amplitude. 
		When `step_size` is not provided, is a list of `0.0`.
	changes : List[float]
		A total coordinate change performed with a knob.
	name : str
		Name of the Knob.
	types_of_elements : List[str]
		Types of the elements involved in the Knob.
	amplitude : float
		The current Knob amplitude.
	"""

	_cached_parameters = ['x', 'y', 'xp', 'yp']
	_accepted_types = ['Quadrupole', 'Cavity']

	def __init__(self, elements: List[Element], coord: str, values: List[float], **extra_params):
		"""
		Parameters
		----------
		elements
			List of elements to be used for this `Knob`.
			Elements provided here must be the elements that are the part of the Beamline.
		coord
			Coordinate that to be used for modifications.

			**!!** *So far, we implement the simple model of the Knob, where only 1 parameter is 
			modified. It is the same parameter for all the parameters, Eg. `x`.*
		values
			Values of the given coordinates for the given elements to apply as a Knob.
		
		Other parameters
		----------------
		name : str
			The name of the knob. If not provided, defaults to "".
		step_size : Optional[float]
			Step size for the coordinates changes.
		"""
		self.elements, self.types_of_elements, self.amplitude = elements, [], 0.0
		self.mismatch, self.changes = [0.0] * len(elements), [0.0] * len(elements)
		self.name, self.step_size = extra_params.get('name', ""), extra_params.get('step_size', None)
		
		# checking the supported types and building the types involved
		for element in self.elements:
			if element.type not in self._accepted_types:
				raise TypeError(f"Inappropriate element type. Acceptable are {self._accepted_types}, received '{element.type}'")

			if element.type not in self.types_of_elements:
				self.types_of_elements.append(element.type)
		
		self.coord = coord
		if self.coord not in self._cached_parameters:
			raise ValueError(f"Incorrect coordinate. Acceptable are {self._cached_parameters}, received '{coord}'")

		self.values = values
		if len(self.values) != len(self.elements):
			raise ValueError(f"The number of elements and values provided are different.")
		
	def apply(self, amplitude: float, **kwargs):
		"""
		Apply the knob.

		Amplitude defines the fraction of `values` to add to the `elements`s `coord` involved in 
		the `Knob`. If `step_size` is not defined (default), coordinates changes are applied directly.
		If `step_size` is defined, the values of the coordinates' changes are rounded to the closest
		value that has a full number of `step_size`s. 

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.

		Other parameters
		----------------
		strategy : str
			Strategy to use for calculations of the offsets when the `step_size` is defined. Default is
			'simple_memory'.
		"""
		__strategies_available = ["simple", "simple_memory"]

		if self.step_size == 0:
			self.step_size = None

		if self.step_size is None:
			for i, element in enumerate(self.elements):
				element[self.coord] += self.values[i] * amplitude
		else:
			strategy = kwargs.get("strategy", "simple_memory")
			if strategy not in __strategies_available:
				raise ValueError(f"Strategy '{strategy}' is not available. Possible options are {__strategies_available}.")

			if strategy == "simple":
				self.__appply_simple(amplitude)
			if strategy == "simple_memory":
				self.__apply_simple_memory()
				
		self.amplitude += amplitude

	def __appply_simple(self, amplitude):
		"""
		Apply the the knob.

		The offsets to apply are evaluated by rounding the offsets' amplitude.
		Is prone to accumulating the missmatches of the knobs offsets.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.
		"""
		for i, element in enumerate(self.elements):
			coord_change = self.values[i] * amplitude
			n_step_sizes = int(coord_change / self.step_size)

			new_coord_change = None
			if (coord_change - n_step_sizes * self.step_size) < 0.5 * self.step_size:
				new_coord_change = n_step_sizes * self.step_size
			else:
				new_coord_change = (n_step_sizes + 1) * self.step_size

			self.changes[i] += new_coord_change
			self.mismatch[i] = self.values[i] * (self.amplitude + amplitude) - self.changes[i]

			element[self.coord] += new_coord_change

	def __apply_simple_memory(self, amplitude):
		"""
		Apply the the knob.

		The offsets to apply are evaluated by rounding the offsets' amplitude taking into account also
		the the accumulated mismatch.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.
		"""
		for i, element in enumerate(self.elements):
			coord_change = self.values[i] * amplitude + self.mismatch[i]
			n_step_sizes = int(coord_change / self.step_size)
			
			new_coord_change = None
			if (coord_change - n_step_sizes * self.step_size) < 0.5 * self.step_size:
				new_coord_change = n_step_sizes * self.step_size
			else:
				new_coord_change = (n_step_sizes + 1) * self.step_size

			self.changes[i] += new_coord_change

			self.mismatch[i] = self.values[i] * (self.amplitude + amplitude) - self.changes[i]

			element[self.coord] += new_coord_change

	def to_dataframe(self) -> DataFrame:
		"""
		Return the DataFrame with the Knob data.

		The data included in the DataFrame is:
		```
		['name', 'type', 'girder', 's']
		```
		which is a name, type, girder id, and location of the element belonging to the girder.
		Plus the coordinate amplitude, current value in the beamline, coordinate change performed
		by the knob, and the mismatch when there is a finit step size:
		```
		['y_amplitude', 'y_current']
		```
		Typically, the properties, like `girder` or `s` are acquired during the [`Beamline`][placetmachine.lattice.lattice.Beamline]
		creation. When the knob is created on the isolated element, these properties are set to `None`.

		Returns
		-------
		DataFrame
			Knob data summary
		"""
		data_dict = {key: [] for key in ['name', 'type', 'girder', 's'] + [self.coord + "_amplitude", self.coord + "_current"]}
		for i, element in enumerate(self.elements):
			data_dict['name'].append(element['name'])
			
			data_dict['s'].append(element['s'] if 's' in element.settings else None)

			data_dict['type'].append(element.type)
			data_dict['girder'].append(element.girder)

			data_dict[self.coord + "_amplitude"].append(self.values[i])
			data_dict[self.coord + "_current"].append(element[self.coord])

		data_dict[self.coord + "_changes"] = self.changes
		data_dict[self.coord + "_mismatch"] = self.mismatch

		return DataFrame(data_dict)

	def __str__(self):
		
		return str(self.to_dataframe())

	__repr__ = __str__
