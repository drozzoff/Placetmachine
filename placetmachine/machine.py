import os
from typing import List, Callable
import json
import random
from functools import wraps

import pandas as pd

import numpy as np

from rich.table import Table
from rich.live import Live
from rich.console import Console
from rich.errors import LiveError

import tempfile
from placetmachine import Placet, Beamline, __placet_files_dir__
from placetmachine.lattice import Knob


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

_get_data = lambda name: list(map(lambda x: [float(y) for y in x.split()], open(name, 'r')))
def get_data(filename) -> List:
	res = _get_data(filename)
	if res[-1] == []:
		res.pop(len(res) - 1)
	return res

cut = lambda data, index: list(map(lambda x: x[index], data))

class Machine():
	"""
	A class used for controling the beamline in Placet

	Uses Placet interface to Placet and Beamline for controling the beamline.

	Changes the logic of using the Placet for beam tracking. By default, the number of the machines is set to 1.
	Each Machine instance corresponds to 1 actual beamline. The beamline is described with Beamline.
	All the corrections are applied to the current machines with the current offsets by default. Though, one can
	overwrite that with the typical survey functions, which violates the logic of this class.
	
	...

	Attributes
	----------
	placet: Placet
		A Placet object, used for communicating with the Placet process running in the background
	console: rich.console.Console
		An object used for the fancy terminal output
	beamline: lattice_parse.Beamline, optional
		An object storing the beamline info
	beams_invoked: list(string)
		An object storing the names of the beams that were created
	beamlines_invoked: list(string)
		An object storing the names of the beamlines that were created
	callback_struct_: tuple(func, dict)
		The function that is currently used as callback for the tracking along with its parameters
	_data_folder_: str
		The name of the folder where the temporary files produced by Placet are stored

	Methods
	-------
	set_callback(func: Callable, **extra_params)
		Set the callback function for the tracking
	create_beamline(lattice, **extra_params) -> Beamline
		Create the beamline.
	import_beamline(lattice, **extra_params) -> Beamline
		Import the existing Beamline
	cavities_setup(**extra_params)
		Set up the cavities of the ML
	survey_errors_set(**extra_params)
		Set the survey default errors for the machine
	assign_errors(survey = None, **extra_params)
		Assign the alignment errors to the beamline
	make_beam_particles(e_design: float, e_spread: float, n_particles: int, beam_seed: int = 1234, **extra_params) -> pd.DataFrame:
		Generate the particles distribution
	make_beam_many(beam_name: str, n_slice: int, n: int, beam_seed: int = 1234, **extra_params)
		Generate the particle beam
	make_beam_slice_energy_gradient(beam_name: str, n_slice: int, n_macroparticles: int, eng: float, grad: float, beam_seed: int = 1234, **extra_params) -> str
		Generate the sliced beam
	track(beam, survey = None, **extra_params) 
		Perform the tracking without applying any corrections
	eval_orbit(beam, survey = None, **extra_params)
		Evaluate the beam orbit based on the BPMs readings
	eval_twiss(beam, **extra_params)
		Evaluate the Twiss functions along the beamline
	one_2_one(beam, survey = None, **extra_params)
		Perform the 1-2-1 Beam Based alingment
	DFS(beam, n_slices, n_macroparticles, **extra_params)
		Perform the Dispersion Free Steering
	RF_align(beam, survey = None, **extra_params)
		Perform the RF alignment
	apply_knob(knob: Knob, amplitude: float, **extra_params)
		Apply the knob and update the beamline offsets
	eval_track_results(beam: str = None, beam_type: str = "sliced", **extra_params) -> (pd.DataFrame, float, float)	
		Evaluate the beam parameters at the beamline exit.
	iterate_knob(beam, knob, knob_range = [-1.0, 0.0, 1.0], **extra_params)
		Iterate the given knob in the given range
	scan_knob(beam, knob, knob_range = [-1.0, 0.0, 1.0], **extra_params)
		Scan the knob in the given range, and if the fit is given, assign the knob to the center best value
	apply_quads_errors(strength_error = 0.0)
		Add the strength errors to all the quads
	apply_cavs_errors(phase_error = 0.0, grad_error = 0.0)
		Add the errors to the cavities phase and gradient
	save_beam(**extra_params)
		Save the beam with Placet.BeamDump() command
	save_sliced_beam(**extra_params):
		Save the beam with Placet.BeamSaveAll() command
	phase_advance(self, start_id, end_id)
		Get the phase advance	| Does not work atm

	Methods/Surveys
	---------------
	misalign_element(**extra_params)
		Misalign a single element.
	misalign_elements(**extra_params)
		Misalign multiple elements.
	misalign_girder(**extra_params)
		Misalign a single girder.
	misalign_girder(**extra_params)
		Misalign multiple girders.
	from_file(**extra_params)
		Using file with the misalignmens
	default_clic(**extra_params)
		Using the default Clic Placet routine
	empty()
		No misalignments.
	"""

	surveys = ["default_clic", "from_file", "empty", "misalign_element", "misalign_elements", "misalign_girder", "misalign_girders"]
	callbacks = ["save_sliced_beam", "save_beam", "empty"]

	def __init__(self, **calc_options):
		"""
			
		Additional parameters
		---------------------
		debug_mode: bool, default False
			If True, runs Communicator in debug mode
		save_logs: bool, default True
			If True, invoking Placet.save_debug_info()
		send_delay: float, optional
			The time delay before each data transfer to a Placet process (sometimes needed for stability)
		console_output: bool, default True
			If True, prints the calculations progress in the console
		show_intro: bool default True
			If True, prints the welcome message of Placet at the start
		"""
		self.placet = Placet(save_logs = calc_options.get("save_logs", False), debug_mode = calc_options.get("debug_mode", False), send_delay = calc_options.get("send_delay", None), 
					   show_intro = calc_options.get("show_intro", True))
		self.console_output = calc_options.get("console_output", True)

		self.placet.source(os.path.join(__placet_files_dir__, "clic_basic_single.tcl"), additional_lineskip = 2)
		self.placet.source(os.path.join(__placet_files_dir__, "clic_beam.tcl"))
		self.placet.source(os.path.join(__placet_files_dir__, "wake_calc.tcl"))
		self.placet.source(os.path.join(__placet_files_dir__, "make_beam.tcl"))	#is optional
		self.placet.declare_proc(self.empty)
		self.beamline, self.beams_invoked, self.beamlines_invoked = None, [], []

		#I/O setup
		self.console = Console()
		self._setup_data_folder()

	def __repr__(self):
		return f"Machine(debug_mode = {self.placet.debug_mode}, save_logs = {self.placet._save_logs}, send_delay = {self.placet._send_delay}, console_output = {self.console_output}) && beamline = {repr(self.beamline)}"

	def __str__(self):
		return f"Machine(placet = {self.placet}, beamline = {self.beamline}, beams available = {self.beams_invoked})"

	def _setup_data_folder(self):
		"""Set the temporary folder in tmp/ folder"""
		self.dict = tempfile.TemporaryDirectory()
		self._data_folder_ = self.dict.name

	def term_logging(func: Callable):
		"""Decorator with the fancy status logging"""
		def status_message(func_name):

			if func_name in ["make_beam_slice_energy_gradient", "make_beam_many"]:
				return ["Creating a beam", "Beam created"]

			if func_name in ["create_beamline"]:
				return ["Creating a beamline", "Beamline created"]

			if func_name in ["one_2_one"]:
				return ["Performing 121 alignment", "121 alignment done."]

			if func_name in ["DFS"]:
				return ["Performing the DFS", "DFS alignment done"]

			if func_name in ["track"]:
				return ["Performing the tracking", "Tracking done"]

			if func_name in ["RF_align"]:
				return ["Performing the RF alignment", "RF alignment done"]

			if func_name in ["import_beamline"]:
				return ["Importing a beamline", "Beamline imported"]
			
			if func_name in ["eval_twiss"]:
				return ["Evaluating Twiss", ""]

			return [f"Running '{func_name}'", ""]

		@wraps(func)
		def wrapper(self, *args, **kwargs):
			res = None
			if not self.console_output:
				res = func(self, *args, **kwargs)
			else:
				progress, finished = status_message(func.__name__)
				try:
					with self.console.status(progress) as status:
						res = func(self, *args, **kwargs)
					self.console.log("[green]" + finished)
				except LiveError:
					res = func(self, *args, **kwargs)
			
			return res

		return wrapper

	def set_callback(self, func: Callable, **extra_params):
		"""
		Set the callback function for the tracking

		The name of the procedure used as a callback in Placet is 'callback'.
		The actual procedure can be overriden, that is the purpose of this function.

		Parameters
		----------
		func: func
			Function for the callback

		Additional parameters
		---------------------
		//**// Accepts all the kwargs that func accepts //**//
		"""
		self.placet.declare_proc(func, **dict(extra_params, name = "callback"))
		self.callback_struct_ = (func, extra_params)

	@term_logging
	def create_beamline(self, lattice: str, **extra_params) -> Beamline:
		"""
		Create the beamline in Placet.
		
		[19.07.2022] Returns the Beamline object instead of the typical beamline name return of BeamlineSet 
		
		[26.09.2022] The callback procedure has a fixed name in Placet - "callback". The procedure can no longer be created here.
					By default sets the callback function to Machine.empty() to avoid errors when forgotten to declare
		
		[20.04.2023] Included another parser ("advanced"). It can substitute the the values with the given values in the text.
					Also, can evaluate 'expr []' and rememember the values that are set in the files with 'set var value'.
		......

		Parameters
		----------
		lattice: str
			The name of the file containing the lattice.

		Additional parameters
		---------------------
		name: str, default "default"
			The name of the beamline.
			When the lattice is given as a filename with Placet lattice, used to create the Beamline object and setup the lattice in Placet.
			When the lattice is given as a Beamline object is ignored! The 'Beamline.name' is used the setup the lattice in Placet
		callback: bool, default True
			If True creates the callback procedure in Placet by calling
				Placet.TclCall(script = "callback")
		cavities_setup: dict
			The dictionary containing the parameters for 'Machine.cavities_setup()'
		parser: str default "default"
			The type of parser to be used to read the file into a Beamline. The possibilities are (see Beamline._parsers): 
				"default": The file is well formated, all the settings are numerical, thus no '$e0' or 'expr [..]'
				"advanced": The file containes variables that are referenced. They are either in the file or defined by hand.
		parser_variables: optional
			The dict with the variables and their values that "advanced" parser is going to use to parse the file.
		debug_mode: bool default False
			If True, prints the information the parses processes
		parse_for_placet: bool default False
			[Only if "advanced" parser is used]. If True, feeds the parsed version of the lattice saved with 'to_placet()' function.
			Otherwise, feeds the original file given in lattice.

		Returns
		-------
		Beamline
			The created beamline.
		"""
		lattice_name = extra_params.get("name", "default")
		_parser = extra_params.get('parser', "default")
		if not _parser in Beamline._parsers:
			raise ValueError(f"'parser' - incorrect value. Accepts {Beamline._parsers}, received - {_parser}")
		if lattice_name in self.beamlines_invoked:
			raise Exception(f"Beamline with the name '{lattice_name}' already exists.")

		self.beamline = Beamline(lattice_name)
		self.beamline.read_from_file(lattice, debug_mode = extra_params.get('debug_mode', False), parser = _parser, parser_variables = extra_params.get('parser_variables', {}))
		self.beamlines_invoked.append(lattice_name)

		self.placet.BeamlineNew()
		if _parser == "advanced" and extra_params.get('parse_for_placet', True):
			self.beamline.to_placet(os.path.join(self._data_folder_, "lattice_for_placet.tcl"))
			self.placet.source(os.path.join(self._data_folder_, "lattice_for_placet.tcl"), additional_lineskip = 0)
		else:
			self.placet.source(lattice, additional_lineskip = 0)
		if extra_params.get("callback", True):
			self.placet.TclCall(script = "callback")
			self.set_callback(self.empty)

		self.placet.BeamlineSet(name = lattice_name)
		self.cavities_setup(**extra_params.get('cavities_setup', {}))
		return self.beamline

	@term_logging
	def import_beamline(self, lattice: Beamline, **extra_params) -> Beamline:
		"""
		Import the Beamline in Placet.

		Parameters
		----------
		lattice: Beamline
			The Beamline to import

		Additional parameters
		---------------------
		callback: bool, default True
			If True creates the callback procedure in Placet by calling
				Placet.TclCall(script = "callback")
			
			!!Should be handled carefully! Some functions expect 'callback' procedure to exist. 
			Eg. eval_track_results() evaluates the macroparticles coordinates. To do so, 'callback' procedure is required.
		cavities_setup: dict
			The dictionary containing the parameters for 'Machine.cavities_setup()'
		"""
		if lattice.name in self.beamlines_invoked:
			raise Exception(f"Beamline with the name '{lattice.name}' already exists.")

		self.beamline = lattice
		self.beamlines_invoked.append(lattice.name)

		self.placet.BeamlineNew()
		lattice.to_placet(os.path.join(self._data_folder_, "lattice_for_placet.tcl"))
		self.placet.source(os.path.join(self._data_folder_, "lattice_for_placet.tcl"), additional_lineskip = 0)
		
		if extra_params.get("callback", True):
			self.placet.TclCall(script = "callback")
			self.set_callback(self.empty)

		self.placet.BeamlineSet(name = lattice.name)
		self.cavities_setup(**extra_params.get('cavities_setup', {}))
		return self.beamline

	def cavities_setup(self, **extra_params):
		"""
		Set the main cavities parameters
		.........
		It is required for the beam creation. Beams in Placet use the results from the command
			% calc wake.dat
		to have the values for the transverse (longitudinal?) wakes.

		calc functon from "wake_calc.tcl" uses the functions from "clic_beam.tcl". 
		These functions use the global variable 'structure'. 

		One has to provide all the additional parameters. Having zeros as default could lead to
		unexpected behaviour

		Additional parameters
		---------------------
		a: float
			to check
		g: float
			to check
		l: float
			to check
		delta: float
			to check
		delta_g: float
			to check
		phase: float
			Cavities phase
		frac_lambda: float
			to check
		scale: float
			to check
		"""
		_structure_list = ['a', 'g', 'l', 'delta', 'delta_g']
		structure_dict = {}
		for key in _structure_list:
			if not key in extra_params:
				self.console.log(f"[red] Warning! Machine.cavities_setup(): Parameter '{key}' is not given, using default value (0.0).")
				structure_dict[key] = 0.0
			else:
				structure_dict[key] = extra_params.get(key)
		for key in ['phase', 'frac_lambda', 'scale']:
			if not key in extra_params:
				self.console.log(f"[red] Warning! Machine.cavities_setup(): Parameter '{key}' is not given, using default value (0.0).")
				
		self.placet.set_list("structure", **structure_dict)
		#some go separately
		self.placet.set("phase", extra_params.get('phase', 0.0))
		self.placet.set("frac_lambda", extra_params.get('frac_lambda', 0.0))
		self.placet.set("scale", extra_params.get('scale', 1.0))

	def survey_errors_set(self, **extra_params):
		"""
		Set the survey default errors for the machine.
		
		Overwrites the Placet.SurveyErrorSet and sets the values not provided by the user to zero by default.
		Original Placet.SurveyErrorSet only overwrites the values provided by the user, rest remain unchanged.

		Additional parameters
		---------------------
		//**// All the parameters Placet.SurveyErrorSet accepts//**//
		"""
		errors_dict = {}
		for error in self.placet.survey_erorrs:
			errors_dict[error] = extra_params.get(error, 0.0)
		self.placet.SurveyErrorSet(**errors_dict)

	def assign_errors(self, survey: str = None, **extra_params):
		"""
		Assign the alignment errors to the beamline. 
		Uses given survey and the given static errors to misalign the beamline.

		Parameters
		----------
		survey: str, optional
			If survey is None, by default applying 'empty' survey

		Additional parameters
		---------------------
		static_errors: dict
			The dict containing the statice errors of the lattice.
			This data is used when invoking Placet.SurveyErrorSet
			Is required when invoking 'default_clic' survey.
			//**// The dict can contain all the parameters Placet.SurveyErrorSet accepts //**//
		errors_seed: int
			The seed for errors sequence.
			If not defined, the random number is used
		filename: str
			When "from_file" survey is used
		//**// Also accepts all the parameters of Placet.InterGirderMove //*//
		"""
		if not survey in (self.surveys + [None]):
			raise ValueError("survey is not recognized")

		if survey == "default_clic":
			self.survey_errors_set(**extra_params.get('static_errors', {}))
			self.placet.RandomReset(seed = extra_params.get('errors_seed', int(random.random() * 1e5)))
			self.default_clic(**dict(extra_params))
			self._update_lattice_misalignments(cav_bpm = 1, cav_grad_phas = 1)

		if survey == "from_file":
			if not 'filename' in extra_params:
				raise Exception("No file provided for the survey 'from_file'")
			self.beamline.read_misalignments(extra_params.get('filename'), cav_bpm = 1, cav_grad_phas = 1)

		if (survey == "empty") or (survey is None):
			pass

	def make_beam_particles(self, e_design: float, e_spread: float, n_particles: int, **extra_params) -> pd.DataFrame:
		"""
		Generate the particles distribution. Does not generate the beam!

		Equivalent to the procedure of the same name from PLACET file 'make_beam.tcl'
		
		Parameters
		----------
		e_design: float
			The beam design energy in [GeV]
		e_spread: float
			The beam energy spread in [%]
		n_particles: int
			Number of particles in the beam

		Additional parameters
		---------------------
		sigma_z: float
			Bunch length
		beta_x: float
			Horizontal beta-function
		beta_y: float
			Vertical beta-function
		alpha_x: float
			Horizontal alpha-function
		alpha_y: float
			Vertical alpha-function
		emitt_x: float
			Horizontal normalized emittance
		emitt_y: float
			Vertical normalized emittance

		Returns
		-------
		DataFrame
			The particles' coordinates
		"""
		_options_list = ['sigma_z', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y']
		for value in _options_list:
			if not value in extra_params:
				raise Exception(f"The parameter '{value}' is missing!")

		emittance_x = extra_params.get('emitt_x') * 1e-7 * 0.511e-3 / e_design
		emittance_y = extra_params.get('emitt_y') * 1e-7 * 0.511e-3 / e_design

		sigma_x = np.sqrt(emittance_x * extra_params.get('beta_x')) * 1e6
		sigma_y = np.sqrt(emittance_y * extra_params.get('beta_y')) * 1e6
		sigma_px = np.sqrt(emittance_x / extra_params.get('beta_x')) * 1e6
		sigma_py = np.sqrt(emittance_y / extra_params.get('beta_y')) * 1e6
		sigma_z = extra_params.get('sigma_z')
		sigma_E = 0.01 * np.abs(e_spread)

		e, x, y, z, px, py = [], [], [], [], [], []
		if e_spread < 0:
			for i in range(n_particles):
				e.append(e_design * (1.0 + sigma_E * (random.uniform(0, 1) - 0.5)))
				z_tmp = random.gauss(0, sigma_z)
				while np.abs(z_tmp) >= 3 * sigma_z:
					z_tmp = random.gauss(0, sigma_z)
				z.append(z_tmp)

				x.append(random.gauss(0, sigma_x))
				y.append(random.gauss(0, sigma_y))

				px.append(random.gauss(0, sigma_px) - extra_params.get('alpha_x') * x[-1] * sigma_px / sigma_x)
				py.append(random.gauss(0, sigma_py) - extra_params.get('alpha_y') * x[-1] * sigma_py / sigma_y)
		else:
			for i in range(n_particles):
				e_offset = random.gauss(0, sigma_E)
				while np.abs(e_offset) >= 3 * sigma_E:
					e_offset = random.gauss(0, sigma_E)
				e.append(e_design * (1.0 + e_offset))

				z_tmp = random.gauss(0, sigma_z)
				while np.abs(z_tmp) >= 3 * sigma_z:
					z_tmp = random.gauss(0, sigma_z)
				z.append(z_tmp)

				x.append(random.gauss(0, sigma_x))
				y.append(random.gauss(0, sigma_y))

				px.append(random.gauss(0, sigma_px) - extra_params.get('alpha_x') * x[-1] * sigma_px / sigma_x)
				py.append(random.gauss(0, sigma_py) - extra_params.get('alpha_y') * x[-1] * sigma_py / sigma_y)

		particle_coordinates = pd.DataFrame({'E': e, 'x': x, 'y': y, 'z': z, 'px': px, 'py': py})
		particle_coordinates = particle_coordinates.sort_values('z')

		return particle_coordinates

	@term_logging
	def make_beam_many(self, beam_name: str, n_slice: int, n: int, **extra_params) -> str:
		"""
		Generate the particle beam
		
		Similar to 'make_beam_many' in Placet TCl but rewritten in Python
		........
		
		Practically could pass the whole beam_setup to the function. Keep the same structure as in Placet
		Optional parameters (if not given, checks self.beam_parameters. If self.beam_parameters does not have them throws an Exception)
		
		Parameters
		----------
		beam_name: str
			Name of the beam
		n_slice: int
			Number of the slices
		n_macroparticles: int
			Number of the particles per slice
	
		Additional parameters
		---------------------
		sigma_z: float
			Bunch length
		charge: float
			Bunch charge
		beta_x: float
			Horizontal beta-function
		beta_y: float
			Vertical beta-function
		alpha_x: float
			Horizontal alpha-function
		alpha_y: float
			Vertical alpha-function
		emitt_x: float
			Horizontal normalized emittance
		emitt_y: float
			Vertical normalized emittance
		e_spread: float
			Energy spread
		e_initial: float
			Initial energy
		n_total: int
			Total number of the particles

		Returns
		-------
		str
			The beam name
		"""
		if self.beamlines_invoked == []:
			raise Exception("No beamlines created, cannot create a beam. Create the beamline first")
		if beam_name in self.beams_invoked:
			raise ValueError(f"Beam with the name '{beam_name}' already exists!")

		_options_list = ['sigma_z', 'charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'n_total']
		for value in _options_list:
			if not value in extra_params:
				raise Exception(f"The parameter '{value}' is missing!")

		beam_setup = {
			'bunches': 1,
			'macroparticles': n,
			'particles': extra_params.get('n_total'),
			'energyspread': 0.01 * extra_params.get('e_spread') * extra_params.get('e_initial'),
			'ecut': 3.0,
			'e0': extra_params.get('e_initial'),
			'file': self.placet.wake_calc(os.path.join(self._data_folder_, "wake.dat"), extra_params.get('charge'), -3,  3, extra_params.get('sigma_z'), n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x')
		}
		self.placet.InjectorBeam(beam_name, **beam_setup)

		self.placet.SetRfGradientSingle(beam_name, 0, "{1.0 0.0 0.0}")
		
		particle_beam_setup = {
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x'),
			'sigma_z': extra_params.get('sigma_z')
		}
		particles_distribution = self.make_beam_particles(extra_params.get('e_initial'), extra_params.get('e_spread'), n_slice * n, **particle_beam_setup)
		particles_distribution.to_csv(os.path.join(self._data_folder_, "particles.in"), sep = ' ', index = False, header = False)

		self.placet.BeamRead(beam = beam_name, file = os.path.join(self._data_folder_, "particles.in"))

		return beam_name

	@term_logging
	def make_beam_slice_energy_gradient(self, beam_name: str, n_slice: int, n_macroparticles: int, eng: float, grad: float, beam_seed: int = 1234, **extra_params) -> str:
		"""
		Generate the sliced beam
		
		Similar to 'make_beam_slice_energy_gradient' in Placet TCL but rewritten in Python
		.......
		One has to provide all the additional parameters otherwise the beam creation will fail.

		Parameters
		----------
		beam_name: str
			Name of the beam
		n_slice: int
			Number of the slices
		n_macroparticles: int
			Number of the macroparticles per slice
		eng: float
			Initial energy offset
		grad: float
			Accelerating gradient offset
		beam_seed: int, default 1234
			The seed number of the random number distribution
		
		Additional parameters
		---------------------
		sigma_z: float
			Bunch length
		charge: float
			Bunch charge
		beta_x: float
			Horizontal beta-function
		beta_y: float
			Vertical beta-function
		alpha_x: float
			Horizontal alpha-function
		alpha_y: float
			Vertical alpha-function
		emitt_x: float
			Horizontal normalized emittance
		emitt_y: float
			Vertical normalized emittance
		e_spread: float
			Energy spread
		e_initial: float
			Initial energy
		n_total: int
			Total number of the particles

		Returns
		-------
		str
			The beam name
		"""
		if self.beamlines_invoked == []:
			raise Exception("No beamlines created, cannot create a beam. Create the beamline first")
		if beam_name in self.beams_invoked:
			raise ValueError(f"Beam with the name '{beam_name}' already exists!")

		_options_list = ['charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'sigma_z', 'n_total']
		for value in _options_list:
			if not value in extra_params:
				raise Exception(f"The parameter '{value}' is missing!")

		self.placet.RandomReset(seed = beam_seed)

		beam_setup = {
			'bunches': 1,
			'macroparticles': n_macroparticles,
			'particles': extra_params.get('n_total'),
			'energyspread': 0.01 * extra_params.get('e_spread') * extra_params.get('e_initial'),
			'ecut': 3.0,
			'e0': eng * extra_params.get('e_initial'),
			'file': self.placet.wake_calc(os.path.join(self._data_folder_, "wake.dat"), extra_params.get('charge'), -3,  3, extra_params.get('sigma_z'), n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x')
		}
		self.placet.InjectorBeam(beam_name, **beam_setup)
		
		self.placet.SetRfGradientSingle(beam_name, 0, "{" + str(grad) +  " 0.0 0.0}")
		self.beams_invoked.append(beam_name)

		return beam_name

	def _get_bpm_readings(self) -> pd.DataFrame:
		"""
		Evaluate the BPMs reading and return as a DataFrame

		Returns:
		DataFrame
			BPMs reading
		"""
		_tmp_filename = os.path.join(self._data_folder_, "bpm_readings.dat")
		bpms = [element for element in self.beamline.extract(['Bpm'])]
		self.placet.BpmReadings(file = _tmp_filename)
		res = pd.DataFrame(columns = ['id', 's', 'x', 'y'])

		i = 0
		with open(_tmp_filename, 'r') as f:
			for line in f:
				tmp = list(map(lambda x: float(x), line.split()))
				res = res.append(dict(id = bpms[i].index, s = bpms[i].settings['s'], x = tmp[1], y = tmp[2]), ignore_index = True)
				i += 1
		return res

	def update_misalignments(func: Callable):
		"""Decorator for updating the beamline alignment"""
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			res = func(self, *args, **kwargs)
			self._update_lattice_misalignments(cav_bpm = 1, cav_grad_phas = 1)
			return res
		return wrapper

	def update_readings(func: Callable):
		"""Decorator for updating the BPMs reading"""
		def wrapper(self, *args, **kwargs):
			res = func(self, *args, **kwargs)
			for index, row in res.iterrows():
				self.beamline.lattice[int(row['id'])].settings['reading_x'] = row['x']
				self.beamline.lattice[int(row['id'])].settings['reading_y'] = row['y']
			return res
		return wrapper

	def verify_survey(func: Callable):
		"""Decorator used for verifying the correctness of the survey parameter passed to the track/correct routines"""
		@wraps(func)
		def wrapper(self, beam, survey = None, **kwargs):
			alignment = None
			if survey is None:
				_filename = os.path.join(self._data_folder_, "position_tmp.dat")
				self.beamline.save_misalignments(_filename, cav_bpm = True, cav_grad_phas = True)
				self.placet.declare_proc(self.from_file, file = _filename, cav_bpm = 1, cav_grad_phas = 1)
				alignment = "from_file"
			elif survey in Machine.surveys:
				alignment = survey
			else:
				raise ValueError(f"Incorrect survey. Accepted values are {Machine.surveys} or None")			
			return func(self, beam, alignment, **kwargs)
		return wrapper

	def add_beamline_to_final_dataframe(func: Callable):
		"""Decorator used to add the Beamline name used in the tracking/correction"""
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			res_dataframe = func(self, *args, **kwargs)
			res_dataframe['beamline'] = self.beamline.name
			return res_dataframe
		return wrapper

	@add_beamline_to_final_dataframe
	@verify_survey
	def _track(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""Perform the tracking without applying any corrections. For internal usage only"""
		return self.placet.TestNoCorrection(beam = beam, machines = 1, survey = survey, timeout = 100)

	@term_logging
	def track(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the tracking without applying any corrections

		Essentially, it is a wrapped version of Placet.TestNoCorrection.

		Parameters
		----------
		beam: str
			The name of the beam.
		survey: str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file" (default)
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it
			
			!!Mostly kept for compatibility, better not be used and have a default beaviour.
			The misalignments could be added separately in Machine.asisgn_errors()

		Returns
		-------
		DataFrame
			The tracking summary.
			
			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		return self._track(beam, survey)


	@update_readings
	@verify_survey
	def eval_orbit(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""
		Evaluate the beam orbit based on the BPM readings

		Parameters
		----------
		beam: str
			The name of the beam.
		survey, str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file"
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it

		Returns
		-------
		DataFrame
			The orbit along the beamline.
		"""
		self._track(beam)
		return self._get_bpm_readings()

	@term_logging
	def eval_twiss(self, beam: str, **extra_params) -> pd.DataFrame:
		"""
		Evaluate the Twiss parameters along the lattice.

		The method uses Placet.TwissPlotStep() function to evaluate the Twiss. Apparently, it evaluates the twiss for error-free Lattice, or
		alternatively, for the current misalignments in the lattice.
		......

		Paremeters
		----------
		beam: str
			Name of the beam to use for the calculation

		Additional parameters
		---------------------
		step: float
			Step size to be taken for the calculation. If less than 0 the parameters will be plotted only in the centres of the quadrupoles
		start: int
			First particle for twiss computation
		end: int
			Last particle for twiss computation
		list: list
			Save the twiss parameters only at the selected elements		
		file_read_only: filename
			The program just reads the Twiss table and does not generate it
		beamline: str
			The beamline to be used in the calculations
		
		Returns
		-------	
		DataFrame
			Returns a Pandas Dataframe with the Twiss
		"""
		_twiss_file = None
		if 'file_read_only' in extra_params:
			_twiss_file = extra_params.get('file_read_only')
		else:
			_twiss_file = os.path.join(self._data_folder_, "twiss.dat")
			self.placet.TwissPlotStep(**dict(extra_params, file = _twiss_file, beam = beam))
			
		res = pd.DataFrame(columns = ["id", "type", "s", "betx", "bety", 'alfx', 'alfy', 'Dx', 'Dy', 'E'])
		
		convert_line = lambda line: list(map(lambda x: float(x), line.split()))
		_HEADER_LINES, line_id = 18, 0
		twiss_current = 0.0, 0.0, {}
		with open(_twiss_file, 'r') as f:
			for line in f:
				line_id += 1
				if line_id <= _HEADER_LINES:
					continue

				data_list = convert_line(line)

				twiss_current = {
						"id": int(data_list[0]),
						"type": self.beamline.at(int(data_list[0])).type,
						"s": data_list[1],
						"betx": data_list[5],
						"bety": data_list[9],
						"alfx": data_list[6],
						"alfy": data_list[10],
						"Dx": data_list[11],
						"Dy": data_list[13],
						"E": data_list[2]
					}

				res = res.append(twiss_current, ignore_index = True)
		
		return res	

	@term_logging
	@add_beamline_to_final_dataframe
	@update_misalignments
	@verify_survey
	def one_2_one(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the 121 alignment

		Essentially, is a wrapped version of Placet.TestSimpleCorrection.

		Parameters
		----------
		beam: str
			The name of the beam used for correction
		survey: str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file"
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it
			
			!!Mostly kept for compatibility, better not be used and have a default beaviour.
			The misalignments could be added separately in Machine.asisgn_errors()
		
		Additional parameters
		---------------------
		//**// All the parameters Placet.TestSimpleCorrection accepts apart from beam, survey, and machines //**//

		Returns
		-------
		DataFrame
			The tracking summary

			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		return self.placet.TestSimpleCorrection(**dict(extra_params, beam = beam, machines = 1, survey = survey, timeout = 100))

	@term_logging
	@add_beamline_to_final_dataframe
	@update_misalignments
	@verify_survey
	def DFS(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the Dispersion Free Steering
		
		Before actually invoking the 'TestMeasuredCorrection' command in Placet, runs 'Zero' command

		If bpms_realign is False - the reference orbit will not be saved. That means, that any further alignment will 
		typically use BPMs center as the best orbit solution (Eg. Rf alignment). 
		When it is True, runs the callback with 'BpmRealign' command. After performing the DFS, sets the callback to 'empty' (machine.empty)

		The default DFS parameters are:
		{
			'beam0': beam,
			'beam1': test_beam,
			'cbeam0': test_beam_2,
			'cbeam1': test_beam_3,
			'survey': "from_file",
			'machines': 1,
			'wgt1': 3,
			'bin_iteration': 1000,
			'correct_full_bin': 1,
			'binlength': 36,
			'binoverlap': 18,
			'bpm_res': 0.1,
			'emitt_file': "temp/emitt.dat",

			'timeout': 1000,
			'errors_file': alignment_file
		}
		.....

		Parameters
		----------
		beam: str
			The name of the beam used for correction
		survey: str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file"
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it		
			
			!!Mostly kept for compatibility, better not be used and have a default beaviour.
			The misalignments could be added separately in Machine.asisgn_errors()

		Additional parameters
		---------------------
		bpms_realign: bool, True
			If True, updates the reference orbit (bpm reading) by invoking a new callback procedure with 'BpmRealign' in it

		//**//Accepts all the parameters that TestMeasuredCorrection accepts (Check Placet.TestMeasuredCorrection) //**//

		Returns
		-------
		DataFrame
			The tracking summary

			The comlumns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		dfs_default_options = {
			'beam0': beam,
			'survey': survey,
			'machines': 1,
			'timeout': 1000,
			'emitt_file': os.path.join(self._data_folder_, "emitt_dfs.dat")
		}
		dfs_options = {**dfs_default_options, **extra_params}

		if extra_params.get("bpms_realign", True):
			def update_ref_orbit(**extra_params):
				self.placet.BpmRealign(**extra_params)
			self.set_callback(update_ref_orbit)

		self.placet.Zero()
		res = self.placet.TestMeasuredCorrection(**dfs_options)
		if extra_params.get("bpms_realign", True):
			self.placet.declare_proc(self.empty, name = "callback")
		return res

	@update_misalignments
	def _RF_align(self, beam: str, survey: str = None, **extra_params):
		self.placet.TestRfAlignment(**dict(extra_params, beam = beam, survey = survey, machines = 1))

	@term_logging
	@verify_survey
	def RF_align(self, beam: str, survey: str = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the RF alignment.

		Invokes Placet.TestRfAlignment(). After, runs Machine.track() to evaluate the emittance.

		Parameters
		----------
		beam: str
			The name of the beam used for correction
		survey: str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file"
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it		
		
		Additional parameters
		---------------------
		//**// All the parameters Placet.TestRfAlignment accepts apart from beam, survey, and machines //**//

		Returns
		-------
		DataFrame
			The tracking summary

			The comlumns of the resulting DataFrame:
			['correction', 'errors_seed', 'beam_seed', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		self.placet.Zero()
		self._RF_align(beam, survey, **extra_params)
		track_results = self._track(beam)
		track_results.correction = "RF align"
		return track_results

	def apply_knob(self, knob: Knob, amplitude: float):
		"""
		Apply the knob and update the beamline offsets.

		It is generaly safer to use this function instead of individual Knob.apply. Here, the checks are performed
		to ensure the elements involved in Knob correspond to the elements in Beamline.

		Parameters
		----------
		knob: Knob
			The given knob
		amplitude
			Amplitude to apply
		"""
		for element in knob.elements:
			if element not in self.beamline:
				raise ValueError("One or few elements involved in the given Knob are not present in the beamline!")

		knob.apply(amplitude)

	def eval_track_results(self, beam: str, beam_type: str = "sliced", **extra_params) -> (pd.DataFrame, float, float):
		"""
		Evaluate the beam parameters at the beamline exit.
		
		At the beginning of the run, if the calculation requires performing the tracking - sets the callback.
		Depending on the beam type, the different callback is defined. For sliced beam it is Machine.save_sliced_beam().
		For particle beam it is Machine.save_beam().

		The structure of the data in the files for the sliced beam:
			1. s long position along [um]
			2. weight
			3. energy [GeV]
			4. x [um]
			5. x' [um/m]
			6. y [um]
			7. y' [um/m]
			8. sigma_xx
			9. sigma_xx'
			10. sigma_x'x'
			11. sigma_yy
			12. sigma_yy'
			13. sigma_y'y'
			14. sigma_xy (always 0)
			15. 0
			16. 0
			17. 0

		The structure of the data in the files for the particle beam:
			1. energy [GeV]
			2. x [um]
			3. y [um]
			4. z [um]
			5. x' [urad]
			6. y' [urad]

		Parameters
		----------
		beam: str
			The beam to be used for tracking.
		beam_type: str, default "sliced"
			The type of the beam passed.

		Additional parameters
		---------------------
		keep_callback: bool, default False
			If True, does not change the callback function at the end of the run
		
		Returns
		-------
		DataFrame, float, float
			Returns the DataFrame with the particles' coordinates at the ML exit + final horizontal and vertical emittance
			
			The columns of the DataFrame includes are:
				Sliced beam:
				['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx']
				
				Particle beam:
				['E', 'x', 'y', 'z', 'px', 'py']

		"""
		if not beam_type in ["sliced", "particle"]:
			raise ValueError(f"'beam_type' incorrect value. Accepted values are ['sliced', 'particle']. Received '{beam_type}'")
		_filename = os.path.join(self._data_folder_, "particles.dat")

		callback_func, callback_params = self.callback_struct_

		#sliced beam
		if beam_type == "sliced":
			if (callback_func.__name__ == self.save_sliced_beam.__name__) and (callback_params == dict(file = _filename)):
				pass	#if the callback is there, no need to reset it
			else:
				self.set_callback(self.save_sliced_beam, file = _filename)
		if beam_type == "particle":
			if (callback_func.__name__ == self.save_beam.__name__) and (callback_params == dict(file = _filename)):
				pass	#if the callback is there, no need to reset it
			else:
				self.set_callback(self.save_beam, file = _filename)				
		track_res = self._track(beam)
		emitty, emittx = track_res.emitty[0], track_res.emittx[0]

		# reading the file
		_columns = []
		if beam_type == 'sliced':
			_columns = ['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx']
		if beam_type == 'particle':
			_columns = ['E', 'x', 'y', 'z', 'px', 'py']

		data_res, j = pd.DataFrame(columns = _columns), 0

		for data in get_data(_filename):
			data_tmp = pd.DataFrame({_columns[i]: data[i] for i in range(len(_columns))}, index = [j])
			j += 1
			data_res = pd.concat([data_res, data_tmp])
		if not extra_params.get("keep_callback", False):
			self.set_callback(self.empty)
		return data_res, emittx, emitty

	def eval_obs(self, beam: str, observables: List[str], **extra_params):
		"""
		Evaluate the values of the given observables at the end of the tracking.

		The observalbles could be the following:
			For particle beam:
			['E', 'x', 'y', 'z', 'px', 'py'] + ['emittx', 'emitty']
			For macroparticle beam:
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 
			'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 
			'sigma_ypx'] + ['emittx', 'emitty']

			The units for the coordinates are:
				E: GeV
				s(z), x, y, z: micrometer
				px, py: microrad,
				emittx, emitty: nm
			...

		Parameters
		----------
		beam: str
			The name of the beam to be used

			The beam with such a name should exist in Placet, otherwise Placet would throw an error
		observables: list(str)
			The variable to read from the tracking data when performing the scan
			This value can be one of the:
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
		
		Additional parameters
		---------------------
		beam_type: str, default "sliced"
			The type of the beam that is used in the tracking.

			The name of the beam does not indicate what type of the beam is used.
		Returns
		-------
		list:
			The values of the observables
		"""
		obs = []
		if set(observables).issubset(set(['emittx', 'emitty'])):
			#using the results of machine.track 
			track_results = self._track(beam)
			obs = [float(track_results[observable].values) for observable in observables]
		else:
			#running machine.eval_track_results to identify the coordinates etc.
			track_res, emittx, emitty = self.eval_track_results(beam, extra_params.get('beam_type', "sliced"))
			for observable in observables:
				if observable in ['emittx', 'emitty']:
					obs.append(emitty if observable == 'emitty' else emittx)
				else:
					obs.append(list(track_res[observable].values))
		
		return obs

	def iterate_knob(self, beam: str, knob: Knob, observables: List[str], knob_range: List[float] = [-1.0, 0.0, 1.0], **extra_params) -> dict:
		"""
		Iterate the knob. The knob is iterated in the given range and is reset at the end.
		
		Parameters
		----------
		beam: str
			The name of the beam to be used.

			The beam with such a name should exist in Placet, otherwise Placet would throw an error
		knob: Knob
			The knob to perform scan on
		observables: list(str)
			The variable to read from the tracking data when performing the scan
			This value can be one of the:
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
		knob_range: list, default [-1.0, 0.0, 1.0]
			The list of the knob values to perform the scan

		Optional parameters
		-------------------
		beam_type: str, default "sliced"
			The type of the beam used for the tracking
		fit: func
			Function to fit the data
			*Only works if the amound of observables is equaly 1.
		plot: func
			Function to plot the iteration data.
			*Only works if the amound of observables is equaly 1.
		Returns
		------
		dict: 
			The scan summary
		"""
		_obs_values = ['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 
					   'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
		if not set(observables).issubset(set(_obs_values)):
			raise ValueError(f"The observables(s) '{observables}' are not supported")

		observable_values, beam_type = [], extra_params.get('beam_type', "sliced")
		
		if not hasattr(self, '_CACHE_LOCK'):
			self._CACHE_LOCK = {'iterate_knob': False}	#the lock to prevent the cache from being modified by other functions
			self.beamline.cache_lattice_data(knob.elements)
		elif self._CACHE_LOCK['iterate_knob']:
			# this corresponds to the case when the values from the cache were not uploaded to the lattice
			# the reason for this could be the interruption of the execution of eval_obs() function
			self.beamline.upload_from_cache(knob.elements)
			self._CACHE_LOCK['iterate_knob'] = False
		else:
			self._CACHE_LOCK['iterate_knob'] = False
			self.beamline.cache_lattice_data(knob.elements)

		def console_table():
			table = Table(title = f"Performing {knob.name} scan")
			table.add_column("Amplitude", style = "green")
			for observable in observables:
				table.add_column(observable, style = "green")
			
			return table

		def _eval_obs(knob: Knob, amplitude: float):
			"""
			Maybe this function can be used universally, Machine wide.

			It sets the knob, runs the track, reverts the changes, and returns the observable values.
			*I use the similar function to test the knob performance.
			"""
			self.apply_knob(knob, amplitude)
			self._CACHE_LOCK['iterate_knob'] = True

			obs = self.eval_obs(beam, observables, beam_type = beam_type)
			
			self.beamline.upload_from_cache(knob.elements)
			self._CACHE_LOCK['iterate_knob'] = False

			return obs
		
		if self.console_output:
			table = console_table()	
			
			with Live(table, refresh_per_second = 10):
				for amplitude in knob_range:
					obs = _eval_obs(knob, amplitude)
					observable_values.append(obs)
					table.add_row(str(amplitude), *list(map(lambda x: str(x), obs)))
		else:
			for amplitude in knob_range:
				obs = _eval_obs(knob, amplitude)
				observable_values.append(obs)

		iter_data = json.dumps({'knob_range': list(knob_range), 'obs_data': observable_values})
		obs_f_element = list(map(lambda x: x[0], observable_values))

		fit_result = extra_params.get('fit')(knob_range, obs_f_element) if ('fit' in extra_params) and (len(observables) == 1) else None
		
		if self.console_output:
			if fit_result is not None:
				self.console.log("[green]" + fit_result[2])
			else:
				self.console.log("[green]No fit is used")

		if ('plot' in extra_params) and len(observables) == 1:
			if (fit_result != None) and fit_result[1] is not None:
				extra_params.get('plot')(knob_range, obs_f_element, fit_result[1])
			else:
				extra_params.get('plot')(knob_range, obs_f_element)
		
		if fit_result is not None:
			if fit_result[1] is not None:
				return {'scan_log': iter_data, 'fitted_value': fit_result[0], 'best_obs': fit_result[1](fit_result[0])}
			else:
				return {'scan_log': iter_data, 'fitted_value': fit_result[0], 'best_obs': None}
		else: 
			return {'scan_log': iter_data, 'fitted_value': None, 'best_obs': None}

	def within_range(func):
		"""Scan the knob until the optimal value is within the scan range"""	
		@wraps(func)
		def wrapper(self, beam, knob, observable, knob_range, fit_func, **extra_params):
			is_boundary = lambda knob_value: (knob_value == knob_range[0]) or (knob_value == knob_range[-1])
			res = func(self, beam, knob, observable, knob_range, fit_func, **extra_params)
			while is_boundary(res['knob_value'].values[-1]):
				res = res.append(func(self, beam, knob, observable, knob_range, fit_func, **extra_params), ignore_index = True)
			return res

		return wrapper

	@within_range
	def scan_knob(self, beam: str, knob: Knob, observable: str, knob_range: List[float], fit_func: Callable, **extra_params) -> pd.DataFrame:
		"""
		Scan the knob

		After the scan, the optimal knob value is saved in the memory in Beamline.beamline. 
		To update it in Placet, one has to call machine._update_lattice_misalignments()
		
		Parameters
		----------
		beam: str
			The beam used for the scan
		knob: Knob
			The knob to perform scan on
		knob_range: list, default [-1.0, 0.0, 1.0]
			The list of the knob values to perform the scan
		observable: str
			The variable to read from the tracking data when performing the scan

			Possible options include:
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 
			'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']

		fit_func: func(x, y)
			The fit function for the data

		Extra parameters
		----------------
		plot: func
			The function to plot the knob iteration of the format f(x, y)
		evaluate_optimal: bool, default True
			If True reevaluates the emittance by running TestNoCorrection

		Returns
		-------
		DataFrame
			The scan summary

		See also
		--------
		iterate_knob: Iterate the knob
		"""
		_options = ['plot', 'evaluate_optimal']

		fit_data = self.iterate_knob(beam, knob, [observable], knob_range, **dict(_extract_dict(_options, extra_params), fit = fit_func))

		self.apply_knob(knob, fit_data['fitted_value'])

		best_obs = fit_data['best_obs']
		if extra_params.get('evaluate_optimal', True):
			best_obs = self._track(beam)[observable].values[0]

		res = {
			'correction' : knob.name,
			'positions_file': None, 
			'emittx': None, 
			'emitty': best_obs,
			'knob_value': fit_data['fitted_value'],
			'scan_log': fit_data['scan_log']
		}
		return pd.DataFrame([res])

	def apply_quads_errors(self, strength_error = 0.0):
		"""
		Add the strength errors to all the quads

		Parameters
		----------
		strengths_error: float, default 0.0
			Standard relative deviation of the quadrupole strength
		"""
		for quad in self.beamline.extract(['Quadrupole']):
			quad.settings['strength'] += quad.settings['strength'] * random.gauss(0, strength_error)

		self._update_quads_strengths()	

	def apply_cavs_errors(self, phase_error = 0.0, grad_error = 0.0):
		"""
		Add the errors to the cavities phase and gradient

		Original function used Placet.ElementSetAttributes() to update cavs parameters, but is very slow
		[23/11/2022] Modified to use with Beamline
		....

		Parameters
		----------
		phase_error: float default 0.0
			Standard deviation of the phase (Absolue value)
		grad_error: float default 0.0
			Standard deviation of the gradient (Absolue value)
		"""
		for cav in self.beamline.extract(['Cavity']):
			cav.settings['phase'] += random.gauss(0, phase_error)
			cav.settings['gradient'] += random.gauss(0, grad_error)

		self._update_cavs_phases()
		self._update_cavs_gradients()

	def misalign_element(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element

		The offset is added to the element property in self.beamline
		
		Additional parameters
		---------------------
		element_index: int
			The id of the element in the lattice
		x: float default 0.0
			The horizontal offset in micrometers
		xp: float default 0.0
			The horizontal angle in micrometers/m
		y: float default 0.0
			The vertical offset in micrometers
		yp: float default 0.0
			The vertical angle in micrometers/m
		roll: float default 0.0
			The roll angle in microrad
		"""
		self.beamline.misalign_element(**extra_params)

	def misalign_elements(self, **extra_params):
		"""
		Apply the geometrical misalignments to the elements in the dictionary

		Additional parameters
		---------------------
		offsets_data: dict
			The dictionary with the elements offsets in the following format
			{
				'element_id1': {
					'x': ..
					'y': ..
					..
				}
				'element_id2':{
					..
				}
				..
			}
		"""
		self.beamline.misalign_elements(**extra_params)

	def misalign_articulation_point(self, **extra_params):
		"""
		Offset the articulation point either between 2 girders or at the beamline start/end.

		The girders and elements on them are misalligned accordingly.

		Additional parameters
		---------------------
		girder_left: int, optional
			The id of the girder to the left of the articulation point
		girder_right: int, optional
			The id of the girder to the roght of the articulation point
		x: float, default 0.0
			The horizontal offset in micrometers
		y: float, default 0.0
			The vertical offset in micrometers
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
			
		There is an option to provide the ids of the girders to the right and to the left of the articulation point.
		That require girder_right - girder_left = 1, otherwise an exception will be raised.

		It is possible to provide only 1 id either of the right or the left one. This also works for the start/end of the beamline

		"""
		self.beamline.misalign_articulation_point(**extra_params)
	
	def misalign_girder_2(self, **extra_params):
		"""
		Misalign the girder by means of moving its end points
		
		Additional parameters
		---------------------
		girder: int
			The id of the girder
		x_right: float default 0.0
			The horizontal offset in micrometers of right end-point
		y_right: float default 0.0
			The vertical offset in micrometers of the right end-point
		x_left: float default 0.0
			The horizontal offset in micrometers of left end-point
		y_left: float default 0.0
			The vertical offset in micrometers of the left end-point
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		"""
		self.beamline.misalign_girder_2(**extra_params)
	
	def misalign_girder(self, **extra_params):
		"""
		Offset the girder along with the elements on it.

		All the elements on the girder are equally misaligned.

		Additional parameters
		---------------------
		girder: int
			The id of the girder
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		x: float default 0.0
			The horizontal offset in micrometers
		xp: float default 0.0
			The horizontal angle in micrometers/m
		y: float default 0.0
			The vertical offset in micrometers
		yp: float default 0.0
			The vertical angle in micrometers/m
		roll: float default 0.0
			The roll angle in microrad
		tilt: float default 0.0
			The tilt angle in microrad
		"""
		self.beamline.misalign_girder(**extra_params)

	def misalign_girders(self, **extra_params):
		"""
		Misalign the girders

		Additional parameters
		---------------------
		offsets_data: dict
			The dictionary with the girders offsets in the following format
			{
				'girder_id1': {
					'x': ..
					'y': ..
					..
				}
				'girder_id2':{
					..
				}
				..
			}
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		"""
		self.beamline.misalign_girders(**extra_params)

	def from_file(self, **extra_params):
		"""
		Apply the survey that uses the misalignments from the file
	
		Additional parameters
		---------------------
		file: str
			The name of the file with the misalignments
		additional_lineskip: int, default 0
			Can only take the value of '0'. If not given, the default values for the commands are used
		"""
		if not 'file' in extra_params:
			raise Exception("'file' is not given")

		if extra_params.get('additional_lineskip', 0) != 0:
			raise ValueError("additional_lineskip given to survey-function can only be 0")
		
		self.placet.ReadAllPositions(**extra_params)

	def default_clic(self, **extra_params):
		"""
		Apply the default Clic survey to a lattice.
		
		The function calls Clic func in Placet. It requires the lattice misalignments to declared with clic.placet.SurveyErrorSet(**static_errors)
		
		Can be declared as a proc in Placet

		Additional Parameters
		---------------------
		additional_lineskip: int, default 0
			Can only take the value of '0'. If not given, the default values for the commands are used
		//**// Accepts the parameters for InterGirderMove (see Placet.InterGirderMove) 
			   and Placet.Clic (see Placet.Clic) //**//
		"""
		if extra_params.get('additional_lineskip', 0) != 0:
			raise Exception("additional_lineskip given to survey-function can only be 0")

		self.placet.Clic(**extra_params)
		self.placet.InterGirderMove(**extra_params)

	def empty(self, **extra_params):
		"""Apply the empty function"""
		pass
	
	def save_beam(self, **extra_params):
		"""
		Save the particle beam

		Additional parameters
		---------------------
		//**// Accepts all the parameters for Placet.BeamDump() //**//
		"""
		self.placet.BeamDump(**extra_params)

	def save_sliced_beam(self, **extra_params):
		"""
		Save the sliced beam

		Additional parameters
		---------------------
		//**// Accepts all the parameters for Placet.BeamSaveAll() //**//

		"""
		self.placet.BeamSaveAll(**extra_params)

	def phase_advance(self, start_id, end_id):
		"""
		Get the phase advance
		
		Does not work atm.

		Parameters
		----------
		start_id
			Element index of the first element
		end_id
			Element index of the last element

		"""
		transfer_matrix = self.placet.GetTransferMatrix(self.beamline, start = start_id, end = end_id)
		pass

	def _update_lattice_misalignments(self, **extra_params):
		"""
		Synchronize the misalignments in self.beamline with Placet

		1)Writes the lattice's misalignments stored in Placet to a file
		2)Proceeds it with Beamline.read_misalignments() to update the values in Python

		Writes the misalignments to 'position_tmp.dat' file

		......

		Additional parameters
		---------------------
		cav_bpm

		cav_grad_phas
		
		//**//TO UPDATE THE DESCRIPTION//**//
		"""
		_options_list, _tmp_file = ['cav_bpm', 'cav_grad_phas'], os.path.join(self._data_folder_, "position_tmp.dat")

		self.placet.SaveAllPositions(**_extract_dict(_options_list, extra_params), file = _tmp_file)
		self.beamline.read_misalignments(_tmp_file, **_extract_dict(_options_list, extra_params))

	def _update_quads_strengths(self, **extra_params):
		"""Synchronize the quads strength in self.beamline with Placet"""
		self.placet.QuadrupoleSetStrengthList(self.beamline._get_quads_strengths())

	def _update_cavs_phases(self, **extra_params):
		"""Synchronize the cavs phase in self.beamline with Placet"""
		self.placet.CavitySetPhaseList(self.beamline._get_quads_strengths())

	def _update_cavs_gradients(self, **extra_params):
		"""Synchronize the cavs phase in self.beamline with Placet"""
		self.placet.CavitySetGradientList(self.beamline._get_quads_strengths())
