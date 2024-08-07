import unittest
import pandas as pd
from placetmachine.lattice import Girder, Quadrupole, Cavity


class GirderElementaryTest(unittest.TestCase):

	def setUp(self):
		
		test_quad = Quadrupole(dict(name = "test_quad"))
		test_cav = Cavity(dict(name = "test_cav"))

		self.girder = Girder([test_quad, test_cav], name = "test_girder")

	def test_init(self):
		
		self.assertEqual(self.girder.name, "test_girder")

		self.assertIs(self.girder, self.girder.elements[0].girder)
		self.assertIs(self.girder, self.girder.elements[1].girder)

	def test_access(self):

		self.assertEqual(self.girder[0]['name'], "test_quad")
		
		self.assertEqual(self.girder[1]['name'], "test_cav")

		new_quad = Quadrupole(dict(name = "new_quad"))
		self.girder.append(new_quad)

		self.assertEqual(self.girder[2]['name'], "new_quad")

		test = self.girder.pop(1)
		self.assertEqual(test['name'], "test_cav")

	def test_access2(self):
		new_quad = Quadrupole(dict(name = "new_quad"))

		self.girder[1] = new_quad

		self.assertEqual(self.girder[1]['name'], "new_quad")

		self.assertEqual(self.girder[0]['name'], "test_quad")

	def test_append(self):
		new_quad = Quadrupole(dict(name = "new_quad"))

		self.girder.append(new_quad)

		self.assertIs(self.girder, new_quad.girder)

	def test_to_dataframe(self):
		new_quad = Quadrupole(dict(name = "new_quad"))

		self.girder.append(new_quad)

		test_dataframe_dict = {
			'name': ["test_quad", "test_cav", "new_quad"], 
			'type': ["Quadrupole", "Cavity", "Quadrupole"],
			's': [None] * 3,
			}
		test_dataframe = pd.DataFrame(test_dataframe_dict)

		pd.testing.assert_frame_equal(test_dataframe, self.girder.to_dataframe())