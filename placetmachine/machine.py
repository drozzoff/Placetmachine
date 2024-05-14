import os
from typing import List, Callable, Optional
import json
import random
import pandas as pd
from rich.console import Console
from rich.errors import LiveError
from functools import wraps
import numpy as np
from rich.table import Table
from rich.live import Live
import tempfile
from placetmachine import Placet, Beamline
from placetmachine.lattice import Knob
from placetmachine.beam import Beam


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

_get_data = lambda name: list(map(lambda x: [float(y) for y in x.split()], open(name, 'r')))
def get_data(filename) -> List:
	res = _get_data(filename)
	if res[-1] == []:
		res.pop(len(res) - 1)
	return res

cut = lambda data, index: list(map(lambda x: x[index], data))

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
	"""
	Decorator used for verifying the correctness of the survey parameter passed to the track/correct routines
	
	It is important that the decorated function has the following signature:
	```
	result = func(self, beam, survey, **kwargs)
	```
	"""
	@wraps(func)
	def wrapper(self, beam, survey = None, **kwargs):
		alignment, result = None, None
		if survey is None:
			# Default behaviour - No survey, we use current beamline misalignments
			_filename = os.path.join(self._data_folder_, "position_tmp.dat")
			self.beamline.save_misalignments(_filename, cav_bpm = True, cav_grad_phas = True)
			self.placet.declare_proc(self.from_file, file = _filename, cav_bpm = 1, cav_grad_phas = 1)
			alignment = "from_file"
			result = func(self, beam, alignment, **kwargs)
		elif survey in Placet.surveys:
			# One of the Placet built-in surveys
			result = func(self, beam, survey, **kwargs)

			# syncing the offsets in `Machine.beamline` with Placet
			self._update_lattice_misalignments(cav_bpm = 1, cav_grad_phas = 1)
		else:
			raise ValueError(f"'{survey}' - incorrect survey. Accepted values are: {Machine.surveys + Placet.surveys}.")			
		
		return result
	return wrapper

def verify_beam(func: Callable):
	"""
	Decorator used to verify the beam used in the tracking/correction routines exist and was created
	within the current `Machine` instance.
	
	It is important that the decorated function has the following signature:
	```
	result = func(self, beam, survey, **kwargs)
	```
	"""
	@wraps(func)
	def wrapper(self, beam, *args, **kwargs):
		if not beam in self.beams_invoked:
			raise ValueError(f"Beam with a name '{beam.name}' does not exist!")
		return func(self, beam, *args, **kwargs)
	
	return wrapper

def add_beamline_to_final_dataframe(func: Callable):
	"""Decorator used to add the Beamline name used in the tracking/correction"""
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		res_dataframe = func(self, *args, **kwargs)
		res_dataframe['beamline'] = self.beamline.name
		return res_dataframe
	return wrapper

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

