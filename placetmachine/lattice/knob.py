from .element import Element
from typing import List


class Knob:

	_cached_parameters = ['x', 'y', 'xp', 'yp']
	_accepted_types = ['Quadrupole', 'Cavity']

	def __init__(self, elements: List[Element], coord: str, values: List[float]):
		"""
		Initialize the Knob

		Parameters
		----------
		elements: List[Element]
			List of elements to be used for this Knob

			Elements provided here should be the elements that are the part of the Beamline.
		coord: str
			Coordinate that to be used for modifications

			So far, we implement the simple model of the Knob, where only 1 parameter is 
			modified. It is the same parameter for all the parameters. Eg. 'x'
		values: List[float]
			Values of the given coordinates for the given elements to apply as a Knob
		"""
		self.elements = elements
		
		# checking the supported types
		for element in self.elements:
			if element.type not in self._accepted_types:
				raise TypeError(f"Inappropriate element type. Acceptable are {self._accepted_types}, received '{element.type}'")
		
		self.coord = coord
		if self.coord not in self._cached_parameters:
			raise ValueError(f"Incorrect coordinate. Acceptable are {self._cached_parameters}, received '{coord}'")

		self.values = values
		if len(self.values) != len(self.elements):
			raise ValueError(f"The number of elements and values provided are different.")
		
	def apply(self, amplitude: float):
		"""
		Apply the knob

		This function is going to apply modifications to the lattice associated with this Knob

		Parameters
		----------
		amplitude: float
			Amplitude of the knob to apply
		"""
		i = 0
		for element in self.elements:
			element[self.coord] += self.values[i] * amplitude