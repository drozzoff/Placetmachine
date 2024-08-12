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
		
		knob.apply(0.5, strategy = "simple_memory")
		# offsets = 1.5, 0.75
		# applied 2.0, 1.0 | missmatch -0.5, -0.25

		self.assertEqual(self.test_quad['y'], 2.0)
		self.assertEqual(knob.mismatch, [-0.5, -0.25])

		knob.apply(0.5, strategy = "simple_memory")
		# offsets = 1.5, 0.75
		# applied 1.0 (3.0), 1.0(2.0) | missmatch 0.0, -0.5

		self.assertEqual(self.test_quad['y'], 3.0)
		self.assertEqual(knob.mismatch, [0.0, -0.5])
		self.assertEqual(second_quad['y'], 2.0)

		knob.apply(1.0, strategy = "simple_memory")
		# offsets = 3.0, 1.5
		# applied 3.0(6.0), 1.0(2.0) | mismatch 0.0, 0.0

		self.assertEqual(knob.mismatch, [0.0, 0.0])

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

		print(knob)
		print(knob.amplitude)

	def test_apply5(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale")
		# offrsets = 1.625, 0.75
		# applied 2.0 (correct 2.1666..), 1.0 (correct 1.0) | mismatch 0.166.., 0.0 | Amplitude change 0.5 -> 0.6666

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		
		print(knob)
		print(knob.amplitude)

		knob.apply(1.0, strategy = "min_scale")
		# offrsets = 3.25, 1.5
		# applied 4.0 (correct 4.333..), 2.0 (correct 2.0) | mismatch 0.33.., 0.0 | Amplitude change 1.0 -> 1.3333..
		# total applied 6.0, 3.0 | missmatch total 0.5, 0.0 | Total amplitude 2.0

		self.assertEqual(knob.amplitude, 2.0)
		self.assertAlmostEqual(self.test_quad['y'], 6.0)
		self.assertAlmostEqual(second_quad['y'], 3.0)
		self.assertEqual(knob.mismatch, [0.5, 0.0])

		print(knob)
		print(knob.amplitude)

	def test_apply6(self):
		
		second_quad = Quadrupole({'name': "test_quad2"})

		knob = Knob([self.test_quad, second_quad], 'y', [3.25, 1.5], step_size = 1.0)
		
		knob.apply(0.5, strategy = "min_scale_memory")
		# offrsets = 1.625, 0.75
		# applied 2.0 (correct 2.1666..), 1.0 (correct 1.0) | mismatch 0.166.., 0.0 | Amplitude change 0.5 -> 0.6666

		self.assertEqual(second_quad['y'], 1.0)
		self.assertAlmostEqual(self.test_quad['y'], 2.0)
		self.assertAlmostEqual(knob.amplitude, 2./3.)
		
		print(knob)
		print(knob.amplitude)

		knob.apply(1.0, strategy = "min_scale_memory")
		# offrsets = 3.25, 1.5
		# applied 5.0 (correct 4.333.. + 0.166 (memory)), 2.0 (correct 2.0) | mismatch -0.5, 0.0 | Amplitude change 1.0 -> 1.3333..
		# total applied 7.0, 3.0 | missmatch total -0.5, 0.0 | Total amplitude 2.0

		self.assertEqual(knob.amplitude, 2.0)
		self.assertAlmostEqual(self.test_quad['y'], 7.0)
		self.assertAlmostEqual(second_quad['y'], 3.0)
		self.assertEqual(knob.mismatch, [-0.5, 0.0])

		print(knob)
		print(knob.amplitude)


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
			'y_mismatch': [0.0]
			}
		test_dataframe = pd.DataFrame(test_dataframe_dict)

		pd.testing.assert_frame_equal(test_dataframe, knob.to_dataframe())