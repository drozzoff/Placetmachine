from placetmachine.lattice.element import Element


class Girder:
	"""
	A class that stores the elements' references that are placed on it.
	"""

	def __init__(self, name: str = None):
		"""

		Parameters
		----------
		name: str, optinal
			The name of the girder
		"""
		self.elements, self.name = [], name

	def append(self, element: Element):
		"""Add the given girder to the Girder. """
		self.elements.append(element)

	def pop(self, index: int = None) -> Element:
		"""Remove and return the """

	def at(self, element_id: int) -> Element:
		"""
		Get the element at the given position 
		"""
		return self.elements[element_id]

	def __setitem__(self, index: int, element: Element):
		"""Place the element on the girder at the given position."""
		self.elements[index] = element

	def __getitem__(self, index: int) -> Element:
		"""Get the element from that girder at the given position."""
		return self.elements[index]
	