class Machine():
	"""
	A class used for controling the beamline in **Placet**.

	Uses Python interface to Placet ([`Placet`][placetmachine.placet.placetwrap.Placet]) and 
	[`Beamline`][placetmachine.lattice.lattice.Beamline] class for controling the beamline.

	Changes the logic of using the **Placet** for beam tracking. By default, the number 
	of the machines is set to **1**. Each `Machine` instance corresponds to 1 actual beamline. 
	The beamline is described with [`Beamline`][placetmachine.lattice.lattice.Beamline] object. 
	All the corrections are applied to the current machines with the current offsets by default. 
	Though, one can overwrite that with the typical survey functions, which violates the logic 
	of this class and also has to be used carefully.

	Attributes
	----------
	placet : Placet
		A [`Placet`][placetmachine.placet.placetwrap.Placet] object, used for communicating with 
		the Placet process running in the background.
	console : rich.console.Console
		An object used for the fancy terminal output.
	beamline : Optional[Beamline]
		An object storing the beamline info.
	beams_invoked : List[Beam]
		An object storing the beams that were created within current `Machine`.
	beamlines_invoked : List[str]
		An object storing the names of the beamlines that were created within the current `Machine`.
	callback_struct_ : tuple(Callable, dict)
		The function that is used as callback for the tracking along with its parameters.
	_data_folder_ : str
		The name of the folder where the temporary files produced by **Placet** are stored.
	"""

	misalignment_surveys = ["default_clic", "from_file", "empty", "misalign_element", "misalign_elements", 
			"misalign_girder", "misalign_girders"]
	surveys = [None]
	callbacks = ["save_sliced_beam", "save_beam", "empty"]

	def __init__(self, **calc_options):
		"""
		Other parameters
		----------------
		debug_mode : bool
			If `True` (default is `False`), runs `self.placet` in debug mode.
		save_logs : bool, default True
			If `True` (default is `True`), saves the execution logs by means of invoking 
			[`save_debug_info`][placetmachine.placet.placetwrap.Placet.save_debug_info] for `self.placet`.
		send_delay : Optional[float]
			The time delay before each data transfer to a Placet process (sometimes needed for stability).
		console_output : bool
			If `True` (default is `True`), prints the calculations progress in the console.
		show_intro : bool
			If `True` (default is `True`), prints the welcome message of Placet at the start.
		"""
		self.placet = Placet(save_logs = calc_options.get("save_logs", False), debug_mode = calc_options.get("debug_mode", False), 
					   send_delay = calc_options.get("send_delay", None), show_intro = calc_options.get("show_intro", True))
		self.console_output = calc_options.get("console_output", True)

		#Sourcing the neccesarry scripts
		dir_path = os.path.dirname(os.path.realpath(__file__))

		self.placet.source(os.path.join(dir_path, "placet_files/clic_basic_single.tcl"), additional_lineskip = 2)
		self.placet.source(os.path.join(dir_path, "placet_files/clic_beam.tcl"))
		self.placet.source(os.path.join(dir_path, "placet_files/wake_calc.tcl"))
		self.placet.source(os.path.join(dir_path, "placet_files/make_beam.tcl"))	#is optional
		self.placet.declare_proc(self.empty)
		self.beamline, self.beams_invoked, self.beamlines_invoked = None, [], []

		#I/O setup
		self.console = Console()
		self._setup_data_folder()

	def __repr__(self):
		return f"Machine(debug_mode = {self.placet.debug_mode}, save_logs = {self.placet._save_logs}, send_delay = {self.placet._send_delay}, console_output = {self.console_output}) && beamline = {repr(self.beamline)}"

	def __str__(self):
		beams_names_compiled = list(map(lambda x: x.name, self.beams_invoked))
		return f"Machine(placet = {self.placet}, beamline = {self.beamline}, beams available = {beams_names_compiled})"

	def _setup_data_folder(self):
		"""Set the temporary folder in tmp/ folder"""
		self.dict = tempfile.TemporaryDirectory()
		self._data_folder_ = self.dict.name

	def set_callback(self, func: Callable, **extra_params):
		"""
		Set the callback function for the tracking.

		By default, when a `Beamline` is created within `Machine`, a callback procedure is
		declared with [`TclCall`][placetmachine.placet.placetwrap.Placet.TclCall]. This procedure
		is going to be called every time the beam tracking through the beamline is performed. 
		The name of this procedure is set to `'callback'`. After the beamline creation the name
		of the function cannot be changed, but the actual procedure can be overwritten in Placet.
		And this is what this function does.

		It is primaraly used for saving the macroparticle and particle beams' distributions.
		Normally, one does not have to call it, but use the other function that set it 
		automatically.

		Parameters
		----------
		func
			Function for the callback.

		*Other parameters could be any keyword argument that the input `func` accepts.*
		"""
		self.placet.declare_proc(func, **dict(extra_params, name = "callback"))
		self.callback_struct_ = (func, extra_params)

	@term_logging
	def create_beamline(self, lattice: str, **extra_params) -> Beamline:
		"""
		Create the beamline in Placet from the input lattice file.

		The `beamline` attribute of `Machine` is going to be overwritten.

		Parameters
		----------
		lattice
			The name of the file containing the lattice.

		Other parameters
		----------------
		name : str
			The name of the beamline (By default is set to `"default"`).
		callback : bool
			If `True`(default is `True`) creates the callback procedure in Placet by invoking
			[`set_callback()`][placetmachine.machine.Machine.set_callback].
		cavities_setup : dict
			The dictionary containing the parameters for [`cavities_setup()`][placetmachine.machine.Machine.cavities_setup].
		parser : str
			The type of parser to be used to read the file into a `Beamline` object. 
			The possible options are described in [`Beamline`][placetmachine.lattice.lattice.Beamline]
		parser_variables : dict
			The dict with the variables and their values that parser is going to use to parse the file. Can only be used with
			`"advanced"` parcer of `Beamline`.
		debug_mode : bool
			If `True` (default is `False`), prints the information during the parsing processes.
		parse_for_placet : bool
			*[Only if `"advanced"` parser is used]*. If `True` (default is `False`), feeds the parsed version 
			of the lattice saved with [`Beamline.to_placet()`] function. Otherwise, feeds the original file given in lattice.

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
		self.beamline.read_placet_lattice(lattice, debug_mode = extra_params.get('debug_mode', False), parser = _parser, parser_variables = extra_params.get('parser_variables', {}))
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
		Import the existing `Beamline` object as a beamline into Placet.

		Parameters
		----------
		lattice
			The Beamline to import.

		Other parameters
		----------------
		callback : bool
			If `True`(default is `True`) creates the callback procedure in Placet by invoking
			[`set_callback()`][placetmachine.machine.Machine.set_callback].
			
			**!!Should be handled carefully! Some functions expect 'callback' procedure to exist. **
			Eg. [`eval_track_results()`][placetmachine.machine.Machine.eval_track_results] evaluates 
			the macroparticles coordinates. To do so, 'callback' procedure is required.
		cavities_setup : dict
			A dictionary containing the parameters for [`cavities_setup()`][placetmachine.machine.Machine.cavities_setup].
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
		Set the main cavities parameters.

		It is required for the beam creation. Beams in **Placet** use the results from the command
		
		```
		% calc wake.dat
		```
		to have the values for the transverse (longitudinal?) wakes.

		The `calc` function from the file `"wake_calc.tcl"` uses the functions from "clic_beam.tcl". 
		These functions utilize the global variable `structure'`. Thus, until these functions are
		substituted with Python alternatives, one has to call this function every time one sets the
		beamline. Moreover the macroparticles' weights are takendirectly from the file `"wake.dat"`.

		**One has to provide all the other parameters. Having zeros as default could lead to
		unexpected behaviour.**

		The variables `a`, `g`, `l`, `delta`, and `delta_g` are going to be declared in Placet in the
		form of structure by using [`Placet.set_list()`][placetmachine.placet.placetwrap.Placet.set_list].

		Other parameters
		----------------
		a : float
			to check
		g : float
			to check
		l : float
			to check
		delta : float
			to check
		delta_g : float
			to check
		phase : float
			Cavities phase. Default is `0.0`.
		frac_lambda : float
			to check. Default is `0.0`.
		scale : float
			to check. Default is `1.0`.
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
		Set the default errors for the Placet surveys.
		
		Overwrites the [`Placet.SurveyErrorSet()`][placetmachine.placet.placetwrap.Placet.SurveyErrorSet] 
		and sets the values not provided by the user to zero by default. Original 
		[`Placet.SurveyErrorSet()`][placetmachine.placet.placetwrap.Placet.SurveyErrorSet] only overwrites 
		the values provided by the user, not touching the rest.

		Other parameters are the same as for [`Placet.SurveyErrorSet()`][placetmachine.placet.placetwrap.Placet.SurveyErrorSet].
		The full list:
		```
		['quadrupole_x', 'quadrupole_y', 'quadrupole_xp', 'quadrupole_yp', 'quadrupole_roll', 
		'cavity_x', 'cavity_realign_x', 'cavity_y', 'cavity_realign_y', 'cavity_xp', 
		'cavity_yp', 'cavity_dipole_x', 'cavity_dipole_y', 'piece_x', 'piece_xp', 'piece_y', 
		'piece_yp', 'bpm_x', 'bpm_y', 'bpm_xp', 'bpm_yp', 'bpm_roll', 'sbend_x', 'sbend_y', 
		'sbend_xp', 'sbend_yp', 'sbend_roll']
		```
		Refer to [`Placet.SurveyErrorSet()`][placetmachine.placet.placetwrap.Placet.SurveyErrorSet] for more
		details.
		"""
		errors_dict = {}
		for error in self.placet.survey_erorrs:
			errors_dict[error] = extra_params.get(error, 0.0)
		self.placet.SurveyErrorSet(**errors_dict)

	def assign_errors(self, survey: Optional[str] = None, **extra_params):
		"""
		Assign the alignment errors to the beamline currently used (`beamline` attribute).
		Uses provided `survey` along with the static errors given as keyword arguments.
		The `survey` acts as an instruction on how to misalign the lattice.

		There are several options to misalign the beamline using different built-int 
		misalignment surveys (accessed through `Machine.misalignment_surveys`):
		```
		["default_clic", "from_file", "empty", "misalign_element", "misalign_elements", 
		"misalign_girder", "misalign_girders"]
		```
		These surveys are implemented as Python functions and can be called outside of the
		score of this function.
		
		- `"default_clic"` corresponds to the function 
		[`Machine.default_clic()`][placetmachine.machine.Machine.default_clic] and applies
		the misalignments according to 
		[`Placet.Clic()`][placetmachine.placet.placetwrap.Placet.Clic] survey.
		- `"from_file"` corresponds to the function
		[`Machine.from_file()`][placetmachine.machine.Machine.from_file] and applies the
		misalignments from the file.
		- `"empty"` corresponds to the function
		[`Machine.empty()`][placetmachine.machine.Machine.empty] and does not apply any
		misalignments.
		- `"misalign_element"` corresponds to the function
		[`Machine.misalign_element()`][placetmachine.machine.Machine.misalign_element] and 
		misaligns one element in the beamline.
		- `"misalign_elements"` corresponds to the function
		[`Machine.misalign_element()`][placetmachine.machine.Machine.misalign_elements] and 
		misaligns multiple element in the beamline.
		- `"misalign_girder"` corresponds to the function
		[`Machine.misalign_girder()`][placetmachine.machine.Machine.misalign_girder] and 
		misaligns one girder in the beamline.
		- `"misalign_girders"` corresponds to the function
		[`Machine.misalign_girders()`][placetmachine.machine.Machine.misalign_girders] and 
		misaligns multiple girders in the beamline.

		Parameters
		----------
		survey
			If survey is `None`, by default applying 'empty' survey.

		Other parameters
		----------------
		static_errors : dict
			The dict containing the static errors of the lattice. This data is used when 
			invoking 
			[`Machine.survey_errors_set()`][placetmachine.machine.Machine.survey_errors_set]
			Is required when using `"default_clic"` survey.
			All the possible settings are:
			```
			['quadrupole_x', 'quadrupole_y', 'quadrupole_xp', 'quadrupole_yp', 
			'quadrupole_roll', 'cavity_x', 'cavity_realign_x', 'cavity_y', 
			'cavity_realign_y', 'cavity_xp', 'cavity_yp', 'cavity_dipole_x', 
			'cavity_dipole_y', 'piece_x', 'piece_xp', 'piece_y', 'piece_yp', 
			'bpm_x', 'bpm_y', 'bpm_xp', 'bpm_yp', 'bpm_roll', 'sbend_x', 
			'sbend_y', 'sbend_xp', 'sbend_yp', 'sbend_roll']
			```
		errors_seed : int
			The seed for errors sequence.
			If not defined, the random number is used.
		filename : str
			When `"from_file"` survey is used, the `filename` is used to read the misalignments,
			otherwise ignored.
		
		Other keyword arguments accepted are the parameters of the 
		[`Placet.InterGirderMove()`][placetmachine.placet.placetwrap.Placet.InterGirderMove].
		"""
		if not survey in (self.misalignment_surveys + [None]):
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

		# TO DO
		# extend for other surveys.

	@term_logging
	def make_beam_many(self, beam_name: str, n_slice: int, n: int, **extra_params) -> Beam:
		"""
		Generate the particle beam.
		
		Wraps [`Beam.make_beam_many()`][placetmachine.beam.beam.Beam.make_beam_many].
		Similar to `make_beam_many` from "make_beam.tcl" in Placet but rewritten in Python.
		
		Practically could pass the whole beam_setup to the function. Keep the same structure as in Placet.
		Optional parameters (if not given, checks self.beam_parameters. If self.beam_parameters does not have them throws an Exception)
		
		Parameters
		----------
		beam_name
			Name of the beam.
		n_slice
			Number of the slices.
		n
			Number of the particles per slice.
	
		Other parameters
		----------------
		sigma_z : float
			**[Required]** Bunch length in micrometers. 
		charge : float
			**[Required]** Bunch charge.
		beta_x : float
			**[Required]** Horizontal beta-function.
		beta_y : float
			**[Required]** Vertical beta-function.
		alpha_x : float
			**[Required]** Horizontal alpha-function.
		alpha_y : float
			**[Required]** Vertical alpha-function.
		emitt_x : float
			**[Required]** Horizontal normalized emittance.
		emitt_y : float
			**[Required]** Vertical normalized emittance.
		e_spread : float
			**[Required]** Energy spread.
		e_initial : float
			**[Required]** Initial energy.
		n_total : int
			**[Required]** Total number of the particles.

		Returns
		-------
		str
			The beam name.
		"""
		if self.beamlines_invoked == []:
			raise Exception("No beamlines created, cannot create a beam. Create the beamline first")
		for beam in self.beams_invoked:
			if beam_name == beam.name:
				raise ValueError(f"Beam with the name '{beam_name}' already exists! The beam you want to create should have a different name")	

		particle_beam = Beam(beam_name, self.placet, "particle")
		particle_beam.make_beam_many(n_slice, n, **extra_params)

		self.beams_invoked.append(particle_beam)

		return particle_beam

	@term_logging
	def make_beam_slice_energy_gradient(self, beam_name: str, n_slice: int, n_macroparticles: int, eng: float, grad: float, beam_seed: Optional[int] = None, **extra_params) -> Beam:
		"""
		Generate the macroparticle (sliced) beam.
		
		Wraps [`Beam.make_beam_slice_energy_gradient()`][placetmachine.beam.beam.Beam.make_beam_slice_energy_gradient].
		Similar to `make_beam_slice_energy_gradient`from "make_beam.tcl" in Placet but rewritten in Python.

		Parameters
		----------
		beam_name
			Name of the beam.
		n_slice
			Number of the slices.
		n_macroparticles
			Number of the macroparticles per slice.
		eng
			Initial energy offset.
		grad
			Accelerating gradient offset.
		beam_seed
			The seed number of the random number distribution. If not given a random
			number in the range [1, 1000000] is taken.
		
		Other parameters
		----------------
		sigma_z : float
			**[Required]** Bunch length in micrometers. 
		charge : float
			**[Required]** Bunch charge.
		beta_x : float
			**[Required]** Horizontal beta-function.
		beta_y : float
			**[Required]** Vertical beta-function.
		alpha_x : float
			**[Required]** Horizontal alpha-function.
		alpha_y : float
			**[Required]** Vertical alpha-function.
		emitt_x : float
			**[Required]** Horizontal normalized emittance.
		emitt_y : float
			**[Required]** Vertical normalized emittance.
		e_spread : float
			**[Required]** Energy spread.
		e_initial : float
			**[Required]** Initial energy.
		n_total : int
			**[Required]** Total number of the particles.

		Returns
		-------
		str
			The beam name.
		"""
		if self.beamlines_invoked == []:
			raise Exception("No beamlines created, cannot create a beam. Create the beamline first")
		for beam in self.beams_invoked:
			if beam_name == beam.name:
				raise ValueError(f"Beam with the name '{beam_name}' already exists! The beam you want to create should have a different name")	

		sliced_beam = Beam(beam_name, self.placet, "sliced")
		sliced_beam.make_beam_slice_energy_gradient(n_slice, n_macroparticles, eng, grad, beam_seed, **extra_params)

		self.beams_invoked.append(sliced_beam)

		return sliced_beam

	def _get_bpm_readings(self) -> pd.DataFrame:
		"""
		Evaluate the BPMs reading and return them as a DataFrame.

		Returns
		-------
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

	@add_beamline_to_final_dataframe
	@verify_survey
	@verify_beam
	def _track(self, beam: Beam, survey: str = None) -> pd.DataFrame:
		"""Perform the tracking without applying any corrections. For internal use only."""
		return self.placet.TestNoCorrection(beam = beam.name, machines = 1, survey = survey, timeout = 100)

	@term_logging
	def track(self, beam: Beam, survey: Optional[str] = None) -> pd.DataFrame:
		"""
		Perform the tracking without applying any corrections.

		It is a wrapped version of 
		[`Placet.TestNoCorrection()`][placetmachine.placet.placetwrap.Placet.TestNoCorrection].
		When `survey` parameter is not provided (**Recommended**), the current
		misalignments in `self.beamline` are used. This is important, because 
		[`Placet.TestNoCorrection()`][placetmachine.placet.placetwrap.Placet.TestNoCorrection]
		does not offer such capabilities. It can only misalign the lattice according to some
		guidelines and ignores the misalignmenst prior to calling. 
		
		`Machine.track()` on the other hand relies on the data stored in `self.beamline`. 
		So, to overcome the limitation
		of [`Placet.TestNoCorrection()`][placetmachine.placet.placetwrap.Placet.TestNoCorrection]
		the default survey is set to `"from_file"` and the file used is the one produced for the
		current state of `self.beamline`.

		**[!!]** Be aware that Placet internally does not generate random numbers, but rather 
		takes pseudo random numbers from the sequence, uniquely defined by a seed value. So, if
		you run your `Machine` program with a Placet built-in surveys there is alway a chance you
		are going to get the same offsets sequence. To make sure that misalignments are different
		one has to run [`Placet.RandomReset`][placetmachine.placet.placetwrap.Placet.RandomReset]
		before the tracking with surveys. In
		[`Machine.assign_errors()`][placetmachine.machine.Machine.assign_errors] for example, this
		is invoked by default (set to a random value) if the `error_seed` parameter is not declared.

		Parameters
		----------
		beam
			The beam to use.
		survey
			The type of survey to be used. So far the accepted options are:
			```
			[None, "None", "Zero", "Clic", "Nlc", "Atl", 
			"AtlZero", "Atl2", "AtlZero2, "Earth"]
			```
			
			- If survey is `None` (**default**) - uses the current beamline alignment from 
			`self.beamline`.
			- The rest value are Placet built-in surveys. After it is used, the alignment
			in `self.beamline` is going to be updated with new values generated by a survey.

		Returns
		-------
		DataFrame
			The tracking summary.
			
			The columns of the resulting DataFrame:
			```
			['correction', 'beam', 'beamline', 'survey', 'positions_file', 'emittx', 'emitty']
			```
		"""
		return self._track(beam, survey)


	@update_readings
	def eval_orbit(self, beam: Beam) -> pd.DataFrame:
		"""
		Evaluate the beam orbit based on the BPM readings.

		Parameters
		----------
		beam
			The beam to use.

		Returns
		-------
		DataFrame
			The orbit along the beamline.
		"""
		self._track(beam)
		return self._get_bpm_readings()

	@term_logging
	@verify_beam
	def eval_twiss(self, beam: Beam, **extra_params) -> pd.DataFrame:
		"""
		Evaluate the Twiss parameters along the lattice.

		The method uses 
		[`Placet.TwissPlotStep()`][placetmachine.placet.placetwrap.Placet.TwissPlotStep] 
		function to evaluate the Twiss. 
		
		**(?)** Apparently, it evaluates the twiss for error-free Lattice, or
		alternatively, for the current misalignments in the lattice.

		Parameters
		----------
		beam
			The beam to use.

		Other parameters
		----------------
		step : float
			Step size to be taken for the calculation. If less than 0 the 
			parameters will be plotted only in the centres of the quadrupoles.
		start : int
			**(?)** First particle for twiss computation.
		end : int
			**(?)** Last particle for twiss computation
		list : List[int]
			Save the twiss parameters only at the selected elements.
		file_read_only : str
			When the parameter is given, the function just reads the Twiss 
			from this file and does not generate it.
		beamline : str
			The beamline to be used in the calculations.
		
		Returns
		-------	
		DataFrame
			Returns a Pandas Dataframe with the Twiss data.

			The table contains the following columns:
			```
			["id", "type", "s", "betx", "bety", 'alfx', 'alfy', 'Dx', 'Dy', 'E']
			```
		"""
		_twiss_file = None
		if 'file_read_only' in extra_params:
			_twiss_file = extra_params.get('file_read_only')
		else:
			_twiss_file = os.path.join(self._data_folder_, "twiss.dat")
			self.placet.TwissPlotStep(**dict(extra_params, file = _twiss_file, beam = beam.name))
			
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
						"type": self.beamline[int(data_list[0])].type,
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
	@verify_beam
	def one_2_one(self, beam: Beam, survey: Optional[str] = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the one-to-one (1-2-1) alignment.

		It is a wrapped version of 
		[`Placet.TestSimpleCorrection()`][placetmachine.placet.placetwrap.Placet.TestSimpleCorrection].

		Parameters
		----------
		beam
			The beam to use.
		survey
			The type of survey to be used. So far the accepted options are:
			```
			[None, "None", "Zero", "Clic", "Nlc", "Atl", 
			"AtlZero", "Atl2", "AtlZero2, "Earth"]
			```
			
			- If survey is `None` (**default**) - uses the current beamline alignment from 
			`self.beamline`.
			- The rest value are Placet built-in surveys. After it is used, the alignment
			in `self.beamline` is going to be updated with new values generated by a survey.
		
		Other arguments accepted are inherited from 
		[`Placet.TestSimpleCorrection()`][placetmachine.placet.placetwrap.Placet.TestSimpleCorrection],
		except of `machines`, `survey`, and `beam`.

		Returns
		-------
		DataFrame
			The tracking summary after the correction.

			The columns of the resulting DataFrame:
			```
			['correction', 'beam', 'beamline', 'survey', 'positions_file', 'emittx', 'emitty']
			```
		"""
		return self.placet.TestSimpleCorrection(**dict(extra_params, beam = beam.name, machines = 1, survey = survey, timeout = 100))

	@term_logging
	@add_beamline_to_final_dataframe
	@update_misalignments
	@verify_survey
	@verify_beam
	def DFS(self, beam: Beam, survey: Optional[str] = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the Dispersion Free Steering or DFS.
		
		Before actually invoking the 
		[`Placet.TestMeasuredCorrection()`][placetmachine.placet.placetwrap.Placet.TestMeasuredCorrection]
		function, runs [`Placet.Zero()`][placetmachine.placet.placetwrap.Placet.Zero].

		If `bpms_realign` is `False` - the reference orbit will not be saved. 
		That means, that any further alignment will typically use BPMs center as 
		the best orbit solution (Eg. Rf alignment). 
		When it is `True`, runs the callback with 'BpmRealign' command. 
		After performing the DFS, sets the callback to `"empty"`.

		The default DFS parameters used:
		```
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
		```

		Parameters
		----------
		beam
			The beam to use.
		survey
			The type of survey to be used. So far the accepted options are:
			```
			[None, "None", "Zero", "Clic", "Nlc", "Atl", 
			"AtlZero", "Atl2", "AtlZero2, "Earth"]
			```
			
			- If survey is `None` (**default**) - uses the current beamline alignment from 
			`self.beamline`.
			- The rest value are Placet built-in surveys. After it is used, the alignment
			in `self.beamline` is going to be updated with new values generated by a survey.

		Other parameters
		----------------
		bpms_realign : bool
			If `True` (default is `True`), updates the reference orbit (bpm reading) by 
			invoking a new callback procedure with `BpmRealign` in it.

		Other arguments accepted are inherited from 
		[`Placet.TestMeasuredCorrection()`][placetmachine.placet.placetwrap.Placet.TestMeasuredCorrection],
		except of `machines`, `survey`, and `beam`.

		Returns
		-------
		DataFrame
			The tracking summary.

			The comlumns of the resulting DataFrame:
			```
			['correction', 'beam', 'beamline', 'survey', 'positions_file', 'emittx', 'emitty']
			```
		"""
		dfs_default_options = {
			'beam0': beam.name,
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
	def _RF_align(self, beam: Beam, survey: str = None, **extra_params):
		self.placet.TestRfAlignment(**dict(extra_params, beam = beam.name, survey = survey, machines = 1))

	@term_logging
	@verify_survey
	@verify_beam
	def RF_align(self, beam: Beam, survey: Optional[str] = None, **extra_params) -> pd.DataFrame:
		"""
		Perform the accelerating structures alignment (RF alignment).

		Does the correction with 
		[`Placet.TestRfAlignment()`][placetmachine.placet.placetwrap.Placet.TestRfAlignment]. 
		After, runs [`Machine.track()`][placetmachine.machine.Machine.track] to evaluate the emittances.

		Parameters
		----------
		beam
			The beam to use.
		survey
			The type of survey to be used. So far the accepted options are:
			```
			[None, "None", "Zero", "Clic", "Nlc", "Atl", 
			"AtlZero", "Atl2", "AtlZero2, "Earth"]
			```
			
			- If survey is `None` (**default**) - uses the current beamline alignment from 
			`self.beamline`.
			- The rest value are Placet built-in surveys. After it is used, the alignment
			in `self.beamline` is going to be updated with new values generated by a survey.
		
		Other arguments accepted are inherited from 
		[`Placet.TestRfAlignment()`][placetmachine.placet.placetwrap.Placet.TestRfAlignment],
		except of `machines`, `survey`, and `beam`.

		Returns
		-------
		DataFrame
			The tracking summary

			The comlumns of the resulting DataFrame:
			```
			['correction', 'errors_seed', 'beam_seed', 'survey', 'positions_file', 
			'emittx', 'emitty']
			```
		"""
		self.placet.Zero()
		self._RF_align(beam, survey, **extra_params)
		track_results = self._track(beam)
		track_results.correction = "RF align"
		return track_results

	def apply_knob(self, knob: Knob, amplitude: float):
		"""
		Apply the knob and update the beamline offsets.

		It is generaly safer to use this function instead of individual 
		[`Knob.apply()`][placetmachine.lattice.knob.Knob.apply]. 
		Here, the checks are performed to ensure that all the elements involved 
		in `knob` exist in `self.beamline`.

		Parameters
		----------
		knob
			The knob to use.
		amplitude
			Amplitude to apply.
		"""
		if knob not in self.beamline.adjusted_knobs:
			raise ValueError("The knob provided does not exist!")
		knob.apply(amplitude)

	@verify_beam
	def eval_track_results(self, beam: Beam, **extra_params) -> (pd.DataFrame, float, float):
		"""
		Evaluate the beam parameters at the beamline exit.
		
		At the beginning of the run, if the calculation requires performing the tracking,
		sets the callback. Depending on the beam type, the different callback is defined. 
		For sliced beam it is 
		[`Machine.save_sliced_beam()`][placetmachine.machine.Machine.save_sliced_beam].
		For particle beam it is 
		[`Machine.save_beam()`][placetmachine.machine.Machine.save_beam].

		The structure of the data in the files for the sliced beam:
		```
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
		```

		The structure of the data in the files for the particle beam:
		```
		1. energy [GeV]
		2. x [um]
		3. y [um]
		4. z [um]
		5. x' [urad]
		6. y' [urad]
		```

		Parameters
		----------
		beam
			The beam to use.

		Other parameters
		----------------
		keep_callback : bool
			If `True` (default is `False`), does not change the callback function 
			at the end of the run.
		
		Returns
		-------
		tuple(DataFrame, float, float)
			Returns the DataFrame with the particles' coordinates at the beamline exit 
			and final horizontal and vertical emittance.
			
			The columns of the DataFrame includes are:
			
			- For sliced beam:
			```
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 
			'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 
			'sigma_xpy', 'sigma_yx', 'sigma_ypx']
			```
			- For particle beam:
			```
			['E', 'x', 'y', 'z', 'px', 'py']
			```

		"""
		beam_type = beam.beam_type
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
		track_res = self.track(beam)
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

	def eval_obs(self, beam: Beam, observables: List[str], **extra_params) -> List[float]:
		"""
		Evaluate the requested observables for the current state of `self.beamline`.

		The observalbles could be the following:
		
		- For particle beam:
		```
		['E', 'x', 'y', 'z', 'px', 'py']
		```
		- For macroparticle beam:
		```
		['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 
		'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 
		'sigma_xpy', 'sigma_yx', 'sigma_ypx']
		```
		Also, emittance `['emittx', 'emitty']` is evaluted in each case.
		
		The units for the coordinates are:
		- `E`: GeV
		- `s(z)`, `x`, `y`, `z`: micrometer
		- `px`, `py`: microrad,
		- `emittx`, `emitty`: nm

		Parameters
		----------
		beam
			The beam to use.
		observables
			The variables to read from the tracking data when performing the scan.
			It can consist of:
			```
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 
			'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 
			'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
			```
		
		Other parameters
		----------------
		suppress_output : bool
			If `True` (default is `False`) suppresses the log message in regards of the tracking.
		
		Returns
		-------
		List[float]
			The values of the observables.
		"""
		obs = []
		if set(observables).issubset(set(['emittx', 'emitty'])):
			#using the results of machine.track 
			track_results = self.track(beam) if not extra_params.get('suppress_output', False) else self._track(beam)
			obs = [float(track_results[observable].values) for observable in observables]
		else:
			#running machine.eval_track_results to identify the coordinates etc.
			track_res, emittx, emitty = self.eval_track_results(beam)
			for observable in observables:
				if observable in ['emittx', 'emitty']:
					obs.append(emitty if observable == 'emitty' else emittx)
				else:
					obs.append(list(track_res[observable].values))
		
		return obs

	def iterate_knob(self, beam: Beam, knob: Knob, observables: List[str], knob_range: List[float] = [-1.0, 0.0, 1.0], **extra_params) -> dict:
		"""
		Iterate the given knob in the given range and get the iteration summary.
		
		Parameters
		----------
		beam
			The name of the beam to be used.
		knob
			The knob to perform scan on.
		observables
			The variables to read from the tracking data when performing the scan.
			It can consist of:
			```
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 
			'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 
			'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
			```
		knob_range
			The list of the knob values to perform the scan.

		Other parameters
		----------------
		fit : Callable
			Function to fit the data.
			**!!** Only works if the amound of observables is equaly **1**.
		plot : Callable
			Function to plot the iteration data.
			**!!** Only works if the amound of observables is equaly **1**.

		Returns
		------
		dict
			The scan summary.
		"""
		_obs_values = ['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 
					   'sigma_xy', 'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
		if not set(observables).issubset(set(_obs_values)):
			raise ValueError(f"The observables(s) '{observables}' are not supported")

		observable_values = []
		
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

			obs = self.eval_obs(beam, observables, suppress_output = True)
			
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

	@within_range
	def scan_knob(self, beam: Beam, knob: Knob, observable: str, knob_range: List[float], fit_func: Callable, **extra_params) -> pd.DataFrame:
		"""
		Scan the given knob in the given range, apply the fit function and set the 
		knob value to the optimum.

		Since, the optimal value is set only in `self.beamline`, in case one needs to update
		these values in Placet immediatly, one has to call
		`Machine._update_lattice_misalignments()`
		
		Parameters
		----------
		beam
			The beam used for the scan.
		knob
			The knob to perform scan on.
		knob_range
			The list of the knob values to perform the scan.
		observable
			The variables to read from the tracking data and use it for identifying
			the optimum in the scan. It can be one of:
			```
			['s', 'weight', 'E', 'x', 'px', 'y', 'py', 'sigma_xx', 'sigma_xpx', 
			'sigma_pxpx', 'sigma_yy', 'sigma_ypy', 'sigma_pypy', 'sigma_xy', 
			'sigma_xpy', 'sigma_yx', 'sigma_ypx', 'emittx', 'emitty']
			```
		fit_func
			The fit function for the data.

		Other parameters
		----------------
		plot : Callable[[List[float], List[float]], None]
			The function to plot the knob iteration of the format f(x, y).
		evaluate_optimal : bool
			If `True` (default is `True`) reevaluates the emittance by running `track()`
			function.

		Returns
		-------
		DataFrame
			The scan summary. The columns of the output table are:
			```
			['correction', 'positions_file', 'emittx', 'emitty', 'knob_value', 'scan_log']
			```
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

	def apply_quads_errors(self, strength_error: float = 0.0):
		"""
		Add the relative strength errors to all the 
		[`Quadrupole`][placetmachine.lattice.quadrupole.Quadrupole]s in
		`self.beamline`.

		Parameters
		----------
		strength_error
			Standard relative deviation of the quadrupole strength.
		"""
		for quad in self.beamline.extract(['Quadrupole']):
			quad.settings['strength'] += quad.settings['strength'] * random.gauss(0, strength_error)

		self._update_quads_strengths()	

	def apply_cavs_errors(self, phase_error: float = 0.0, grad_error: float = 0.0):
		"""
		Add the errors to the cavities' phases and gradients.

		Parameters
		----------
		phase_error
			Standard deviation of the phase (Absolue value).
		grad_error
			Standard deviation of the gradient (Absolue value).
		"""
		for cav in self.beamline.extract(['Cavity']):
			cav.settings['phase'] += random.gauss(0, phase_error)
			cav.settings['gradient'] += random.gauss(0, grad_error)

		self._update_cavs_phases()
		self._update_cavs_gradients()

	def misalign_element(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element with the given ID.

		Duplicates 
		[`Beamline.misalign_element()`][placetmachine.lattice.lattice.Beamline.misalign_element].
		
		Other parameters
		----------------
		element_index : int
			The id of the element in the lattice. **Required**
		x : float
			The horizontal offset in micrometers. Default is `0.0`.
		xp : float
			The horizontal angle in micrometers/m. Default is `0.0`.
		y : float
			The vertical offset in micrometers. Default is `0.0`.
		yp : float
			The vertical angle in micrometers/m. Default is `0.0`.
		roll : float
			The roll angle in microrad. Default is `0.0`.
		"""
		self.beamline.misalign_element(**extra_params)

	def misalign_elements(self, **extra_params):
		"""
		Apply the geometrical misalignments to the elements in the dictionary

		Other parameters
		----------------
		offsets_data : dict
			**[Required]** The dictionary with the elements offsets 
			in the following format:
			```
				{
					'element_id1': {
						'x': ..
						'y': ..
						..
					}
					'element_id2': {
						..
					}
					..
				}
			```
		"""
		self.beamline.misalign_elements(**extra_params)

	def misalign_articulation_point(self, **extra_params):
		"""
		Offset the articulation point either between 2 girders or at the beamline start/end.

		The girders and elements on them are misalligned accordingly (wrt the geometry of the girder).

		There is an option to provide the ids of the girders to the right and to the left of the articulation point. That 
		require `girder_right` - `girder_left` to be equal 1, otherwise an exception will be raised.

		It is possible to provide only 1 id either of the right or the left one. This also works for the start/end of the beamline.

		Other parameters
		----------------
		girder_left : Optional[int]
			The ID of the girder to the left of the articulation point.
		girder_right : Optional[int]
			The ID of the girder to the right of the articulation point.
		x : float
			The horizontal offset in micrometers. Default is `0.0`.
		y : float
			The vertical offset in micrometers. Default is `0.0`.
		filter_types : Optional[List[str]]
			The types of elements to apply the misalignments to.
			By default, the misalignments are applied to all the elements on the girder.
		"""
		self.beamline.misalign_articulation_point(**extra_params)
	
	def misalign_girder_general(self, **extra_params):
		"""
		Misalign the girder by means of moving its end points.
		
		Other parameters
		----------------
		girder : int
			**[Required]** The id of the girder.
		x_right : float
			The horizontal offset in micrometers of right end-point. Default is `0.0`.
		y_right : float
			The vertical offset in micrometers of the right end-point. Default is `0.0`.
		x_left : float
			The horizontal offset in micrometers of left end-point. Default is `0.0`.
		y_left : float
			The vertical offset in micrometers of the left end-point. Default is `0.0`.
		filter_types : Optional[List[str]]
			The types of elements to apply the misalignments to.
			By default, the misalignments are applied to all the elements on the girder.
		"""
		self.beamline.misalign_girder_general(**extra_params)
	
	def misalign_girder(self, **extra_params):
		"""
		Offset the girder transversaly together with the elements on it.

		All the elements on the girder are equally misaligned.

		Other parameters
		----------------
		girder : int
			The girder ID.
		filter_types : Optional[List(str)]
			The types of elements to apply the misalignments to.
			By default, the misalignments are applied to all the elements on the girder.
		x : float
			The horizontal offset in micrometers.
		y : float
			The vertical offset in micrometers.
		"""
		self.beamline.misalign_girder(**extra_params)

	def misalign_girders(self, **extra_params):
		"""
		Misalign the girders according to the dictionary.

		Other parameters
		----------------
		offsets_data : dict
			The dictionary with the girders offsets in the following format:
			```
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
			```
		filter_types : Optional[List[str]]
			The types of elements to apply the misalignments to.
			By default, the misalignments are applied to all the elements on the girder.
		"""
		self.beamline.misalign_girders(**extra_params)

	def from_file(self, **extra_params):
		"""
		Apply the survey that uses the misalignments from the file.
	
		Other parameters
		----------------
		file : str
			The name of the file with the misalignments.
		additional_lineskip : int
			Can only take the value of `0`. If not given, the default values for the commands are used.
		"""
		if not 'file' in extra_params:
			raise Exception("'file' is not given")

		if extra_params.get('additional_lineskip', 0) != 0:
			raise ValueError("additional_lineskip given to survey-function can only be 0")
		
		self.placet.ReadAllPositions(**extra_params)

	def default_clic(self, **extra_params):
		"""
		Apply the default Clic survey to a lattice.
		
		The function calls `Clic` func in Placet. It requires the 
		lattice misalignments to be already declared with either with
		[`Machine.survey_errors_set()`][placetmachine.machine.Machine.survey_errors_set] (preferred)
		or with 
		[`self.placet.SurveyErrorSet()`][placetmachine.placet.placetwrap.Placet.SurveyErrorSet].

		**Can be used inside of a `proc` in Placet.**

		Other parameters
		---------------------
		additional_lineskip : int
			Can only take the value of '0' (default). If not given, the default values for the commands are used

		Other keyword arguments accepted are parameters of the
		[`self.placet.InterGirderMove()`][placetmachine.placet.placetwrap.Placet.InterGirderMove]
		function, which is invoked within `default_clic`.
		"""
		if extra_params.get('additional_lineskip', 0) != 0:
			raise Exception("additional_lineskip given to survey-function can only be 0")

		self.placet.Clic(**extra_params)
		self.placet.InterGirderMove(**extra_params)

	def empty(self, **extra_params):
		"""
		Apply the empty survey function.
		
		Corresponds to using `'None'` survey in Placet.

		**Can be used inside of a `proc` in Placet.**
		"""
		pass
	
	def save_beam(self, **extra_params):
		"""
		Save the particle beam.

		**Can be used inside of a `proc` in Placet.**

		Other keyword arguments accepted are parameters of the
		[`self.placet.BeamDump()`][placetmachine.placet.placetwrap.Placet.BeamDump]
		function, which is invoked within `save_beam`.
		"""
		self.placet.BeamDump(**extra_params)

	def save_sliced_beam(self, **extra_params):
		"""
		Save the sliced beam.

		Other keyword arguments accepted are parameters of the
		[`self.placet.BeamSaveAll()`][placetmachine.placet.placetwrap.Placet.BeamSaveAll]
		function, which is invoked within `save_sliced_beam`.
		"""
		self.placet.BeamSaveAll(**extra_params)

	def phase_advance(self, start_id: int, end_id: int):
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

	def random_reset(self, seed: Optional[int] = None):
		"""
		Reset the random seed in Placet.

		Runs [`Placet.RandomReset()`][placetmachine.placet.placetwrap.Placet.RandomReset].
		"""
		self.placet.RandomReset(seed = seed if seed is not None else random.randint(1, 1000000))
