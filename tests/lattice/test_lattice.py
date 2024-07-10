import unittest
import warnings
from placetmachine import Beamline
from placetmachine.lattice import Quadrupole, Cavity, Drift


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

	def test_realign_elements(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		for j, parameter in enumerate(self.beamline._alignment_parameters):
			i = j + 1
			self.beamline[0][parameter] = i if (i % 2) == 0 else -i
			self.beamline[1][parameter] = 2 * i if (i % 2) == 0 else -2 * i

		self.beamline.realign_elements()

		for parameter in self.beamline._alignment_parameters:
			self.assertEqual(self.beamline[0][parameter], 0.0)
			self.assertEqual(self.beamline[1][parameter], 0.0)
		
	def test_realign_elements2(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		for j, parameter in enumerate(self.beamline._alignment_parameters):
			i = j + 1
			self.beamline[0][parameter] = i if (i % 2) == 0 else -i
			self.beamline[1][parameter] = 2 * i if (i % 2) == 0 else -2 * i

		test_param = 'y'
		self.beamline.realign_elements(test_param)

		self.assertEqual(self.beamline[0][test_param], 0.0)
		self.assertEqual(self.beamline[1][test_param], 0.0)

	def test_realign_elements3(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		for j, parameter in enumerate(self.beamline._alignment_parameters):
			i = j + 1
			self.beamline[0][parameter] = i if (i % 2) == 0 else -i
			self.beamline[1][parameter] = 2 * i if (i % 2) == 0 else -2 * i

		test_params = ['y', 'roll']
		self.beamline.realign_elements(test_params)

		for parameter in test_params:
			self.assertEqual(self.beamline[0][parameter], 0.0)
			self.assertEqual(self.beamline[1][parameter], 0.0)		

	def test_realign_elements4(self):

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		for j, parameter in enumerate(self.beamline._alignment_parameters):
			i = j + 1
			self.beamline[0][parameter] = i if (i % 2) == 0 else -i
			self.beamline[1][parameter] = 2 * i if (i % 2) == 0 else -2 * i

		test_params = ['my_coordinate1', 'mycoordinate2']
		
		with self.assertRaises(ValueError):
			self.beamline.realign_elements(test_params)	


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

	def test_misalign_elements(self):

		offsets = {
			1: {
				'x': 0.5,
				'y': 10.0
			},
			2: {
				'x': -10.0,
				'y': 15.0
			}
		}

		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)
		self.beamline.append(self.test_quad)
		self.beamline.append(self.test_cavity)

		self.beamline.misalign_elements(offset_data = offsets)

		self.assertEqual(self.beamline[1]['x'], 0.5)
		self.assertEqual(self.beamline[1]['y'], 10.0)

		self.assertEqual(self.beamline[2]['x'], -10.0)
		self.assertEqual(self.beamline[2]['y'], 15.0)

		self.assertEqual(self.beamline[3]['x'], 0.0)
		self.assertEqual(self.beamline[3]['y'], 0.0)

	def test_get_girder(self):
		#creating a beamline with 3 girders with multiple elements on it

		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.0
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})

		# bulding the girder 1
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)

		# bulding the girder 2
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)

		# bulding the girder 3
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)

		# testing girder 1
		for element, i in zip(self.beamline.get_girder(1), range(5)):
			self.assertIs(element, self.beamline[i] )

		#testting girder 2
		for element, i in zip(self.beamline.get_girder(2), range(5, 11)):
			self.assertIs(element, self.beamline[i] )			

		#testting girder 3
		for element, i in zip(self.beamline.get_girder(3), range(10, 16)):
			self.assertIs(element, self.beamline[i])
			
	def test_misalign_girder_general(self):

		# creating a beamline with 1 girder and elements on it that have finite length
		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.0
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})
		
		# bulding the girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)
		# 1.0 - 0.5 - 2.0 - 0.5 - 1.0 - 5.0 total

		#misaligning the girder
		x_left, x_right = 5.0, 10.0
		y_left, y_right = -10.0, 10.0

		self.beamline.misalign_girder_general(girder = 1, x_right = x_right, x_left = x_left, y_right = y_right, y_left = y_left, filter_types = ['Quadrupole'])

		self.assertAlmostEqual(self.beamline[0]['x'], 5.5, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[2]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[4]['x'], 9.5, delta = 1e-5)

		self.assertAlmostEqual(self.beamline[0]['y'], -8.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[2]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[4]['y'], 8.0, delta = 1e-5)

		#incorrect type
		with self.assertRaises(ValueError):
			self.beamline.misalign_girder_general(girder = 1, x_right = x_right, x_left = x_left, y_right = y_right, y_left = y_left, filter_types = ['MyType'])

	def test_misalign_girder(self):

		# creating a beamline with 2 girders
		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.0
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})
		
		# bulding the girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)
		# 1.0 - 0.5 - 2.0 - 0.5 - 1.0 - 5.0 total

		# building the second girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)

		x, y = 5.0, -10.0

		self.beamline.misalign_girder(girder = 1, x = x, y = y)

		for i in range(5):
			self.assertAlmostEqual(self.beamline[i]['x'], x, delta = 1e-5)
			self.assertAlmostEqual(self.beamline[i]['y'], y, delta = 1e-5)
		
		for i in range(5, 10):
			self.assertEqual(self.beamline[i]['x'], 0.0)
			self.assertEqual(self.beamline[i]['y'], 0.0)

	def test_misalign_articulation_point_basic(self):

		# creating a beamline with 2 girders
		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.0
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})
		
		# bulding the girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)
		# 1.0 - 0.5 - 2.0 - 0.5 - 1.0 - 5.0 total

		# building the second girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		self.beamline.append(cavity)
		self.beamline.append(drift)
		self.beamline.append(quad)

		x, y = 5.0, -10.0
		
		self.beamline.misalign_articulation_point(girder_left = 1, girder_right = 2, x = x, y = y, filter_types = ['Quadrupole'])

		# girder 1
		self.assertAlmostEqual(self.beamline[0]['x'], 0.5, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[2]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[4]['x'], 4.5, delta = 1e-5)

		self.assertAlmostEqual(self.beamline[0]['y'], -1.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[2]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[4]['y'], -9.0, delta = 1e-5)

		# girder 2
		self.assertAlmostEqual(self.beamline[5]['x'], 4.5, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[6]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[7]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[8]['x'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[9]['x'], 0.5, delta = 1e-5)

		self.assertAlmostEqual(self.beamline[5]['y'], -9.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[6]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[7]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[8]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[9]['y'], -1.0, delta = 1e-5)

		# incorrect girder ids (< 0 or > N girders)
		with self.assertRaises(ValueError):
			self.beamline.misalign_articulation_point(girder_left = 0, girder_right = 1, x = x, y = y, filter_types = ['Quadrupole'])

		with self.assertRaises(ValueError):
			self.beamline.misalign_articulation_point(girder_left = 2, girder_right = 3, x = x, y = y, filter_types = ['Quadrupole'])

	def test_misalign_articulation_point_sides(self):

		# creating a beamline with 2 girders
		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.5
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})
		
		# bulding the girder 1
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		# 1.0 - 0.5

		# building the second girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		# 1.0 - 0.5

		#building the girder 3
		self.beamline.append(cavity, new_girder = True)
		self.beamline.append(drift)
		# 2.0 - 0.5

		x, y = 5.0, -10.0

		self.beamline.misalign_articulation_point(girder_right = 1, x = x, y = y)

		self.beamline.misalign_articulation_point(girder_left = 3, x = x, y = y)

		self.assertAlmostEqual(self.beamline[0]['x'], 3.125, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['x'], 0.625, delta = 1e-5)
		
		self.assertAlmostEqual(self.beamline[0]['y'], -6.25, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['y'], -1.25, delta = 1e-5)
		
		for i in [2, 3]:
			self.assertEqual(self.beamline[i]['x'], 0.0)
			self.assertEqual(self.beamline[i]['y'], 0.0)

		self.assertAlmostEqual(self.beamline[4]['x'], 2.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[5]['x'], 4.5, delta = 1e-5)
		
		self.assertAlmostEqual(self.beamline[4]['y'], -4.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[5]['y'], -9.0, delta = 1e-5)
		

		with self.assertRaises(ValueError):
			self.beamline.misalign_articulation_point(girder_left = 1, girder_right = 3, x = x, y = y, filter_types = ['Quadrupole'])	

	def test_misalign_girders(self):

		# creating a beamline with 2 girders
		drift = Drift({
			"name": "test_drift",
			"length": 0.5,
		})

		quad = Quadrupole({
			"name": 'test_quad',
			"length": 1.5
		})

		cavity = Cavity({
			"name": "test_cav",
			"length": 2.0
		})
		
		# bulding the girder 1
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		# 1.0 - 0.5

		# building the second girder
		self.beamline.append(quad, new_girder = True)
		self.beamline.append(drift)
		# 1.0 - 0.5

		#building the girder 3
		self.beamline.append(cavity, new_girder = True)
		self.beamline.append(drift)
		# 2.0 - 0.5

		offset_data = {
			'1': {
				'x': 0.5,
				'y': 2.5
			},
			'2': {
				'x': -5.0
			}

		}

		self.beamline.misalign_girders(offset_data = offset_data)

		# girder 1
		self.assertAlmostEqual(self.beamline[0]['x'], 0.5, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['x'], 0.5, delta = 1e-5)

		self.assertAlmostEqual(self.beamline[0]['y'], 2.5, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[1]['y'], 2.5, delta = 1e-5)

		# girder 2
		self.assertAlmostEqual(self.beamline[2]['x'], -5.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['x'], -5.0, delta = 1e-5)

		self.assertAlmostEqual(self.beamline[2]['y'], 0.0, delta = 1e-5)
		self.assertAlmostEqual(self.beamline[3]['y'], 0.0, delta = 1e-5)

		# girder 3
		for i in [4, 5]:
			self.assertAlmostEqual(self.beamline[i]['x'], 0.0, delta = 1e-5)
			self.assertAlmostEqual(self.beamline[i]['y'], 0.0, delta = 1e-5)

	def test_to_placet(self):

		pass