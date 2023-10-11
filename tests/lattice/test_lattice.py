import unittest
import warnings
from placetmachine import Beamline
from placetmachine.lattice import Quadrupole, Cavity


class ElementElementaryTest(unittest.TestCase):

	def setUp(self):

		self.beamline = Beamline("test_beamline")

		self.test_quad = Quadrupole({'name': "test_quad"})
		self.test_cavity = Cavity({'name': "test_cavity"})

	def test_append(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		self.assertEqual(self.beamline.lattice[0]['name'], "test_quad")
		self.assertEqual(self.beamline.lattice[0].index, 0)
		self.assertEqual(self.beamline.lattice[1].index, 1)
	
	def test_append_girder_check(self):

		self.beamline.append(self.test_quad, new_girder = True)
		self.beamline.append(self.test_cavity)

		self.assertEqual(self.beamline.lattice[1].girder, 1)
	
	def test_append_girder_check2(self):

		self.beamline.append(self.test_quad, new_girder = True)
		self.beamline.append(self.test_cavity, new_girder = True)

		self.assertEqual(self.beamline.lattice[1].girder, 2)
	
	def test_append_girder_check3(self):

		self.beamline.append(self.test_quad)

		with warnings.catch_warnings(record = True) as warning_list:
			self.beamline.append(self.test_cavity, new_girder = True)

		self.assertEqual(len(warning_list), 1)
		self.assertTrue(issubclass(warning_list[0].category, RuntimeWarning))

		self.assertEqual(self.beamline.lattice[1].girder, None)
	
	def test_setitem(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		test_element = Quadrupole({'name': "test_quad2"})

		self.beamline[1] = test_element

		self.assertFalse(test_element is self.beamline[1])
		self.assertEqual(self.beamline[1]['name'], "test_quad2")

	def test_next(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)

		i = 0
		correct_names = ["test_quad", "test_cavity", "test_quad"]
		for element in self.beamline:
			self.assertEqual(element['name'], correct_names[i])
			i += 1
	
	def test_data_caching(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		# setting initial values
		reference_value = 40.0
		for element in self.beamline:
			element['y'] = reference_value

		# caching the data of certain elements
		self.beamline.cache_lattice_data([self.beamline[0], self.beamline[3]])

		# setting the differen values
		for element in self.beamline:
			element['y'] = reference_value * 0.5

		self.beamline.upload_from_cache([self.beamline[0], self.beamline[3]])

		with warnings.catch_warnings(record = True) as warning_list:
			self.beamline.upload_from_cache([self.beamline[1]])

		self.assertEqual(len(warning_list), 1)
		self.assertTrue(issubclass(warning_list[0].category, RuntimeWarning))

		self.assertEqual(self.beamline[0]['y'], reference_value)
		self.assertEqual(self.beamline[1]['y'], reference_value * 0.5)

		test_element = Quadrupole({'name': "test_quad2"})
		with self.assertRaises(ValueError):
			self.beamline.cache_lattice_data([test_element])

	def test_girders_number(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		
		self.assertIs(self.beamline.get_girders_number(), None)
	
	def test_girders_number2(self):

		self.beamline.append(self.test_quad, new_girder = True)
		self.beamline.append(self.test_cavity)
		
		self.assertIs(self.beamline.get_girders_number(), 1)
		
	def test_girders_number3(self):

		self.beamline.append(self.test_quad, new_girder = True)
		self.beamline.append(self.test_cavity, new_girder = True)
		
		self.assertIs(self.beamline.get_girders_number(), 2)

	def test_extract(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		for quad in self.beamline.extract(['Quadrupole']):
			self.assertIn(quad, [self.beamline[0], self.beamline[2]])
		
		for cav in self.beamline.extract(['Cavity']):
			self.assertIn(cav, [self.beamline[1], self.beamline[3]])

		with self.assertRaises(ValueError):
			for cav in self.beamline.extract(['MyElement']):
				pass
	
	def test_number_lists(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		self.assertEqual(self.beamline.quad_numbers_list(), [0, 2])
		self.assertEqual(self.beamline.cavs_numbers_list(), [1, 3])
		self.assertEqual(self.beamline.bpms_numbers_list(), [])

	def test_misalign_element(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		self.beamline.misalign_element(element_index = 1, y = 40.0)

		self.assertEqual(self.beamline[0]['y'], 0.0)
		self.assertEqual(self.beamline[1]['y'], 40.0)