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
		"""
		self.elements, self.types_of_elements = elements, []
		self.name = extra_params.get('name', "")
		
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
		
	def apply(self, amplitude: float):
		"""
		Apply the knob.

		This function is going to apply modifications to the elements associated with the Knob.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.
		"""
		i = 0
		for element in self.elements:
			element[self.coord] += self.values[i] * amplitude
			i += 1

	def __str__(self):
		_data_to_show = ['name', 'type', 'girder', 's', 'x', 'y', 'xp', 'yp']
		i = 0
		data_dict = {key: [None] * len(self.elements) for key in _data_to_show}
		for element in self.elements:
			for key in ['name', 's', 'x', 'y', 'xp', 'yp']:
				if key == self.coord:
					data_dict[key][i] = self.values[i]
				elif key in ['name', 's']:
					data_dict[key][i] = element[key]
				else:
					data_dict[key][i] = 0.0
			data_dict['type'][i] = element.type
			data_dict['girder'][i] = element.girder

			i += 1
		res_table = DataFrame(data_dict)

		return str(res_table)

	__repr__ = __str__
