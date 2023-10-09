import unittest
from placetmachine.lattice import Knob, Quadrupole, Bpm


class KnobTest(unittest.TestCase):

	def setUp(self):
		
		self.test_quad = Quadrupole()

	def test_init(self):

		knob = Knob([self.test_quad], 'y', [40.0])

		self.assertEqual(knob.values, [40.0])

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
	