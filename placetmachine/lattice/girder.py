from typing import Optional, List, Union
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
			self.elements = [elements_sequence]
		else:
			self.elements = elements_sequence
		self.name = kwargs.get('name', "")

	def append(self, element: Element):
		"""Add the given girder to the Girder. """
		self.elements.append(element)

	def pop(self, index: int) -> Element:
		"""Remove the element from the girder"""
		return self.elements.pop(index)
	
	def __setitem__(self, index: int, element: Element):
		"""Place the element on the girder at the given position."""
		self.elements[index] = element

	def __getitem__(self, index: int) -> Element:
		"""Get the element from that girder at the given position."""
		return self.elements[index]
	
