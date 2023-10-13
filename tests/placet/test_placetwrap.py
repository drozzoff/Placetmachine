import unittest
import os
import tempfile
import random
from placetmachine import Placet, Beamline, __placet_files_dir__


class PlacetTest(unittest.TestCase):

	def setUp(self):
		self.placet = Placet(debug_mode = False, save_logs = True, show_intro = False)

		self.placet.source(os.path.join(__placet_files_dir__, "clic_basic_single.tcl"), additional_lineskip = 2)
		self.placet.source(os.path.join(__placet_files_dir__, "clic_beam.tcl"))
		self.placet.source(os.path.join(__placet_files_dir__, "wake_calc.tcl"))
		self.placet.source(os.path.join(__placet_files_dir__, "make_beam.tcl"))	#is optional

		self.data_file_path = os.path.join(os.path.dirname(__file__), "../data/")

		self.dict = tempfile.TemporaryDirectory()
		self._data_folder_ = self.dict.name

		# defining an empty callback
		def empty(**extra_params):
			pass
		
		self.empty_callback = empty
		
		# Initializing multiple beamline for the test purposes (CLIC ML, FFS, IR, ..)

		# Defining a ML beamline
		self.ml_beamline = Beamline("test_ml_beamline")
		
		# reading the lattice into Beamline
		self.ml_beamline.read_from_file(os.path.join(self.data_file_path, "ml_beamline.tcl"))
		
		self.ml_cavity_structure = {
			'a': 3.33e-3,
			'g': 6.4e-3,
			'l': 8.33333e-3,
			'delta': 0.18,
			'delta_g': 0.5e-3,
			'phase': 8.0, 
			'frac_lambda': 0.25, 
			'scale': 1.0
			}
		
	def test_TestNoCorrection(self):
		# to do the track testing, we need
		# 1. create a beamline
		# 2. create a beam (with the correct callback function)
		# 3. run the function

		# ---- beamline creation ----

		# declaring we are starting the creation of the beamline
		self.placet.BeamlineNew()

		# sourcing the lattice to a Placet
		self.ml_beamline.to_placet(os.path.join(self._data_folder_, "ml_tmp_beamline.tcl"))
		self.placet.source(os.path.join(self._data_folder_, "ml_tmp_beamline.tcl"))

		# setting up the callback function with a default name of "callback"
		self.placet.TclCall(script = "callback")
		self.placet.declare_proc(self.empty_callback, name = "callback")

		# finishing the beamline definition
		self.placet.BeamlineSet(name = self.ml_beamline.name)

		# setting up the cavities setup
		self.placet.set_list("structure", **{
			'a': self.ml_cavity_structure['a'],
			'g': self.ml_cavity_structure['g'],
			'l': self.ml_cavity_structure['l'],
			'delta': self.ml_cavity_structure['delta'],
			'delta_g': self.ml_cavity_structure['delta_g'] 
		})

		self.placet.set("phase", self.ml_cavity_structure['phase'])
		self.placet.set("frac_lambda",  self.ml_cavity_structure['frac_lambda'])
		self.placet.set("scale",  self.ml_cavity_structure['scale'])

		# ---- Beam creation ----

		self.placet.RandomReset(seed = int(1000 * random.random()))

		beam_setup = {
			'bunches': 1,
			'macroparticles': 5,
			'particles': 500,
			'energyspread': 0.01 * 1.6 * 9.0,
			'ecut': 3.0,
			'e0': 1.0 * 9.0,
			'file': self.placet.wake_calc(os.path.join(self._data_folder_, "wake.dat"), 5.2e9, -3,  3, 70, 11),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': 6.250882009649877e-03,
			'beta_y': 1.201443036029169,
			'emitt_y': 0.1,
			'alpha_x': 2.455451375064132e-02,
			'beta_x': 8.054208256047598,
			'emitt_x': 8.0
		}
		self.placet.InjectorBeam("main_beam", **beam_setup)
		
		self.placet.SetRfGradientSingle("main_beam", 0, "{" + str(1.0) +  " 0.0 0.0}")

		# ---- Performing the tracking ----

		res = self.placet.TestNoCorrection(machines = 1, beam = "main_beam", survey = "Zero")
		emittx, emitty = res.emittx[0], res.emitty[0]
		emittx_target, emitty_target = 8.0093, 0.100151 # evaluated for configuration of 11 slices X 5 macroparticle per slice

		emittx_tolerance, emitty_tolerance = 0.01, 0.001
		self.assertAlmostEqual(emittx, emittx_target, delta = emittx_tolerance)
		self.assertAlmostEqual(emitty, emitty_target, delta = emitty_tolerance)
	
	def test_TestIntRegion(self):

		pass