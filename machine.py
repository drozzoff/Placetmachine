from .placet.placetwrap import Placet
from .lattice.placetlattice import PlacetLattice
from .util import Knob, CoordTransformation

import json
import time
import random
import pandas as pd
from rich.console import Console
from rich.errors import LiveError
from functools import wraps
import copy
import scipy as sp

import numpy as np
import warnings

from rich.table import Table
from rich.live import Live

import tempfile

_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

_get_data = lambda name: list(map(lambda x: [float(y) for y in x.split()], open(name, 'r')))
def get_data(filename) -> list:
	res = _get_data(filename)
	if res[-1] == []:
		res.pop(len(res) - 1)
	return res

cut = lambda data, index: list(map(lambda x: x[index], data))

def parabola(x, a, b, c) -> float:
	return a + b * (x - c)**2

def parabola_jac(x, a, b, c) -> np.array:
	J = np.zeros((len(x), 3))
	for i in range(len(x)):
		J[i][0] = 1
		J[i][1] = (x[i] - c)**2
		J[i][2] = -2 * b * (x[i] - c)

	return J

def parabola_fit(knob_range, observable_values, **kwargs) -> list:
	"""
	Apply the parabolic fit for the knob scan
	
	Parameters
	----------
	knob_range: list
		The knob values
	observable_values: list
		The observable values

	Additional parameters
	---------------------
	init_guess: [double, double, double] default [1e-13, 10, 0.0]
		The list of the initial guesses for the parabola
	ignore_restrictions: bool default False
		If True, the initial fit result check is ignored
	transform_observables: func, optional
		If given, transforms each observable as func(obs) before doing the fit.
										
	Returns
	-------
	[double, func, message]
		The fitting summary of the format
		[
			fit_center,			- double; center of the Gaussian fit
			fit_func			- func; resulting fit function
			message				- str; message from the fit
		]
	"""
	convert = kwargs.get('transform_observables', None)
	if convert is not None:
		observable_values = [convert(obs) for obs in observable_values]
	try: 
		fit_params, pcov = sp.optimize.curve_fit(parabola, knob_range, observable_values, kwargs.get("init_guess", [1e-13, 10, 0.0]), None, True, True, [-np.inf, np.inf], 'lm', parabola_jac)
	except RuntimeError:
		''' fitting failed, setting to zero '''
		return [sum(knob_range) / len(knob_range), None, "Fitting failed! Setting to zero"]

	if kwargs.get('ignore_restrictions', False):
		''' fitting succeeded, skipping the restrictions'''
		return [fit_params[2], lambda x: parabola(x, *fit_params), "Fit is correct! Smallest obs for " + str(fit_params[2])]

	""" Check of the fitting effectiveness """
	if fit_params[1] == 0:
		'''	incorrect fit, taking the average value'''
		return [sum(knob_range) / len(knob_range), None, "Fit is not correct! Setting to zero"]

	if fit_params[1] < 0.0:
		if fit_params[2] > 0.0:
			return [knob_range[0], None, "Fit is not correct! Setting to the boundary"]
		else:
			return [knob_range[1], None, "Fit is not correct! Setting to the boundary"]
	else:
		
		optimal = fit_params[2]
		'''Checking the boundaries'''
		if optimal > knob_range[-1]: optimal = knob_range[-1]
		if optimal < knob_range[0]: optimal = knob_range[0]

		return [optimal, lambda x: parabola(x, *fit_params), "Fit is correct! Smallest obs for " + str(optimal)]

