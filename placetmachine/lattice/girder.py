from typing import Optional, List, Union
import warnings
from placetmachine.lattice.element import Element


class Girder:
	"""
	A class that stores the elements' references that are placed on it.
	"""

	def __init__(self, elements_sequence : Optional[Union[Element, List[Element]]], **kwargs):
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
		if isinstance(elements_sequence, Element):
			elements_sequence = [elements_sequence]

		for element in elements_sequence:
			if element.girder is None:
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
	
