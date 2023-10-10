import unittest
from placetmachine.lattice import Girder


class GirderElementaryTest(unittest.TestCase):

	def setUp(self):

		self.girder = Girder("test_girder")

	def test_init(self):

		self.assertEqual(self.girder.name, "test_girder")