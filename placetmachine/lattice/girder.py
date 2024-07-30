from typing import Optional, List, Union
import warnings
from pandas import DataFrame
from placetmachine.lattice.element import Element


class Girder:
	"""
	A class that stores the elements' references that are placed on it.
	"""

	def __init__(self, elements_sequence : Optional[Union[Element, List[Element]]] = None, **kwargs):
		"""

		Parameters
		----------
		elements_sequence
			An `Element` or list of `Element`s to be placed on girder.

		Other parameters
		----------------
		name : str
			Name of the girder.
		"""
		if elements_sequence is None:
			elements_sequence = []
			
		if isinstance(elements_sequence, Element):
			elements_sequence = [elements_sequence]

		for element in elements_sequence:
			if element.girder is not None:
				raise ValueError("Element(s) provided are already on other Girder. Cannot create a new Girder.")
				
		self.elements = elements_sequence

		for element in elements_sequence:
			element.girder = self

		self.name = kwargs.get('name', "")

	def append(self, element: Element):
		"""
		Add the given girder to the Girder.
		Raises an Exception when the element is already on the `Girder`.

		Parameters
		----------
		element
			Element to append
		"""
		if element.girder is None:
			self.elements.append(element)
			element.girder = self
		else:
			warnings.warn("Given element is already on the other girder!")

	def pop(self, index: int) -> Element:
		"""
		Remove the `Element` from the `Girder`
		
		Parameters
		----------
		index
			The index of the element to pop.
		
		Returns
		-------
		Element
			`Element` that was removed from the `Girder`.
		"""
		self.elements[index].girder = None
		return self.elements.pop(index)
	
	def __setitem__(self, index: int, element: Element):
		"""Place the element on the girder at the given position."""
		if element.girder is None:
			self.elements[index].girder = None
			self.elements[index] = element
		else:
			warnings.warn("Given element is already on the other girder!")

	def __getitem__(self, index: int) -> Element:
		"""Get the element from that girder at the given position."""
		return self.elements[index]
	
	def get_dataframe(self) -> DataFrame:
		"""
		Return the DataFrame with the Girder data.

		The data included in the DataFrame are the `Elements` information:
		```
		['name', 'type', 's']
		```
		which is a name, type, and location of the element belonging to the girder.
		
		Typically, the properties, like `s` are acquired during the [`Beamline`][placetmachine.lattice.lattice.Beamline]
		creation. When the girder is created separately, these properties are set to `None`.

		Returns
		-------
		DataFrame
			Girder data summary
		"""
		data_dict = {key: [] for key in ['name', 'type', 's']}
		for i, element in enumerate(self.elements):
			data_dict['name'].append(element['name'])
			
			data_dict['s'].append(element['s'] if 's' in element.settings else None)

			data_dict['type'].append(element.type)
		return DataFrame(data_dict)
	
	def __str__(self):
		
		return str(self.get_dataframe())

	__repr__ = __str__