class Machine():
	"""
	A class used for controling the beamline in Placet

	Uses placet_wrap.Placet interface to Placet and lattice_parse.PlacetLattice for controling the beamline.

	Changes the logic of using the Placet for beam tracking. By default, the number of the machines is set to 1.
	Each Machine instance corresponds to 1 actual beamline. The beamline is described with PlacetLattice.
	All the corrections are applied to the current machines with the current offsets by default. Though, one can
	overwrite that with the typical survey functions, which violates the logic of this class.
	
	...

	Attributes
	----------
	placet: placet_wrap.Placet
		A Placet object, used for communicating with the Placet process running in the background
	console: rich.console.Console
		An object used for the fancy terminal output
	beamline: lattice_parse.PlacetLattice, optional
		An object storing the beamline info
	beam_parameters: dict
		Dict storing the key info, neede for the Placet running. Primarily used for the beam creation
	callback_struct_: tuple(func, dict)
		The function that is currently used as callback for the tracking along with its parameters
	_data_folder_: str
		The name of the folder where the temporary files produced by Placet are stored

	Methods
	-------
	create_beamline(lattice, **extra_params) -> lattice_wrap.PlacetLattice
		Create the beamline.
	cavities_setup(**extra_params)
		Set up the cavities of the ML.
	make_beam_many(beam_name, n_slice, n_macroparticles, beam_seed = 1234, **extra_params) -> str
		Create the particle beam
	make_beam_slice_energy_gradient(beam_name, n_slice, n_macroparticles, eng, grad, beam_seed = 1234, **extra_params) -> str
		Create the sliced beam.
	assign_errors(survey = None, **extra_params)
		Apply the lattice missalignments
	apply_quads_errors(strength_error = 0.0)
		Apply the quadrupoles strengths errors
	apply_cavs_errors(phase_error = 0.0, grad_error = 0.0)
		Apply the cavities phase and gradient errors
	save_beam(**extra_params)
		Save the beam with Placet.BeamDump() command
	save_sliced_beam(**extra_params):
		Save the beam with Placet.BeamSaveAll() command
	track(beam, survey = None, **extra_params) 
		Perform the tracking without applying any corrections
	DFS(beam, n_slices, n_macroparticles, **extra_params)
		Perform the Dispersion Free Steering
	one_2_one(beam, survey = None, **extra_params)
		Perform the 1-2-1 Beam Based alingment
	RF_align(beam, survey = None, **extra_params)
		Perform the RF alignment	| To be verified that it works correctly
	iterate_knob(beam, knob, knob_range = [-1.0, 0.0, 1.0], **extra_params)
		Iterate the given knob in the given range
	knob_scan(beam, knob, knob_range = [-1.0, 0.0, 1.0], **extra_params)
		Scan the knob in the given range, and if the fit is given, assign the knob to the center best value
	eval_twiss(beam, **extra_params)
		Evaluate the Twiss functions along the beamline
	eval_orbit(beam, survey = None, **extra_params)
		Evaluate the beam orbit based on the BPMs readings

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
		"""
		self.placet = Placet(save_logs = calc_options.get("save_logs", True), debug_mode = calc_options.get("debug_mode", False), send_delay = calc_options.get("send_delay", None))
		self.console_output = calc_options.get("console_output", True)

		#Sourcing the neccesarry scripts
		self.placet.source("clic_basic_single.tcl", additional_lineskip = 2)
		self.placet.source("clic_beam.tcl")
		self.placet.source("wake_calc.tcl")
		self.placet.source("make_beam.tcl")	#is optional
		self.placet.declare_proc(self.empty)
		self.beamline = None

		#I/O setup
		self.console = Console()
		self.setup_data_folder()

	def __repr__(self):
		return f"Machine(debug_mode = {self.placet.debug_mode}, save_logs = {self.placet._save_logs}, send_delay = {self.placet._send_delay}, console_output = {self.console_output}) && beamline = {repr(self.beamline)}"

	def __str__(self):
		return f"Machine(placet = {str(self.placet)}, beamline = {str(self.beamline)})"

	def setup_data_folder(self):
		"""Set the temporary folder in tmp/ folder"""
		self.dict = tempfile.TemporaryDirectory()
		self._data_folder_ = self.dict.name

	def term_logging(func):
		"""Decorator with the fancy status logging"""
		def status_message(func_name) -> str:

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

	def set_callback(self, func, **extra_params):
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
	def create_beamline(self, lattice, **extra_params) -> PlacetLattice:
		"""
		Create the beamline
		
		[19.07.2022] Returns the PlacetLattice object instead of the typical beamline name return of BeamlineSet 
		
		[26.09.2022] The callback procedure has a fixed name in Placet - "callback". The procedure can no longer be created here.
					By default sets the callback function to Machine.empty() to avoid errors when forgotten to declare
		......

		Parameters
		----------
		lattice: str
			The name of the file containing the lattice.

		Additional parameters
		---------------------
		name: str, default "default"
			The name of the beamline.
		callback: bool, default True
			If True creates the callback procedure in Placet by calling
				self.placet.TclCall(script = "callback")

		Returns
		-------
		PlacetLattice
			The created beamline.
		"""
		self.placet.BeamlineNew()
		self.placet.source(lattice, additional_lineskip = 0)
		if extra_params.get("callback", True):
			self.placet.TclCall(script = "callback")
			self.set_callback(self.empty)

		self.placet.BeamlineSet(name = extra_params.get("name", "default"))
		
		#parsing the lattice with PlacetLattice
		self.beamline = PlacetLattice(extra_params.get("name", "default"))
		self.beamline.read_from_file(lattice)
		return self.beamline

	def cavities_setup(self, **command_details):
		"""
		Set the main cavities parameters

		Required paramaters:
			cavity_structure		- dict; dictionary with the main cavity parameters (a, g, l, delta, delta_g)
			phase
			frac_lambda
			scale
		
		To be updated!

		Default cavity structure use
		"""
		#cavity structure
		self.cavity_structure = command_details.get('cavity_structure', None)

		self.placet.set_list("structure", **self.cavity_structure)

		self.phase = self.placet.set("phase", command_details.get('phase', 8.0))
		self.frac_lambda = self.placet.set("frac_lambda", command_details.get('frac_lambda', 0.25))
		self.scale = self.placet.set("scale", command_details.get('scale', 1.0))

	def assign_errors(self, survey = None, **extra_params):
		"""
		Assign the errors to the beamline.

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
		assert survey in (self.surveys + [None]), "Survey is not recongnized"

		if survey == "default_clic":
			self.placet.SurveyErrorSet(**extra_params.get('static_errors', {}))
			self.placet.RandomReset(seed = extra_params.get('errors_seed', int(random.random() * 1e5)))
			self.default_clic(**dict(extra_params))
			self._update_lattice_misalignments(cav_bpm = 1, cav_grad_phas = 1)

		if survey == "from_file":
			assert 'filename' in extra_params, "No file provided for the survey 'from_file'"
			self.beamline.read_misalignments(extra_params.get('filename'), cav_bpm = 1, cav_grad_phas = 1)

		if (survey == "empty") or (survey is None):
			pass

	@term_logging
	def make_beam_many(self, beam_name, n_slice, n_macroparticles, beam_seed = 1234, **extra_params) -> str:
		"""
		Generate the particle beam
		
		Similar to 'make_beam_many' in Placet TCl but rewritten in Python

		To check the function - placet.make_beam_particles does not exist (???)
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
			Horizontal emittance
		emitt_y: float
			Vertical emittance
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
		self.placet.beam_seed = self.placet.set("beam_seed", beam_seed)

		_options_list = ['sigma_z', 'charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'n_total']
		
		parameters = {}

		for option in _options_list:
			if option in extra_params:
				parameters[option] = extra_params.get(option)
			elif option in self.beam_parameters:
				parameters[option] = self.beam_parameters[option]
			else:
				raise Exception("Parameters " + option + " is not specified")

		beam_setup = {
			'bunches': 1,
			'macroparticles': n_macroparticles,
			'particles': parameters['n_total'],
			'energyspread': 0.01 * parameters['e_spread'] * parameters['e_initial'],
			'ecut': 3.0,
			'e0': parameters['e_initial'],
			'file': self.placet.wake_calc(self._data_folder_ + "/wake.dat", parameters['charge'], -3,  3, parameters['sigma_z'], n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': parameters['alpha_y'],
			'beta_y': parameters['beta_y'],
			'emitt_y': parameters['emitt_y'],
			'alpha_x:': parameters['alpha_x'],
			'beta_x': parameters['beta_x'],
			'emitt_x': parameters['emitt_x']
		}

		self.placet.InjectorBeam(beam_name, **beam_setup)

		self.placet.SetRfGradientSingle(beam_name, 0, "{1.0 0.0 0.0}")
		
		self.placet.set_list("match", **self.beam_parameters)	#for make_beam_particles, since it uses a bunch of external variables

		self.placet.make_beam_particles(self.e_initial, self.beam_parameters['e_spread'], self.n_slice * self.n, additional_lineskip = 2, timeout = 20.0)

		self.placet.BeamRead(beam = beam_name, file = "particles.in", timeout = 20.0)

		return beam_name

	@term_logging
	def make_beam_slice_energy_gradient(self, beam_name, n_slice, n_macroparticles, eng, grad, beam_seed = 1234, main_beam = True, **extra_params) -> str:
		"""
		Generate the sliced beam
		
		Similar to 'make_beam_slice_energy_gradient' in Placet TCL but rewritten in Python
		.......
		Optional parameters (if not given, checks self.beam_parameters. If self.beam_parameters does not have them throws an Exception)

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
		main_beam: bool, default True
			If True, the created beam is the primar beam for the tracking
		
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
			Horizontal emittance
		emitt_y: float
			Vertical emittance
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
		if main_beam:
			self.placet.beam_seed = self.placet.set("beam_seed", beam_seed)
		
		_options_list = ['charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'sigma_z', 'n_total']
		
		parameters = {}

		for option in _options_list:
			if option in extra_params:
				parameters[option] = extra_params.get(option)
			elif option in self.beam_parameters:
				parameters[option] = self.beam_parameters[option]
			else:
				raise Exception("Parameters " + option + " is not specified")

		beam_setup = {
			'bunches': 1,
			'macroparticles': n_macroparticles,
			'particles': parameters['n_total'],
			'energyspread': 0.01 * parameters['e_spread'] * parameters['e_initial'],
			'ecut': 3.0,
			'e0': eng * parameters['e_initial'],
			'file': self.placet.wake_calc(self._data_folder_ + "/wake.dat", parameters['charge'], -3,  3, parameters['sigma_z'], n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': parameters['alpha_y'],
			'beta_y': parameters['beta_y'],
			'emitt_y': parameters['emitt_y'],
			'alpha_x:': parameters['alpha_x'],
			'beta_x': parameters['beta_x'],
			'emitt_x': parameters['emitt_x']
		}
		self.placet.InjectorBeam(beam_name, **beam_setup)
		
		self.placet.SetRfGradientSingle(beam_name, 0, "{" + str(grad) +  " 0.0 0.0}")

		return beam_name

	def _get_bpm_readings(self) -> pd.DataFrame:
		"""
		Evaluate the BPMs reading and return as a DataFrame

		Returns:
		DataFrame
			BPMs reading
		"""
		_tmp_filename = self._data_folder_ + "/bpm_readings.dat"
		bpms = self.beamline.get_bpms_list()
		self.placet.BpmReadings(file = _tmp_filename)
		res = pd.DataFrame(columns = ['id', 's', 'x', 'y'])

		i = 0
		with open(_tmp_filename, 'r') as f:
			for line in f:
				tmp = list(map(lambda x: float(x), line.split()))
				res = res.append(dict(id = bpms[i].index, s = bpms[i].settings['s'], x = tmp[1], y = tmp[2]), ignore_index = True)
				i += 1
		return res

	def update_misalignments(func):
		"""Decorator for updating the beamline alignment"""
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			res = func(self, *args, **kwargs)
			self._update_lattice_misalignments(cav_bpm = 1, cav_grad_phas = 1)
			return res
		return wrapper

	def update_readings(func):
		"""Decorator for updating the BPMs reading"""
		def wrapper(self, *args, **kwargs):
			res = func(self, *args, **kwargs)
			for index, row in res.iterrows():
				self.beamline.lattice[int(row['id'])].settings['reading_x'] = row['x']
				self.beamline.lattice[int(row['id'])].settings['reading_y'] = row['y']
			return res
		return wrapper

	def verify_survey(func):
		"""Decorator used for verifying the correctness of the survey parameter passed to the track/correct routines"""
		@wraps(func)
		def wrapper(self, beam, survey = None, **kwargs):
			alignment = None
			if survey is None:
				_filename = self._data_folder_ + "/position_tmp.dat"
				self.beamline.save_misalignments(_filename, cav_bpm = True, cav_grad_phas = True)
				self.placet.declare_proc(self.from_file, file = _filename, cav_bpm = 1, cav_grad_phas = 1)
				alignment = "from_file"
			elif survey in Machine.surveys:
				alignment = survey
			else:
				raise ValueError("Incorrect survey. Accepted values are" + str(Machine.surveys) + " or None")

			return func(self, beam, alignment, **kwargs)
		return wrapper

#	@term_logging
	@verify_survey
	def track(self, beam, survey = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the tracking without applying any corrections

		Essentially, it is a wrapped version of Placet.TestNoCorrection.

		Parameters
		----------
		beam: str
			The name of the beam.
		survey: str, optional
			The type of survey to be used. One has to define the procedure in Placet in order to use it.
			
			if survey is None - uses the current alignment in self.beamline and runs using alignment "from_file"
			If the survey is given (One of "default_clic", "from_file", "empty") - distributes the elements according to it
			
		Returns
		-------
		DataFrame
			The tracking summary.
			
			The comlumns of the resulting DataFrame:
			['correction', 'errors_seed', 'beam_seed', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		return self.placet.TestNoCorrection(beam = beam, machines = 1, survey = survey, timeout = 100)

	@update_readings
	@verify_survey
	def eval_orbit(self, beam, survey = None, **extra_params) -> pd.DataFrame:
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
		self.placet.TestNoCorrection(beam = beam, machines = 1, survey = survey, timeout = 100)

		return self._get_bpm_readings()

	def eval_twiss(self, beam, **command_details) -> pd.DataFrame:
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
		step: int
			Step size to be taken for the calculation. If less than 0 the parameters will be plotted only in the centres of the quadrupoles
		start: int
			First particle for twiss computation
		end: int
			Last particle for twiss computation
		list: list
			Save the twiss parameters only at the selected elements		
		read_only: bool
			The program just reads the Twiss table and does not generate it
		beamline: str
			The beamline to be used in the calculations
		
		Returns
		-------	
		DataFrame
			Returns a Pandas Dataframe with the Twiss
		"""
		_twiss_file = file = self._data_folder_ + "/twiss.dat"
		if not command_details.get('read_only', False):
			self.TwissPlotStep(**dict(command_details, file = _twiss_file))

		res = pd.DataFrame(columns = ["id", "keyword", "s", "betx", "bety", 'alfx', 'alfy', 'mux', 'muy', 'Dx', 'Dy', 'E'])
		
		convert_line = lambda line: list(map(lambda x: float(x), line.split()))
		_HEADER_LINES, line_id, element_start = 18, 0, True
		mux_tmp, muy_tmp, twiss_current = 0.0, 0.0, {}

		with open(command_details.get('file'), 'r') as f:
			for line in f:
				line_id += 1
				if line_id <= _HEADER_LINES:
					continue

				data_list = convert_line(line)
				i = data_list[0]
				keyword = None
				if i in self.beamline.quad_numbers_list:
					keyword = "quad"
				elif i in self.beamline.cav_numbers_list:
					keyword = "cavity"
				elif i in self.beamline.bpm_numbers_list:
					keyword = "BPM"
				else:
					keyword = "drift"

				def get_phases():
					nonlocal element_start
					if element_start:
						element_start = False
						return twiss_current['mux'] if 'mux' in twiss_current else 0.0, twiss_current['muy'] if 'muy' in twiss_current else 0.0
					else:
						R = self.get_element_transverse_matrix(int(i), beamline = command_details.get('beamline'))
						R_11, R_12 = R[0][0], R[0][1]
						R_33, R_34 = R[2][2], R[2][3]
						element_start = True
						return twiss_current['mux'] + np.arctan2(R_12, R_11 * twiss_current['betx'] - R_12 * twiss_current['alfx']) / np.pi, twiss_current['muy'] + np.arctan2(R_34, R_33 * twiss_current['bety'] - R_34 * twiss_current['alfy'])/ np.pi

				mux, muy = get_phases()

				twiss_current = {
						"id": int(data_list[0]),
						"keyword": keyword,
						"s": data_list[1],
						"betx": data_list[5],
						"bety": data_list[9],
						"alfx": data_list[6],
						"alfy": data_list[10],
						"mux": mux,
						"muy": muy,
						"Dx": data_list[11],
						"Dy": data_list[13],
						"E": data_list[2]
					}

				res = res.append(twiss_current, ignore_index = True)
				i += 1
		
		return res	

	@term_logging
	@update_misalignments
	@verify_survey
	def one_2_one(self, beam, survey = None, **extra_params) -> pd.DataFrame:
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
		
		Additional parameters
		---------------------
		//**// All the parameters Placet.TestSimpleCorrection accepts apart from beam, survey, and machines //**//

		Returns
		-------
		DataFrame
			The tracking summary

			The columns of the resulting DataFrame:
			['correction', 'errors_seed', 'beam_seed', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		return self.placet.TestSimpleCorrection(**dict(extra_params, beam = beam, machines = 1, survey = survey, timeout = 100))

	@term_logging
	@update_misalignments
	@verify_survey
	def DFS(self, beam, survey = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the Dispersion Free Steering
		
		Before actially invoking the 'TestMeasuredCorrection' command in Placet, runs 'Zero' command

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
		
		Additional parameters
		---------------------
		alignment_file: str, optional
			The file containing the current beamline misalignments
		create_opt_beams: bool, default True
			If True, creates the optional beams for DFS
		n_slices: int, default 11
			number of the slices in the beam
		n_macroparticles: int, default 5
			number of the mactoparticles in a slice
		bpms_realign: bool, True
			If True, updates the reference orbit (bpm reading) by invoking a new callback procedure with 'BpmRealign' in it

		//**//Accepts all the parameters that TestMeasuredCorrection accepts (Check Placet.TestMeasuredCorrection) except
			beam0, beam1, cbeam1, machines, emitt_file)! 
			The additional beams are generated once per Machines instance as follow

				>>> beam1 = self.make_beam_slice_energy_gradient("test_beam", n_slices, n_macroparticles, 0.95, 0.9, int(random.random() * 1e5), False, n_total = 500)
				>>> cbeam0 = self.make_beam_slice_energy_gradient("test_beam_2", 1, 1, 1.0, 1.0, int(random.random() * 1e5), False, n_total = 500)
				>>> cbeam1 = self.make_beam_slice_energy_gradient("test_beam_3", 1, 1, 0.95, 0.9, int(random.random() * 1e5), False, n_total = 500)
			machines is set to 1
			emitt_file is set to "temp/emitt_dfs.dat" by default (crashes otherwise)

		Returns
		-------
		DataFrame
			The tracking summary

			The comlumns of the resulting DataFrame:
			['correction', 'errors_seed', 'beam_seed', 'survey', 'positions_file', 'emittx', 'emitty']
		"""
		n_slices, n_macroparticles = extra_params.get('n_slices', 11), extra_params.get('n_macroparticles', 5)
		if extra_params.get('create_opt_beams', True):
			beam1 = self.make_beam_slice_energy_gradient("test_beam", n_slices, n_macroparticles, 0.95, 0.9, int(random.random() * 1e5), False, n_total = 500)
			cbeam0 = self.make_beam_slice_energy_gradient("test_beam_2", 1, 1, 1.0, 1.0, int(random.random() * 1e5), False, n_total = 500)
			cbeam1 = self.make_beam_slice_energy_gradient("test_beam_3", 1, 1, 0.95, 0.9, int(random.random() * 1e5), False, n_total = 500)

		dfs_default_options = {
			'beam0': beam,
			'beam1': "test_beam",
			'cbeam0': "test_beam_2",
			'cbeam1': "test_beam_3",
			'survey': survey,
			'machines': 1,
			'timeout': 1000,
			'emitt_file': self._data_folder_ + "/emitt_dfs.dat"
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
	def _RF_align(self, beam, survey = None, **extra_params):
		self.placet.TestRfAlignment(**dict(extra_params, beam = beam, survey = survey, machines = 1))

	@term_logging
	@verify_survey
	def RF_align(self, beam, survey = None, **extra_params) -> pd.DataFrame:
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
		track_results = self.track(beam)
		track_results.correction = "RF align"
		return track_results

	def apply_knob(self, knob, amplitude, **extra_params):
		"""
		Apply the knob and update the beamline offsets

		Parameters
		----------
		knob: Knob
			The given knob
		amplitude
			Amplitude to apply

		Additional parameters
		---------------------
		cavs_only, default True
			If True, only cavities on girders are misaligned
		"""
		assert isinstance(knob, Knob), "knob has to be of Knob type"
		girders_offset, elements_offset = knob.apply(amplitude)
		self.misalign_girders(offset_data = girders_offset, cavs_only = extra_params.get('cavs_only', True), no_run = True)
		self.misalign_elements(offset_data = elements_offset, no_run = True)

	def eval_track_results(self, run_track = True, beam = None, **extra_params) -> (pd.DataFrame, float, float):
		"""
		Evaluate the beam parameters at the beamline exit
		
		At the beginning of the run, if the calculation requires performing the tracking - sets the callback
		The structure of the data in the files:

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
		
		Parameters
		----------
		run_track: bool, default True
			If True runs track() before reading the file
		beam: str, optional
			The beam to be used for tracking. If run_track == True, must to be defined

		Additional parameters
		---------------------
		filename: str, default "temp/particles.dat"
			The name of the file for the tracking data

			When run_track is False, reads the data directly from the file
		keep_callback: bool, default False
			If True, does not change the callback function at the end of the run
		
		Returns
		-------
		DataFrame, float, float
			Returns the DataFrame with the particles' coordinates at the ML exit + final horizontal and vertical emittance

			The columns of the DataFrame includes are:
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx']

			When run_track is False -> returns None as emittance value
		"""
		_filename, emitty = extra_params.get("filename", self._data_folder_ + "/particles.dat"), None
		if run_track:
			if beam is None:
				raise ValueError("Beam for the tracking is not defined!")
			callback_func, callback_params = self.callback_struct_
			if (callback_func.__name__ == self.save_sliced_beam.__name__) and (callback_params == dict(file = _filename)):
				pass	#if the callback is there, no need to reset it
			else:
				self.set_callback(self.save_sliced_beam, file = _filename)
			track_res = self.track(beam)
			emitty, emittx = track_res.emitty[0], track_res.emittx[0]

		_columns = ['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx']
		data_res, j = pd.DataFrame(columns = _columns), 0

		for data in get_data(_filename):
			data_tmp = pd.DataFrame({_columns[i]: data[i] for i in range(len(_columns))}, index = [j])
			j += 1
			data_res = pd.concat([data_res, data_tmp])
		if not extra_params.get("keep_callback", False):
			self.set_callback(self.empty)
		return data_res, emittx, emitty

	def iterate_knob(self, beam, knob, observables, knob_range = [-1.0, 0.0, 1.0], **extra_params) -> dict:
		"""
		Iterate the knob
		
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
		_obs_values = ['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
		assert set(observables).issubset(set(_obs_values)), "the parameter(s) " + str(observables) + " are not supported"

		observable_values, elements_to_modify = [], knob.types_of_elements
		self.beamline.cache_lattice_data(elements_to_modify)
		
		if self.console_output:
			table = Table(title = "Performing " + str(knob.name) + " scan")
			table.add_column("Amplitude", style = "green")
			for observable in observables:
				table.add_column(observable, style = "green")
			
			with Live(table, refresh_per_second = 10):
				for amplitude in knob_range:
					self.apply_knob(knob, amplitude)
					obs = []
					if set(observables).issubset(set(['emittx', 'emitty'])):
						#using the results of machine.track 
						track_results = self.track(beam)
						obs = [float(track_results[observable].values) for observable in observables]
					else:
						#running machine.eval_track_results to identify the coordinates etc.
						track_res, emittx, emitty = self.eval_track_results(True, beam)
						for observable in observables:
							if observable in ['emittx', 'emitty']:
								obs.append(emitty if observable == 'emitty' else emittx)
							else:
								obs.append(list(track_res[observable].values))
					observable_values.append(obs)
					self.beamline.upload_from_cache(elements_to_modify)
					
					table.add_row(str(amplitude), *list(map(lambda x: str(x), obs)))
		else:
			for amplitude in knob_range:
				self.apply_knob(knob, amplitude)
				obs = []
				if set(observables).issubset(set(['emittx', 'emitty'])):
					#using the results of machine.track 
					track_results = self.track(beam)
					obs = [float(track_results[observable].values) for observable in observables]
				else:
					#running machine.eval_track_results to identify the coordinates etc.
					track_res, emittx, emitty = self.eval_track_results(True, beam)
					for observable in observables:
						if observable in ['emittx', 'emitty']:
							obs.append(emitty if observable == 'emitty' else emittx)
						else:
							obs.append(list(track_res[observable].values))
				observable_values.append(obs)
				self.beamline.upload_from_cache(elements_to_modify)

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
		def wrapper(self, beam, knob, observable, knob_range = [-1.0, 0.0, 1.0], fit_func = parabola_fit, **extra_params):
			is_boundary = lambda knob_value: (knob_value == knob_range[0]) or (knob_value == knob_range[-1])
			res = func(self, beam, knob, observable, knob_range, fit_func, **extra_params)
			while is_boundary(res['knob_value'].values[-1]):
				res = res.append(func(self, beam, knob, observable, knob_range, fit_func, **extra_params), ignore_index = True)
			return res

		return wrapper

	@within_range
	def knob_scan(self, beam, knob, observable, knob_range = [-1.0, 0.0, 1.0], fit_func = parabola_fit, **extra_params) -> pd.DataFrame:
		"""
		Scan the knob

		After the scan, the optimal knob value is saved in the memory in PlacetLattice.beamline. 
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
		fit_func: func(x, y), default parabola_fit
			The fit function for the data
			By default, uses parabola_fit with optimal value corresponding to the center of parabola
			x - knob values; y - observable

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
			best_obs = self.track(beam)[observable].values[0]

		res = {
			'correction' : knob.name,
			'errors_seed': self.placet.errors_seed,
			'beam_seed': self.placet.beam_seed, 
			'survey': "knob_scan", 
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
		for quad in self.beamline.get_quads_list():
			quad.settings['strength'] += quad.settings['strength'] * random.gauss(0, strength_error)

		self._update_quads_strengths()	

	def apply_cavs_errors(self, phase_error = 0.0, grad_error = 0.0):
		"""
		Add the errors to the cavities phase and gradient

		Original function used Placet.ElementSetAttributes() to update cavs parameters, but is very slow
		[23/11/2022] Modified to use with PlacetLattice
		....

		Parameters
		----------
		phase_error: float default 0.0
			Standard deviation of the phase (Absolue value)
		grad_error: float default 0.0
			Standard deviation of the gradient (Absolue value)
		"""
		for cav in self.beamline.get_cavs_list():
			cav.settings['phase'] += random.gauss(0, phase_error)
			cav.settings['gradient'] += random.gauss(0, grad_error)

		self._update_cavs_phases()
		self._update_cavs_gradients()

	def misalign_element(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element

		The offset is added to the element property in self.beamline

		To have them in Placet as well, one has to use a flag no_run = False.
		This will invoke the Placet.ElementAddOffset() command
		
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
		no_run: bool default True
			If True, placet command ElementAddOffset is not invoked 
			!! To be used carefullt
		"""
		_options = ['x', 'xp', 'y', 'yp', 'roll']
		
		try:
			elem_id = extra_params.get('element_index')
		except KeyError:
			print("Element number is not given")
			return

		offsets_dict = _extract_dict(_options, extra_params)
		for key in offsets_dict:
			self.beamline.lattice[elem_id].settings[key] += offsets_dict[key]

		if not extra_params.get('no_run', True):
			self.placet.ElementAddOffset(elem_id, offsets_dict)

	def misalign_elements(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element

		The offsets are added to the elements in self.beamline. To push them in Placet, one has to run:
			>>> self.beamline.save_misalignments()
			>>> self.placet.ReadAllPositions()
		
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
		no_run: bool default False
			If True, placet command ElementAddOffset is not invoked
		"""
		_options = ['no_run']
		
		assert 'offset_data' in extra_params, "Offset data is not given"
		
		elements = extra_params.get('offset_data')
		for element in elements:
			self.misalign_element(element_index = int(element), **elements[element], **_extract_dict(_options, extra_params))

	def misalign_girder(self, **extra_params):
		"""
		Offset the elements on the girder

		Additional parameters
		---------------------
		girder: int
			The id of the girder
		cavs_only: bool default False
			If True, only offsets the cavities on the girder
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
		no_run: bool default True
			If True, placet command ElementAddOffset is not invoked
		"""
		_options = ['x', 'xp', 'y', 'yp', 'roll', 'tilt', 'no_run']

		assert 'girder' in extra_params, 'Girder number is not given'
		cavs_only = extra_params.get('cavs_only', False)
		for element in self.beamline.get_girder(extra_params.get('girder')):
			if cavs_only and element.type != "Cavity":
				continue
			self.misalign_element(**dict(_extract_dict(_options, extra_params), element_index = element.index))

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
		cavs_only: bool default False
			If True, only offsets the cavities on the girder
		no_run: bool default True
			If True, placet command ElementAddOffset is not invoked
		"""
		assert 'offset_data' in extra_params, "Girders are not given"

		_options = ['cavs_only', 'no_run']

		girders = extra_params.get('offset_data')
		for girder in girders:
			self.misalign_girder(girder = int(girder), **girders[girder], **_extract_dict(_options, extra_params))

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
		assert 'file' in extra_params, "file is not given"

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
		save_survey: str
			If given saves the survey to a file with a given name
		//**// Accepts the parameters for InterGirderMove (see Placet.InterGirderMove), and SaveAllPositions (see Placet.SaveAllPositions) and Placet.Clic (see Placet.Clic) //**//
		"""
		if extra_params.get('additional_lineskip', 0) != 0:
			raise Exception("additional_lineskip given to survey-function can only be 0")

		self.placet.Clic(**extra_params)
		self.placet.InterGirderMove(**extra_params)

		if 'save_survey' in extra_params:
			self.placet.SaveAllPositions(**dict(extra_params, file = extra_params.get('save_survey'), cav_bpm = 1, cav_grad_phas = 1))
			

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
		self.placet.BeamDump(file = extra_params.get('file', self._data_folder_ + "/particles.out"))

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
		2)Proceeds it with PlacetLattice.read_misalignments() to update the values in Python

		Writes the misalignments to 'position_tmp.dat' file

		......

		Additional parameters
		---------------------
		cav_bpm

		cav_grad_phas
		
		//**//TO UPDATE THE DESCRIPTION//**//
		"""
		_options_list, _tmp_file = ['cav_bpm', 'cav_grad_phas'], self._data_folder_ + "/position_tmp.dat"

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

def CLIC_tuning_bumps():
	
	CLIC = machine()
#	CLIC.run()
#	CLIC.test()
	CLIC.dfs_test()

#	CLIC.track_test()

	CLIC.end()
#	CLIC.make_beam_many("test_beam", 1234)

#@timing
def CLIC_ML_twiss():
	CLIC = machine()

	#CLIC.twiss_test()
	#CLIC.tracking_with_offset_test()
#	CLIC.tracking_with_offset_quad()
#	CLIC.tracking_monochrom_beam2()
	CLIC.tracking_monochrom_beam3(5)
#	CLIC.beam_orbit_test()
	CLIC.end()

#@timing
def CLIC_ML_test():
	CLIC = machine()
#	CLIC.beam_creation_test()
#	CLIC.tracking_test_sliced_beam_monochrom()
#	CLIC.wakes_investigation()
#	CLIC.end()

if __name__ == "__main__":
#	CLIC_tuning_bumps()
#	CLIC_ML_twiss()
	CLIC_ML_test()