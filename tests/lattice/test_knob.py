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
		
		knob.apply(0.5)

		self.assertEqual(self.test_quad['y'], 2.0)
		self.assertEqual(knob.mismatch, [-0.5, -0.25])

		knob.apply(0.5)

		self.assertEqual(self.test_quad['y'], 3.0)
		self.assertEqual(knob.mismatch, [0.0, -0.5])
		self.assertEqual(second_quad['y'], 2.0)

		knob.apply(1.0)

		self.assertEqual(knob.mismatch, [0.0, 0.0])

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