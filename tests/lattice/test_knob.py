import unittest
from placetmachine.lattice import Knob, Quadrupole, Bpm
import pandas as pd

class KnobTest(unittest.TestCase):

	def setUp(self):
		
		self.test_quad = Quadrupole({'name': "test_quad"})

	def test_init(self):

		knob = Knob([self.test_quad], 'y', [40.0], name = "test_knob")

		self.assertEqual(knob.values, [40.0])

		self.assertEqual(knob.amplitude, 0.0)

		self.assertEqual(knob.name, "test_knob")

		self.assertEqual(knob.changes, [0.0])

		self.assertEqual(knob.mismatch, [0.0])

	def test_init_unsupported_type(self):
		
		bpm = Bpm()
		with self.assertRaises(TypeError):
			knob = Knob([bpm], 'y', [40.0])

	def test_init_unsupported_variable(self):
		
		with self.assertRaises(ValueError):
			knob = Knob([self.test_quad], 'k1', [40.0])

	def test_init_incorrect_length(self):
		
		quad2 = Quadrupole()

		with self.assertRaises(ValueError):
			knob = Knob([self.test_quad, quad2], 'y', [40.0])

	def test_apply(self):

		knob = Knob([self.test_quad], 'y', [40.0])

		knob.apply(0.5)

		self.assertEqual(self.test_quad['y'], 20.0)

		self.assertEqual(knob.amplitude, 0.5)
	
	def test_apply2(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.0, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "simple_memory", use_global_mismatch = False)
		# offsets = 1.5, 0.75
		# applied 2.0, 1.0 | missmatch -0.5, -0.25

#		print(knob)

		self.assertEqual(self.test_quad['y'], 2.0)
		self.assertEqual(knob.mismatch, [-0.5, -0.25])

		knob.apply(0.5, strategy = "simple_memory", use_global_mismatch = False)
		# offsets = 1.5, 0.75
		# applied 1.0 (3.0), 1.0(2.0) | missmatch 0.0, -0.5
#		print(knob)
		self.assertEqual(self.test_quad['y'], 3.0)
		self.assertEqual(knob.mismatch, [0.0, -0.5])
		self.assertEqual(second_quad['y'], 2.0)

		knob.apply(1.0, strategy = "simple_memory", use_global_mismatch = False)
		# offsets = 3.0, 1.5
		# applied 3.0(6.0), 1.0(2.0) | mismatch 0.0, 0.0
#		print(knob)
		self.assertEqual(knob.mismatch, [0.0, 0.0])

	def test_apply2_2(self):
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.0, 1.5], step_size = 1.0)

		second_knob = Knob([self.test_quad], 'y', [0.4], step_size = 1.0)

		knob.apply(0.5, strategy = "simple_memory", use_global_mismatch = False)
		# offsets = 1.5, 0.75
		# applied 2.0, 1.0 | missmatch -0.5, -0.25 | global_mismatch -0.5, -0.25

#		print(knob)

		second_knob.apply(2.0, strategy = "simple_memory", use_global_mismatch = False)
		# offset = 0.8
		# applied 1.0 | mismatch -0.2 | global mismatch -0.7

		self.assertEqual(self.test_quad._mismatch['y'], -0.7)
		self.assertEqual(second_quad._mismatch['y'], -0.25)

#		print(second_knob)

	def test_apply2_3(self):
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.0, 1.5], step_size = 1.0)

		second_knob = Knob([self.test_quad], 'y', [0.7], step_size = 1.0)

		knob.apply(0.5, strategy = "simple_memory", use_global_mismatch = True)
		# offsets = 1.5, 0.75
		# applied 2.0, 1.0 | missmatch -0.5, -0.25 | global_mismatch -0.5, -0.25

#		print(knob)

		second_knob.apply(2.0, strategy = "simple_memory", use_global_mismatch = True)
		# offset = 1.4
		# with global mismatch 0.9 
		# applied 1.0 | mismatch 0.4 (global mismatch is not taken into account here)
		# global mismatch -0.1 (-0.5 + 0.4)
