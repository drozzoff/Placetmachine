import unittest
from placetmachine.lattice import Element


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
		self.assertEqual(self.new_element.type, "NewElement")

		# verifying the name of the NewElement object
		self.assertEqual(self.new_element.settings['name'], "new_element")

		# verifying there are no other parameters except declared
		self.assertNotIn("s", self.new_element.settings)

		with self.assertRaises(KeyError):
			print(self.new_element['s'])
	
	def test_attributes2(self):

		parameters_to_test, test_value = ["s", "x", "y", "xp", "yp", "roll"], 10.0

		# verifying the assignment
		for parameter in parameters_to_test:
			self.new_element[parameter] = test_value

		test_list = [self.new_element[parameter] for parameter in parameters_to_test]

		self.assertEqual(test_list, [test_value] * len(parameters_to_test))


	def test_to_placet(self):
		
		parameters_to_test, test_value = ["s", "x", "y", "xp", "yp", "roll"], -10.0

		# verifying the assignment
		for parameter in parameters_to_test:
			self.new_element[parameter] = test_value

		# the correct result
		placet_line = 'NewElement -name "new_element" -length 0.0 -x -10.0 -y -10.0 -xp -10.0 -yp -10.0 -roll -10.0 -s -10.0'

		self.assertEqual(placet_line, self.new_element.to_placet())

	def test_cache_data(self):

		parameters_to_test, test_value = ["s", "x", "y", "xp", "yp", "roll"], 20.0

		# verifying the assignment
		for parameter in parameters_to_test:
			self.new_element[parameter] = test_value
		
		self.new_element.cache_data()

		self.assertEqual(self.new_element._cached_data, dict(x = 20.0, y = 20.0, xp = 20.0, yp = 20, roll = 20.0))

	def test_use_cached_data(self):

		parameters_to_test, test_value = ["s", "x", "y", "xp", "yp", "roll"], 20.0

		# verifying the assignment
		for parameter in parameters_to_test:
			self.new_element[parameter] = test_value
		
		self.new_element.cache_data()

		for parameter in parameters_to_test:
			self.new_element[parameter] = 0.0
		
		self.new_element.use_cached_data()

		for parameter in ["x", "y", "xp", "yp", "roll"]:
			self.assertEqual(self.new_element[parameter], test_value)
	

	def test_use_cached_data2(self):

		parameters_to_test, test_value = ["s", "x", "y", "xp", "yp", "roll"], 20.0

		# verifying the assignment
		for parameter in parameters_to_test:
			self.new_element[parameter] = test_value
		
		self.new_element.cache_data()

		for parameter in parameters_to_test:
			self.new_element[parameter] = 0.0
		
		self.new_element.use_cached_data(True)

		self.assertEqual(self.new_element._cached_data, None)