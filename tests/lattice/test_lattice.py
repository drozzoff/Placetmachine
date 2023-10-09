import unittest
from placetmachine import Beamline
from placetmachine.lattice import Element, Quadrupole, Drift, Cavity, Bpm, Multipole, Sbend, Dipole


class ElementElementaryTest(unittest.TestCase):

	def setUp(self):

		self.beamline = Beamline("test_beamline")

	def test_append(self):

		