#		print(second_knob)

		self.assertAlmostEqual(self.test_quad._mismatch['y'], -0.1)
		self.assertAlmostEqual(second_knob.mismatch[0], 0.4)

	def test_apply3(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.0, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "simple")
		# offsets = 1.5, 0.75
		# applied 2.0, 1.0 | missmatch -0.5, -0.25

		self.assertEqual(self.test_quad['y'], 2.0)
		self.assertEqual(knob.mismatch, [-0.5, -0.25])

		knob.apply(0.5, strategy = "simple")
		# offsets = 1.5, 0.75
		# applied 2.0 (4.0), 1.0(2.0) | missmatch -1.0, -0.5

		self.assertEqual(self.test_quad['y'], 4.0)
		self.assertEqual(knob.mismatch, [-1.0, -0.5])
		self.assertEqual(second_quad['y'], 2.0)

		knob.apply(1.0, strategy = "simple")
		# offsets = 3.0, 1.5
		# applied 3.0(7.0), 2.0(4.0) | mismatch -1.0, -1.0

		self.assertEqual(knob.mismatch, [-1.0, -1.0])

	def test_apply4(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.0, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale")
		# offrsets = 1.5, 0.75
		# applied 2.0, 1.0 | mismatch 0.0, 0.0 | Amplitude change 0.5 -> 0.6666

		self.assertEqual(self.test_quad['y'], 2.0)
		self.assertEqual(second_quad['y'], 1.0)
		self.assertEqual(knob.mismatch, [0.0, 0.0])
		self.assertAlmostEqual(knob.amplitude, 2./3., delta = 1e-4)

		knob.apply(0.25, strategy = "min_scale")
		# offsets = 0.75, 0.375
		# applied 0.0, 0.0 | mismatch 0.0, 0.0 | amplitude change 0.25 -> 0.0
		self.assertAlmostEqual(knob.amplitude, 2./3., delta = 1e-4)

#		print(knob)
#		print(knob.amplitude)

	def test_apply5(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale")
		# offrsets = 1.625, 0.75
		# applied 2.0 (correct 2.1666..), 1.0 (correct 1.0) | mismatch 0.166.., 0.0 | Amplitude change 0.5 -> 0.6666

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		
#		print(knob)
#		print(knob.amplitude)

		knob.apply(1.0, strategy = "min_scale")
		# offrsets = 3.25, 1.5
		# applied 4.0 (correct 4.333..), 2.0 (correct 2.0) | mismatch 0.33.., 0.0 | Amplitude change 1.0 -> 1.3333..
		# total applied 6.0, 3.0 | missmatch total 0.5, 0.0 | Total amplitude 2.0

		self.assertEqual(knob.amplitude, 2.0)
		self.assertAlmostEqual(self.test_quad['y'], 6.0)
		self.assertAlmostEqual(second_quad['y'], 3.0)
		self.assertAlmostEqual(knob.mismatch[0], 0.5)
		self.assertAlmostEqual(knob.mismatch[1], 0.0)

#		print(knob)
#		print(knob.amplitude)

	def test_apply5_2(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)

		second_knob = Knob([self.test_quad, second_quad], 'y', [0.7, 1.2], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale")
		# offrsets = 1.625, 0.75
		# amplitude adjustment to have .., 1.0: 0.5 -> 0.666
		# applied 2.0 (correct 2.1666..), 1.0 (correct 1.0) | mismatch 0.166.., 0.0

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		
#		print(knob)
#		print(knob.amplitude)

		knob.apply(1.0, strategy = "min_scale")
		# offrsets = 3.25, 1.5
		# amplitude adjustment to have .., 2.0: 1.0 -> 1.3333
		# applied 4.0 (correct 4.333..), 2.0 (correct 2.0)
		# mismatch 0.33.., 0.0 
		# total mismatch 0.5 ,0.0
		# total applied 6.0, 3.0
		# Total amplitude 2.0
		# global mismatch 0.5, 0.0

#		print(knob)
		self.assertAlmostEqual(self.test_quad._mismatch['y'], 0.5)
		self.assertAlmostEqual(second_quad._mismatch['y'], 0.0)

		second_knob.apply(1.0, strategy = "min_scale")
		# offsets = 0.7, 1.2
		# amplitude adjustment to have 1.0: 1.0 -> 1.4286
		# applied 1.0 (correct 1.0), 2.0 (correct 1.7143)
		# mismatch 0.0, -0.2857
		# total mismatch 0.0, -0.2857
		# global mismatch 0.5, -0.2857
		
#		print(second_knob)
		self.assertAlmostEqual(second_quad._mismatch['y'], 1.2 * 1.0 / 0.7 - 2.0)
		self.assertAlmostEqual(self.test_quad._mismatch['y'], 0.5)

	def test_apply6(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale_memory", use_global_mismatch = False)
		# offrsets = 1.625, 0.75
		# AMplitude
		# Amplitude adjustment to have a full step size for second element is 1.0 / 1.5 = 0.6(6)
		# Amplitude mismatch: 0.5 + 0.0 - 0.6(6) = -0.1(6)
		# Offsets to apply are 2.1(6), 1.0 | Mismatch is 0.0, 0.0
		# Rounding to 2.0, 1.0 |Produced mismatch 0.1(6), 0.0 

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		self.assertAlmostEqual(knob.amplitude_mismatch, 0.5 - 2./3.)
		
#		print(knob)
#		print(knob.amplitude)
#		print(knob.amplitude_mismatch)

		knob.apply(1.0, strategy = "min_scale_memory", use_global_mismatch = False)
		# amplitude to apply 1.0. Current mismatch is -0.1(6) -> 0.8(3)
		# This yields offsets:
		# 2.70833, 1.25
		# Amplutude adjustment ->  1.0 / 1.5 = 0.6(6)
		# Amplitude mismatch 1.0 - 0.1(6) - 0.6(6) = 0.1(6)
		# Offsets to apply: 2.1(6), 1.0. Mismatch is 0.1(6), 0.0
		# Final values are  2.3(3), 1.0
		# Rounding to 2.0, 1.0 | New mismatch is 0.3, 0.0
		# Total applied 4.0, 2.0 | Total amplitude 1.3333

		self.assertAlmostEqual(knob.amplitude, 4./3.)
		self.assertAlmostEqual(self.test_quad['y'], 4.0)
		self.assertAlmostEqual(second_quad['y'], 2.0)
		self.assertAlmostEqual(knob.mismatch[0], 1./3.)
		self.assertAlmostEqual(knob.mismatch[1], 0.0)
		self.assertAlmostEqual(knob.amplitude_mismatch, 2./3. - 0.5)

#		print(knob)
#		print(knob.amplitude)
#		print(knob.amplitude_mismatch)

		with self.assertRaises(ValueError):
			knob.apply(2.5, strategy = "custom")

	def test_apply6_2(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)

		second_knob = Knob([self.test_quad, second_quad], 'y', [1.2, 3.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale_memory", use_global_mismatch = True)
		# offrsets = 1.625, 0.75
		# AMplitude
		# Amplitude adjustment to have a full step size for second element is 1.0 / 1.5 = 0.6(6)
		# Amplitude mismatch: 0.5 + 0.0 - 0.6(6) = -0.1(6)
		# Offsets to apply are 2.1(6), 1.0 | Global mismatch is 0.0, 0.0
		# Rounding to 2.0, 1.0 | Produced mismatch 0.1(6), 0.0
		# Produced global mismatch is 0.1(6), 0.0

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		
#		print(knob)
#		print(knob.amplitude)

		knob.apply(1.0, strategy = "min_scale_memory", use_global_mismatch = True)
		# amplitude to apply 1.0. Current mismatch is -0.1(6) -> 0.8(3)
		# This yields offsets:
		# 2.70833, 1.25
		# Amplutude adjustment ->  1.0 / 1.5 = 0.6(6)
		# Amplitude mismatch 1.0 - 0.1(6) - 0.6(6) = 0.1(6)
		# Offsets to apply: 2.1(6), 1.0. Gloabal mismatch is 0.1(6), 0.0
		# Final values are  2.3(3), 1.0
		# Rounding to 2.0, 1.0 | New  global mismatch is 0.3, 0.0
		# New mismatch is 0.3(3), 0.0
		# Total applied 4.0, 2.0 | Total amplitude 1.3333

		self.assertAlmostEqual(knob.amplitude, 4./3.)
		self.assertAlmostEqual(self.test_quad['y'], 4.0)
		self.assertAlmostEqual(second_quad['y'], 2.0)
		self.assertAlmostEqual(knob.mismatch[0], 1./3.)
		self.assertAlmostEqual(knob.mismatch[1], 0.0)

#		print(knob)
#		print(knob.amplitude)

		second_knob.apply(1.0, strategy = "min_scale_memory", use_global_mismatch = True)
		# Amplitude to apply 1.0 | No mismatch
		# Offsets to apply 1.2, 3.5
		# Amplitude adjustment 1.0 / 1.2 = 0.8(3)
		# Amplitude mismatch 1.0 + 0.0 - 0.8(3) = 0.1(6)
		# Offsets to appl 1.0, 2.91(6) | Global mismatch is 0.3(3), 0.0
		# Final values are 1.3(3), 2.91(6)
		# That rounds to 1.0, 3.0 | New global mismatch 0.3(3), -0.083(3)
		# New mismatch is 0.0, -0.083(3)

		self.assertAlmostEqual(self.test_quad._mismatch['y'], 1./3.)
		self.assertAlmostEqual(second_quad._mismatch['y'], -(3.0 - 1.0 / 1.2 * 3.5))

#		print(second_knob)
#		print(second_knob.amplitude)

		with self.assertRaises(ValueError):
			knob.apply(2.5, strategy = "custom")

	def test_apply7(self):

		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [-3.2, 1.5], step_size = 1.0)

		knob.apply(0.5, strategy = "simple")
		# offrsets = -1.6, 0.75
		# applied -2.0 , 1.0 | mismatch 0.4, -0.25
#		print(knob)
		self.assertAlmostEqual(knob.mismatch[0], 0.4, delta = 1e-4)
		self.assertAlmostEqual(knob.mismatch[1], -0.25, delta = 1e-4)

	def test_cache(self):

		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)

		knob.apply(0.5, strategy = "min_scale_memory")

#		print(knob)
#		print(knob.amplitude)

		knob.cache_state()
#		print(knob._cached_data)

		knob.apply(1.0, strategy = "min_scale_memory")

#		print(knob)
#		print(knob.amplitude)
#		print(knob._cached_data)

		self.assertAlmostEqual(knob._cached_data['amplitude'], 2./3.)
		self.assertEqual(knob._cached_data['changes'], [2.0, 1.0])

		knob.reset()

		self.assertEqual(knob.amplitude, 0.0)
		self.assertEqual(knob.amplitude_mismatch, 0.0)
		self.assertEqual(knob.changes, [0.0, 0.0])
		self.assertEqual(knob.mismatch, [0.0, 0.0])
		self.assertEqual(knob.elements[0]['y'], 0.0)
		self.assertEqual(knob.elements[1]['y'], 0.0)

#		print(knob)
#		print(knob.amplitude)
#		print(knob._cached_data)

		knob.upload_state_from_cache(True)

		self.assertIs(knob._cached_data, None)

		self.assertAlmostEqual(knob.amplitude, 2./3.)
		self.assertEqual(knob.changes, [2.0, 1.0])

#		print(knob)
#		print(knob.amplitude)
#		print(knob._cached_data)

	def test_to_dataframe(self):

		knob = Knob([self.test_quad], 'y', [40.0], step_size = 5.0)

		knob.apply(0.5)

		test_dataframe_dict = {
			'name': ["test_quad"], 
			'type': ["Quadrupole"],
			'girder': [None],
			's': [None],
			'y_amplitude': [40.0],
			'y_current': [20.0],
			'y_changes': [20.0],
			'y_mismatch': [0.0],
			'y_total_mismatch': [0.0]
			}
		test_dataframe = pd.DataFrame(test_dataframe_dict)
#		print(knob.to_dataframe())
		pd.testing.assert_frame_equal(test_dataframe, knob.to_dataframe())