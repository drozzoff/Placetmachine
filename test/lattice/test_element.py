import unittest
from ...placetmachine.lattice.placetlattice import Element


class ElementElementaryTest(unittest.TestCase):

	def setUp(self):
		
		class NewElement(Element):
			parameters = ["name", "s", "x", "y", "xp", "yp", "roll", "type"]
			_float_params = ["s", "x", "y", "xp", "yp", "roll"]
			_int_params = ["type"]
			_cached_parameters = ['x', 'y', 'xp', 'yp', 'roll']

			def __init__(self, in_parameters: dict = None, girder: int = None, index: int = None):
				super(NewElement, self).__init__(in_parameters, girder, index, "NewElement")

		self.new_element = NewElement(dict(name = "new_element"))
		
	def test_attributes(self):

		# verifying the type of the NewElement
		unittest.assertEqual(self.new_element.type, "NewElement")

		# verifying the name of the NewElement object
		unittest.assertEqual(self.new_element.settings['name'], "new_element")

		# verifying there are no other parameters except declared
		unittest.assertNotIn("s", self.new_element.settings)
	
	def test_to_placet(self):

		# the correct result
		placet_line = 'Element -name "new_element" -type "NewElement"'

		unittest.assertEqual(placet_line, self.new_element.to_placet())

	def test_cache_data(self):

		#to modify Element before introducing that
		pass
		


if __name__ == "__main__":
	unittest.main()