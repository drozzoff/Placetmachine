from .pyplacet import Placetpy, PlacetCommand

import pandas as pd
from functools import wraps
from time import sleep, time
import numpy as np

_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

def _generate_command(command_name, param_list, **command_details) -> str:
	"""
	Generate the command for Placet.

	Parameters
	----------
	command_name: str
		The name of the command
	param_list: list
		The list of the parameters that
	"""
	assert isinstance(command_name, str), "command_name should be of 'str' type, received - " + str(type(command_name))
	assert isinstance(param_list, list), "param_list should be of 'list' type, received - " + str(type(param_list))
	
	res = command_name
	for key in _extract_subset(param_list, command_details):
		res += " -" + key + " " + str(command_details[key])
	
	if command_details.get('no_nextline', False):
		return res
	
	res += "\n"
	return res

class Placet(Placetpy):
	"""
	A class used to wrap the Placet commands in a usable format

	Extends Placetpy to provide the usable interface for Python to use Placet commands
	
	Methods have correspondant commands in Placet

	.......

	Methods/PLACET commands ([23/11/2022] - 49 in Total)
	-------
	TwissPlotStep(**command_details)
	FirstOrder(**command_details)
	set(variable, value, **command_details)	
	puts(variable, **command_details)
	source(filename, **command_details)
	TestNoCorrection(**command_details)
	TestSimpleCorrection(**command_details)
	TestFreeCorrection(**command_details)
	TestMeasuredCorrection(**command_details)
	TestRfAlignment(**command_details)
	BeamlineNew(**command_details)
	BeamlineSet(**command_details)
	QuadrupoleNumberList(**command_details)
	CavityNumberList(**command_details)
	BpmNumberList(**command_details)
	DipoleNumberList(**command_details)
	MultipoleNumberList(**command_details)
	CollimatorNumberList(**command_details)
	CavityGetPhaseList(**command_details)
	QuadrupoleGetStrength(quad_number, **command_details)
	QuadrupoleSetStrength(quad_number, value, **command_details)
	QuadrupoleSetStrengthList(values_list, **command_details)
	CavitySetGradientList(values_list, **command_details)
	CavitySetPhaseList(values_list, **command_details)
	ElementGetAttribute(element_id, parameter, **command_details)
	ElementSetAttributes(element_id, **command_details)
	WriteGirderLength(**command_details)
	SurveyErrorSet(**command_details)
	Clic(**command_details)
	Zero(**command_details)
	SaveAllPositions(**command_details)
	ReadAllPositions(**command_details)
	InterGirderMove(**command_details)
	RandomReset(**command_details)
	InjectorBeam(beam_name, **command_details)
	SetRfGradientSingle(beam_name, var1, l)
	BeamRead(**command_details)
	BeamSaveAll(**command_details)
	BeamDump(**command_details)
	TclCall(**command_details)
	TwissMain(**command_details)
	GetTransferMatrix(**command_details)
	BeamSetToOffset(**command_details)
	ElementSetToOffset(index, **command_details)
	ElementAddOffset(index, **command_details)
	BpmReadings(**command_details)
	MoveGirder(**command_details)
	BpmRealign(**command_details)
	
	Methods
	-------
	get_element_transverse_matrix(index, **command_details)
		Returns the Tranfer matrix of an element with a given index
	wake_calc(filename, charge, a, b, sigma_z, n_slices, **command_details)
		..
	declare_proc(proc, **command_details)
		Declare a custom procedure in Placet TCL

	"""
	def __init__(self, **Placetpy_params):
		"""

		"""
		super(Placet, self).__init__("placet", **Placetpy_params)

	_exec_params = PlacetCommand.optional_parameters

	survey_erorrs = ['quadrupole_x', 'quadrupole_y', 'quadrupole_xp', 'quadrupole_yp', 'quadrupole_roll', 'cavity_x', 'cavity_realign_x', 'cavity_y', 'cavity_realign_y', 
		'cavity_xp', 'cavity_yp', 'cavity_dipole_x', 'cavity_dipole_y', 'piece_x', 'piece_xp', 'piece_y', 'piece_yp', 'bpm_x', 'bpm_y', 'bpm_xp', 'bpm_yp', 'bpm_roll',
		'sbend_x', 'sbend_y', 'sbend_xp', 'sbend_yp', 'sbend_roll']

	def __repr__(self):
		return f"Placet(debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay}, show_intro = {self._show_intro})"

	def __str__(self):
		return f"Placet(is_alive = {self.isalive()})"

	def logging(func):

		@wraps(func)
		def wrapper(self, *args, **kwargs):
			start = time()
			res = func(self, *args, **kwargs)
			run_time = time() - start
			if self.debug_mode:
				self.debug_data = self.debug_data.append(dict(function = func.__name__, run_time = run_time, res = res), ignore_index = True)
				print(func.__name__, run_time, res)
			return res
		return wrapper


	def __construct_command(self, command, command_params, **command_details):
		"""
		Generic function for creating a PlacetCommand
		
		1)The Placet command is constructed and the command parameters are extracted from command_details
		2)The computing/parsing details of the command are extracted from command_details, based on the Placet._exec_params

		Parameters
		----------
		command: string
			Command name.
		command_params: list(string)
			The full list of the arguments the corresponding command in the Placet TCL can take.

		Additional parameters
		---------------------
		/**/ Could be any including the computational parameters inherited from PlacetCommand.optional_parameters.
			Each function filters those it can accept, the list is usually stored as _options_list. /**/

		"""
		return PlacetCommand(_generate_command(command, command_params, **command_details), **dict(_extract_dict(self._exec_params, command_details), type = command.split()[0]))

	def __set_puts_command(self, command, command_params, **command_details):
		"""
		Generic function for executing the following chain of commands:
			set tmp [command param1 param2 ..]
			puts $tmp

		The data retrieved from puts is returned

		Parameters
		----------
		command: string
			Command name.
		command_params: list(string)
			The full list of the arguments the corresponding command in the Placet TCL can take.

		Additional parameters
		---------------------
		/**/ Could be any including the computational parameters inherited from PlacetCommand.optional_parameters.
			Each function filters those it can accept, the list is usually stored as _options_list. /**/

		"""
		self.set("tmp", "[" + _generate_command(command, command_params, **dict(command_details, no_nextline = True)) + "]")
		return self.puts("tmp")

	def execution_comfirmation(func):
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			res = func(self, *args, **kwargs)
			self.set("finished", 1, **kwargs)
			return res

		return wrapper

	def _BeamlineInfo(self, **command_details):
		'''
			Corresponds to "BeamlineInfo" command in Placet TCL executed in the form:
			array set tmp [BeamlineInfo]
			puts $tmp(n_cavity)
			puts $tmp(n_quadrupole)
			..

		???
		'''

		pass

	def TwissPlotStep(self, **command_details):
		"""
		Run "TwissPlotStep" command in Placet TCL
		
		The output file is composed of:
		1.) Element number 
		2.) s: [m] Distance in the beam line: s 
		3.) E(s): energy [GeV] ( central slice or average energy for particle beam) 
		4.) beta_x_m(s) [m] (of central slice ) 
		5.) alpha_x_m(s) [m] (of central slice ) 
		6.) beta_x_i(s) [m] (of average over slices) 
		7.) alpha_x_i(s) [m] (of average over slices) 
		8.) beta_y_m(s) [m] (of central slice ) 
		9.) alpha_y_m(s) [m] (of central slice ) 
		10.) beta_y_i(s) [m] (of average over slices) 
		11.) alpha_y_i(s) [m] (of average over slices) 
		12.) disp_x(s) [m/GeV] (of average over slices) 
		13.) disp_xp(s) [rad/GeV] (of average over slices) 
		14.) disp_y(s) [m/GeV] (of average over slices) 
		15.) disp_yp(s) [rad/GeV] (of average over slices) 
		
		.....

		Parameters
		----------
		beam: str
			Name of the beam to use for the calculation
		file: str
			Name of the file where to store the results
		step: float
			Step size to be taken for the calculation. If less than 0 the parameters will be plotted only in the centres of the quadrupoles
		start: int (?)
			First particle for twiss computation
		end: int (?)
			Last particle for twiss computation
		list: list
			Save the twiss parameters only at the selected elements			
		"""
		_options_list = ['file', 'beam', 'step', 'start', 'end', 'list']

		assert 'file' in command_details, "Filename is not specified"

		self.run_command(self.__construct_command("TwissPlotStep", _options_list, **command_details))

	def FirstOrder(self, **command_details):
		"""Run "FirstOrder" command in Placet TCL"""
		self.run_command(self.__construct_command("FirstOrder 1", [], **command_details))

	def set(self, variable, value, **command_details):
		"""
		Run 'set' command in TCL

		Parameters
		----------
		variable: str
			Variable to to be set
		value: float
			The value the variable to be set to
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		value
		"""
		assert isinstance(variable, str), "variable should be of 'str' type, received - " + str(type(variable))

		self.run_command(self.__construct_command("set " + variable + " " + str(value), [], **command_details))
		return value

	def set_list(self, name, **command_details):
		'''
			Declares the dictionary in Placet TCL with the name 'name'

			//**//[20/11/2022] Check if needed //**//
		'''
		for key in command_details:
			self.set(name + "(" + key + ")", command_details[key])

	def puts(self, variable, **command_details) -> str:
		"""
		Run the 'puts' command in TCL
		
		Parameters
		----------
		variable: str
			Variable to evaluate
	
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		str
			The Placet return value
		"""
		assert isinstance(variable, str), "variable should be of 'str' type, received - " + str(type(variable))

		self.run_command(self.__construct_command("puts $" + variable, [], **command_details))

		if command_details.get('no_read', False):
			return None

		#in case the output is one line	
		if 'timeout' in command_details:
			return self.readline(command_details.get('timeout'))
		else:
			return self.readline() 

	def source(self, filename, **command_details):
		"""
		Run the 'source' command in TCL

		Parameters
		----------
		filename: str
			Name of the file to read

		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		assert isinstance(filename, str), "filename should be of 'str' type, received - " + str(type(filename))

		self.run_command(self.__construct_command("source " + filename, [], **command_details))

	def make_beam_many(self, beam, nslice, n, **command_details):
		'''
			Correponds to 'make_beam_many' custom command in Placet TCL
			Input:
				name nslice n
			values can be given directly or reference the existing variables in TCL

			!! outdated
		'''
		assert isinstance(beam, str), "beam should be of 'str' type, received - " + str(type(beam))
		assert isinstance(nslice, str) or isinstance(nslice, int), "nslice should be of 'str' or 'int' type, received - " + str(type(nslice))
		assert isinstance(n, str) or isinstance(n, int), "n should be of 'str' or 'int' type, received - " + str(type(n))

		self.run_command(self.__construct_command("make_beam_many " + beam + " " + str(nslice) + " " + str(n), [], **command_details))	

#	@logging
	def TestNoCorrection(self, **command_details) -> pd.DataFrame:
		"""
		Run the 'TestNoCorrection' command in Placet TCL
		
		The default time to executing each command in the chain here is 20s

		/**/The descriptions taken from the Placet Manual/**/

		Additional parameters
		---------------------
		machines: int
			Number of machines to simulate
		beam: str
			Name of the beam to be used for tracking
		survey: str
			Type of prealignment survey to be used
		emitt_file: str
			Filename for the results defaults to NULL (no output)
		bpm_res: float
			BPM resolution
		format: float
			Format of the file output

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		DataFrame
			The tracking results after running TestNoCorrection

			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']

			The number of rows correspond to the number of the machines simulated

		"""
		assert 'beam' in command_details, "beam is not given"
		
		_options_list, _extra_time = ['machines', 'beam', 'survey', 'emitt_file', 'bpm_res', 'format'], 20.0

		self.run_command(self.__construct_command("TestNoCorrection", _options_list, **command_details))
		data_log = pd.DataFrame(columns = ['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty'])

		#Since execution of TestNoCorrection takes time, we increase the default timeout
		timeout = command_details.get('timeout', _extra_time)

		for i in range(command_details.get('machines', 1)):
			if i > 0: self.skipline(timeout)	#	iteration i
			emittx_tmp = float(self.readline(timeout).split()[-1])
			if i > 0: self.skipline(timeout)	#	mean values and errors
			emitty_tmp = float(self.readline(timeout).split()[-1])
			if i > 0: self.skipline(timeout)	#	mean values and errors
			track_tmp = pd.DataFrame({
				'correction': "No",
#				'errors_seed': self.errors_seed if hasattr(self, 'errors_seed') else None, 
				'beam': command_details.get('beam'), 
				'survey': command_details.get('survey', None), 
				'positions_file': command_details.get("errors_file", None), 
				'emittx': emittx_tmp, 
				'emitty': emitty_tmp}, index = [i])
			data_log = pd.concat([data_log, track_tmp])
		return data_log

#	@logging
	def TestSimpleCorrection(self, **command_details) -> pd.DataFrame:
		"""
		Run the 'TestSimpleCorrection' command in Placet TCL
		
		The default time to executing each command in the chain here is 120s

		/**/The descriptions taken from the Placet Manual/**/

		Additional parameters
		---------------------
		beam: str
			Name of the beam to be used for correction
		machines: int, default 1
			Number of machines to simulate
		start: int
			First element to be corrected
		end: int
			Last element but one to be corrected (<0: go to the end)
		interleave: ?
			Used to switch on interleaved bins (correcting only focusing quadrupoles)
		binlength: int
			Number of quadrupoles per bin
		binoverlap: int
			Overlap of bins in no of quadrupoles
		jitter_x: float
			Vertical beam jitter [micro meter]
		jitter_y: float
			Horizontal beam jitter [micro meter]
		bpm_resolution: float
			BPM resolution [micro meter]
		testbeam: str
			Name of the beam to be used for evaluating the corrected beamline
		survey: str
			Type of prealignment survey to be used
		emitt_file: str
			Filename for the results
		bin_last: str
			Filename for the results
		bin_file_out:str
			Filename for the bin information
		bin_file_in:str
			Filename for the bin information
		correctors: list
			List of correctors to be used

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		DataFrame
			The tracking results after running TestSimpleCorrection

			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']

			The number of rows correspond to the number of the machines simulated

		"""
		assert 'beam' in command_details, "beam is not given"
#		assert hasattr(self, 'beam_seed'), "Beam seed is not defined"
#		assert hasattr(self, 'errors_seed'), "Errors seed is not defined"

		_extra_time, _options_list = 120.0, ['machines', 'start', 'end', 'interleave', 'binlength', 'binoverlap', 'jitter_x', 'jitter_y', 'bpm_resolution', 'beam', 'testbeam',
		'survey', 'emitt_file', 'bin_list', 'bin_file_out', 'bin_file_in', 'correctors']

		self.run_command(self.__construct_command("TestSimpleCorrection", _options_list, **command_details))

		data_log = pd.DataFrame(columns = ['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty'])

		timeout = command_details.get('timeout', _extra_time)

		for i in range(command_details.get('machines', 1)):
			
			track_tmp = pd.DataFrame({
				'correction': "1-2-1",
#				'errors_seed': self.errors_seed if hasattr(self, 'errors_seed') else None, 
				'beam': command_details.get('beam'), 
				'survey': command_details.get('survey', None),
				'positions_file': command_details.get("errors_file", None), 
				'emittx': None, 
				'emitty': float(self.readline(timeout).split()[-3])
			}, index = [i])
			data_log = pd.concat([data_log, track_tmp])
		self.skipline()	#sum of the simulations over several machines
		return data_log

	def TestFreeCorrection(self, **command_details) -> pd.DataFrame:
		'''
			Corresponds to 'TestFreeCorrection' command in Placet TCL

			The full list of the command parameters:
			machines				- Number of machines to simulate
			binlength				- Number of quadrupoles per bin
			binoverlap				- Overlap of bins in no of quadrupoles
			jitter_y				- Vertical beam jitter
			jitter_x				- Horizontal beam jitter
			bpm_resolution			- BPM resolution
			rf_align				- Align the RF after the correction?
			beam					- Name of the beam to be used for correction
			survey					- Type of prealignment survey to be used (default Clic)
			emitt_file				- Filename for the results (default NULL)
			wgt0					- Weight for the BPM position
			wgt1					- Weight for the BPM resolution
			pwgt					- Weight for the old quadrupole position
			quad_set0				- List of quadrupole strengths to be used
			quad_set1				- List of quadrupole strengths to be used
			quad_set2				- List of quadrupole strengths to be used
			load_bins				- File with bin information to be loaded
			save_bins				- File with bin information to be loaded
		
		TO DO
		-----
			Add description

		Not tested
		'''

		_options_list = ['machines', 'binlength', 'binoverlap', 'jitter_y', 'jitter_x', 'bpm_resolution', "rf_align", 'beam', 'survey', 'emitt_file', 'wgt0', 'wgt1', 'pwgt', 
		'quad_set0', 'quad_set1', 'quad_set2', 'load_bins', 'save_bins']

		self.run_command(self.__construct_command("TestFreeCorrection", _options_list, **command_details))
		data_log = pd.DataFrame(columns = ['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty'])
		for i in range(command_details.get('machines', 1)):
			track_tmp = pd.DataFrame({
				'correction': "DFS",
#				'errors_seed': self.errors_seed if hasattr(self, 'errors_seed') else None,
				'beam': command_details.get('beam'),
				'survey': command_details.get('survey', None),
				'positions_file': command_details.get("errors_file", None),
				'emittx': None,
				'emitty': float(self.readline(timeout).split()[-2])}, index = [i])
			data_log = pd.concat([data_log, track_tmp])
		self.skipline()	#sum of the simulations over several machines
		return data_log

	def TestMeasuredCorrection(self, **command_details) -> pd.DataFrame:
		"""
		Run the 'TestMeasuredCorrection' command in Placet TCL
		
		/**/The descriptions taken from the Placet Manual/**/

		Additional parameters
		---------------------		
		machines: int
			Number of machines to simulate
		start: int
			First element to be corrected
		end: int
			Last element but one to be corrected (<0: go to the end)
		binlength: int
			Number of quadrupoles per bin
		correct_full_bin: int
			If not zero the whole bin will be corrected
		binoverlap: int
			Overlap of bins in no of quadrupoles
		jitter_x: float
			Vertical beam jitter [micro meter]
		jitter_y: float
			Horizontal beam jitter [micro meter]
		bpm_resolution: float
			BPM resolution [micro meter]
		rf_align: int(?)
			Align the RF after the correction?
		no_acc: int(?)
			Switch RF off in corrected subsection?
		beam0: str
			Name of the main beam to be used for correction
		beam1: str
			Name of the first help beam to be used for correction
		beam2: str
			Name of the second help beam to be used for correction
		cbeam0: str
			Name of the main beam to be used for correction
		cbeam1: str
			Name of the first help beam to be used for correction
		cbeam2: str
			Name of the second help beam to be used for correction
		gradient1: float
			Gradient for beam1
		gradient2: float
			Gradient for beam2
		survey: str
			Type of prealignment survey to be used defaults to CLIC
		emitt_file: str
			Filename for the results defaults to NULL (no output)
		wgt0: float
			Weight for the BPM position
		wgt1: float
			Weight for the BPM resolution
		wgt2: float
			Second weight for the BPM resolution
		pwgt: float
			Weight for the old position
		quad_set0: list(?)
			List of quadrupole strengths to be used
		quad_set1: list(?)
			List of quadrupole strengths to be used
		quad_set2: list(?)
			List of quadrupole strengths to be used
		load_bins: str
			File with bin information to be loaded
		save_bins: str
			File with bin information to be stored
		gradient_list0: list(?)
			Cavity gradients for beam 0
		gradient_list1: list(?)
			Cavity gradients for beam 1
		gradient_list2: list(?)
			Cavity gradients for beam 2
		bin_iterations: int
			Number of iterations for each bin
		beamline_iterations: int
			Number of iterations for each machine
		correctors: list
			List of correctors to be used
		
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""

		_extra_time, _options_list = 300.0, ['machines', 'start', 'end', 'binlength', 'correct_full_bin', 'binoverlap', 'jitter_x', 'jitter_y', 'bpm_resolution', 'rf_align',
		'no_acc', 'beam0', 'beam1', 'beam2', 'cbeam0', 'cbeam1', 'cbeam2', 'gradient1', 'gradient2', 'survey', 'emitt_file', 'wgt0', 'wgt1', 'wgt2', 'pwgt', 'quad_set0', 
		'quad_set1', 'quad_set2', 'load_bins', 'save_bins', 'gradient_list0', 'gradient_list1', 'gradient_list2', 'bin_iterations', 'beamline_iterations', 'correctors']

		self.run_command(self.__construct_command("TestMeasuredCorrection", _options_list, **command_details))

		data_log = pd.DataFrame(columns = ['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty'])

		timeout = command_details.get('timeout', _extra_time)

		for i in range(command_details.get('machines', 1)):
			track_tmp = pd.DataFrame({
				'correction': "DFS",
#				'errors_seed': self.errors_seed if hasattr(self, 'errors_seed') else None,
				'beam': command_details.get('beam'),
				'survey': command_details.get('survey', None),
				'positions_file': command_details.get("errors_file", None), 
				'emittx': None, 
				'emitty': float(self.readline(timeout).split()[-2])}, index = [i])
			data_log = pd.concat([data_log, track_tmp])
		self.skipline()	#sum of the simulations over several machines
		return data_log

	def TestRfAlignment(self, **command_details) -> None:
		"""
		Run the 'TestRfAlignment' command in Placet TCL.

		//**// Setting the number of the machines to 1 //**//
		
		...........
		The command TestRfAlignment does not produce any output inside Placet.

		Additional parameters
		----------
		beam: str
			Name of the beam to be used for correction
		testbeam: str
			Name of the beam to be used for evaluating the corrected beamline
		machines: int
			Number of machines
		binlength: int
			Length of the correction bins
		wgt0: float
			Weight for the BPM position
		wgt1: float
			Weight for the BPM resolution
		pwgt: float
			Weight for the old position
		girder: int
			Girder alignment model: 
			0 - none; 1 - per girder; 2 - per bin
		bpm_resolution: float
			BPM resolution [micro meter]
		survey: str
			Type of prealignment survey to be used
		emitt_file: str
			Filename for the results defaults to NULL (no output)
		
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		DataFrame
			Correction summary
		"""
		_extra_time, _options_list = 120, ['beam', 'testbeam', 'machines', 'binlength', 'wgt0', 'wgt1', 'pwgt', 'girder', 'bpm_resolution', 'survey', 'emitt_file']
		self.run_command(self.__construct_command("TestRfAlignment", _options_list, **command_details))

		return None

	def BeamlineNew(self, **command_details):
		"""
		Run 'BeamlineNew' command in Placet TCL
			
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		self.run_command(self.__construct_command("BeamlineNew", [], **command_details))

	def BeamlineSet(self, **command_details):
		"""
		Run	'BeamlineSet' command in Placet TCL

		Fixes the beamline. This command is used to do some initial calculations. It must be called once but only once in a run.
		//**//Description taken from Placet manual//*//
		
		Additional parameters
		---------------------
		name: str
			Name of the beamline to create
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		"""
		assert 'name' in command_details, "'name' is not given"

		self.run_command(self.__construct_command("BeamlineSet", ['name'], **command_details))
		return command_details.get('name')

	def QuadrupoleNumberList(self, **command_details) -> list:
		"""
		Run the 'QuadrupoleNumberList' command in Placet TCL in the following format:
			% set tmp [QuadrupoleNumberList]
			% puts $tmp

		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the quadrupoles IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("QuadrupoleNumberList", [], **command_details).split()))

	def CavityNumberList(self, **command_details) -> list:
		"""
		Run the 'CavityNumberList' command in Placet TCL in the following format:
			% set tmp [CavityNumberList]
			% puts $tmp
		
		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the cavities IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CavityNumberList", [], **command_details).split()))

	def BpmNumberList(self, **command_details) -> list:
		"""
		Run the 'BpmNumberList' command in Placet TCL in the following format:
			% set tmp [BpmNumberList]
			% puts $tmp
		
		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the BPMs IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("BpmNumberList", [], **command_details).split()))

	def DipoleNumberList(self, **command_details) -> list:
		"""
		Run the 'DipoleNumberList' command in Placet TCL in the following format:
			% set tmp [DipoleNumberList]
			% puts $tmp
		
		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the dipoles IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("DipoleNumberList", [], **command_details).split()))

	def MultipoleNumberList(self, **command_details) -> list:
		"""
		Run the 'MultipoleNumberList' command in Placet TCL in the following format:
			% set tmp [MultipoleNumberList -orded order]
			% puts $tmp
		
		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		order: int
			Order of the multipoles.
		
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the multipoles IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("MultipoleNumberList", ['order'], **command_details).split()))

	def CollimatorNumberList(self, **command_details) -> list:
		"""
		Run the 'CollimatorNumberList' command in Placet TCL in the following format:
			% set tmp [CollimatorNumberList]
			% puts $tmp
		
		//**// Alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the colimators IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CollimatorNumberList", [], **command_details).split()))

	def CavityGetPhaseList(self, **command_details) -> list:
		"""
		Run the 'CavityGetPhaseList' command in Placet TCL in the following format:
			% set tmp [CavityGetPhaseList]
			% puts $tmp
		
		//**// The better alternative is the use of PlacetLattice //**//
		
		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command

		Returns
		-------
		list
			The list with the dipoles IDs
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CavityGetPhaseList", [], **command_details)))

	def QuadrupoleGetStrength(self, quad_number, **command_details):
		'''
			Corresponds to 'QuadrupoleGetStrength' command in Placet TCL executed in the form:
				set tmp [QuadrupoleGetStrength quad_number]
				puts $tmp

		!! To be updated
		'''
		return list(map(lambda x: float(x), self.__set_puts_command("QuadrupoleGetStrength " + str(quad_number), [], **command_details).split()))

	def QuadrupoleSetStrength(self, quad_number, value):
		'''
			Corresponds to 'QuadrupoleSetStrength' command in Placet TCL executed in the form:

			//**// Update the method + description //**//
		'''
		self.run_command(PlacetCommand("QuadrupoleSetStrength " + str(quad_number) + " " + str(value) + "\n"))

	def QuadrupoleSetStrengthList(self, values_list, **command_details):
		"""
		Run the 'QuadrupoleSetStrengthList' in Placet TCL
		It sets the strengths of the quadrupoles according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet would throw an error
		
		Parameters
		----------
		values_list: list
			The list with the quadrupoles strengths

		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		self.run_command(self.__construct_command("QuadrupoleSetStrengthList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def CavitySetGradientList(self, values_list, **command_details):
		"""
		Run the 'CavitySetGradientList' command in Placet TCL.
		It sets the gradients of the cavities according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet would throw an error
		.....

		Parameters
		----------
		values_list: list(float)
			The list with cavities gradients

		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		self.run_command(self.__construct_command("CavitySetGradientList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def CavitySetPhaseList(self, values_list, **command_details):
		"""
		Run the 'CavitySetPhaseList' command in Placet TCL.
		It sets the phases of the cavities according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet would throw an error
		.....

		Parameters
		----------
		values_list: list(float)
			The list with cavities gradients

		Additional parameters
		---------------------
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		self.run_command(self.__construct_command("CavitySetPhaseList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def ElementGetAttribute(self, element_id, parameter, **command_details) -> float:
		'''
			Corresponds to 'ElementGetAttribute' command in Placet TCL
		'''
		assert isinstance(element_id, int), "element_id should be of 'int' type, received - " + str(type(element_id))
		assert isinstance(parameter, str), "parameter should be of 'str' type, received - " + str(type(parameter))

		self.run_command(self.__construct_command("ElementGetAttribute " + str(element_id) + " -" + parameter, []))
		return float(self.readline().split()[-1])

	def ElementSetAttributes(self, element_id, **command_details):
		'''
			Corresponds to 'ElementSetAttributes' command in Placet TCL

			parameters is a dictionary

			//**// Needs to be updated //**//
		'''
		assert isinstance(element_id, int), "element_id should be of 'int' type, received - " + str(type(element_id))

		quads_option = ['name', 's', 'x', 'y', 'xp', 'yp', 'roll', 'length', 'synrad', 'six_dim', 'thin_lens', 'e0', 'aperture_x', 'aperture_y', 'aperture_losses', 'aperture_shape',
		'strength', 'tilt', 'hcorrector', 'hcorrector_step_size', 'vcorrector', 'vcorrector_step_size']
		additional_sbend_option = ['angle', 'E1', 'E2', 'K', 'K2']
		additional_bpm_option = ['resolution', 'reading_x', 'reading_y', 'scale_x', 'scale_y', 'store_bunches']
		additional_cavity_option = ['gradient', 'phase', 'type', 'lambda', 'frequency']
		additional_dipole_option = ['strength_x', 'strength_y']
		additional_multipole_option = ['steps']

		_options_list = quads_option + additional_sbend_option + additional_bpm_option + additional_cavity_option + additional_dipole_option + additional_multipole_option

		self.run_command(self.__construct_command("ElementSetAttributes " + str(element_id), _options_list, **command_details))

	def WriteGirderLength(self, **command_details):
		'''
			Corresponds to 'WriteGirderLength' command in Placet TCL

			Only file output is available
		'''
		assert 'file' in command_details, "file is not given"
		
		_options_list = ['file', 'binary', 'beginning_only', 'absolute_position']		

		self.run_command(self.__construct_command("WriteGirderLength", _options_list, **command_details))

	def SurveyErrorSet(self, **command_details):
		"""
		Run 'SurveyErrorSet' command in Placet TCL
			
		When the command is invoked - it simply overwrittes the values already in memory. That means if one calls it with 'cavity_y = 5.0' that means that
		'cavity_y' property will be overwritten, others will be kept unchanged. 
		
		--------
		/**/The descriptions taken from the Placet Manual/**/

		Additional parameters
		---------------------
		quadrupole_x: float
			Horizontal quadrupole position error [micro m]
		quadrupole_y: float
			Vertical quadrupole position error [micro m]
		quadrupole_xp: float
			Horizontal quadrupole angle error [micro radian]
		quadrupole_yp: float
			Vertical quadrupole angle error [micro radian]
		quadrupole_roll: float
			Quadrupole roll around longitudinal axis [micro radian]
		cavity_x: float
			Horizontal structure position error [micro m]
		cavity_realign_x: float
			Horizontal structure position error after realignment [micro m]
		cavity_y: float
			Vertical structure position error [micro m]
		cavity_realign_y: float
			Vertical structure position error after realignment [micro m]
		cavity_xp: float
			Horizontal structure angle error [micro radian]
		cavity_yp: float
			Vertical structure angle error [micro radian]
		cavity_dipole_x: float
			Horizontal dipole kick [rad*GeV]
		cavity_dipole_y: float
			Vertical dipole kick [rad*GeV]
		piece_x: float
			Horizontal structure piece error [micro m]
		piece_xp: float
			Horizontal structure piece angle error [micro radian]
		piece_y: float
			Vertical structure piece error [micro m]
		piece_yp: float
			Vertical structure piece angle error [micro radian]
		bpm_x: float
			Horizontal BPM position error [micro m]
		bpm_y: float
			Vertical BPM position error [micro m]
		bpm_xp: float
			Horizontal BPM angle error [micro radian]
		bpm_yp: float
			Vertical BPM angle error [micro radian]
		bpm_roll: float
			BPM roll around longitudinal axis [micro radian]
		sbend_x: float
			Horizontal sbend position error [micro m]
		sbend_y: float
			Vertical sbend position error [micro m]
		sbend_xp: float
			Horizontal sbend angle error [micro radian]
		sbend_yp: float
			Vertical sbend angle error [micro radian]
		sbend_roll: float
			Sbend roll around longitudinal axis [micro radian]
			
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		_options_list = ['quadrupole_x', 'quadrupole_y', 'quadrupole_xp', 'quadrupole_yp', 'quadrupole_roll', 'cavity_x', 'cavity_realign_x', 'cavity_y', 'cavity_realign_y', 
		'cavity_xp', 'cavity_yp', 'cavity_dipole_x', 'cavity_dipole_y', 'piece_x', 'piece_xp', 'piece_y', 'piece_yp', 'bpm_x', 'bpm_y', 'bpm_xp', 'bpm_yp', 'bpm_roll',
		'sbend_x', 'sbend_y', 'sbend_xp', 'sbend_yp', 'sbend_roll']

		self.run_command(self.__construct_command("SurveyErrorSet", _options_list, **command_details))


	def Clic(self, **command_details):
		'''
			Corresponds to 'Clic' command in Placet TCL
		'''
		_options_list = ['start', 'end']

		self.run_command(self.__construct_command("Clic", _options_list, **command_details))

	def Zero(self, **command_details):
		'''
			Corresponds to 'Zero' command in Placet TCL
		'''
		self.run_command(self.__construct_command("Zero", [], **command_details))

	@execution_comfirmation
	def SaveAllPositions(self, **command_details):
		"""
		Run 'SaveAllPositions' command in Placet TCL

		Additional parameters
		---------------------
		file: str
			Filename to write
		binary: int
			If not 0 save as binary file
		nodrift: int
			If not 0 drift positions will not be saved
		vertical_only: int
			If not 0 only vertical information will be saved
		positions_only: int
			If not 0 only positions will be saved
		cav_bpm: int
			If not 0 positions of structure BPMs will be saved
		cav_grad_phas: int
			If not 0 gradient and phase of structure will be saved

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		assert 'file' in command_details, "file is not given"
		_options_list = ['file', 'binary', 'nodrift', 'vertical_only', 'positions_only', 'cav_bpm', 'cav_grad_phas']
		
		self.run_command(self.__construct_command("SaveAllPositions", _options_list, **command_details))

	def ReadAllPositions(self, **command_details):
		'''
			Corresponds to 'ReadAllPositions' command in Placet TCL
		'''
		assert 'file' in command_details, "file is not given"
		_options_list = ['file', 'binary', 'nodrift', 'nomultipole', 'vertical_only', 'positions_only', 'cav_bpm', 'cav_grad_phas']

		self.run_command(self.__construct_command("ReadAllPositions", _options_list, **command_details))

	def InterGirderMove(self, **command_details):
		"""
		Run the 'InterGirderMove' command in Placet TCL

		It distributes the girders endpoints with respect to the Reference wire -> cavities are also moved accordingly

		......

		Additional parameters
		---------------------
		scatter_x: float
			Sigma of Gaussian scattering in x view of the intersubsections between girders [micrometers]
		scatter_y: float
			Sigma of Gaussian scattering in y view of the intersubsections between girders [micrometers]
		flo_x: float
			Sigma of Gaussian scattering in x view of the girder connection around the intersubsection point [micrometers]
		flo_y: float
			Sigma of Gaussian scattering in y view of the girder connection around the intersubsection point [micrometers]
		cav_only: int
			If not zero move only the cavities on the girder

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		_options_list = ['scatter_x', 'scatter_y', 'flo_x', 'flo_y', 'cav_only']

		self.run_command(self.__construct_command("InterGirderMove", _options_list, **command_details))

	def RandomReset(self, **command_details):
		"""
		Run the 'RandomReset' command in Placet TCL
		
		Resets the errors seed number in Placet

		Additional parameters
		---------------------
		seed: int
			The seed number to set
		"""
		_options_list = ['seed']

		self.run_command(self.__construct_command("RandomReset", _options_list, **command_details))
#		self.errors_seed = command_details.get('seed')

	@execution_comfirmation
	def InjectorBeam(self, beam_name, **command_details):
		'''
		Run the 'InjectorBeam' command in Placet TCL
		
		Additional parameters
		---------------------
		macroparticles: int
			Number of macroparticles per slice
		silent: int (?)
			Suppress output at beam creation
		energyspread: float
			Energy spread of initial beam, minus value is linear spread, positive gaussian spread
		ecut: float
			Cut of the energy spread of initial beam
		energy_distribution: float
			Energy distribution of initial beam
		file: str
			Filename for the single bunch parameters
		bunches: int
			Number of bunches
		chargelist: str
			List of bunch charges (required)
		slices: int
			Number of slices
		e0: float
			Beam energy at entrance
		charge: float
			Bunch charge
		particles: int
			Number of particles for particle beam
		last_wgt: float
			Weight of the last bunch for the emittance
		distance: float
			Bunch distance
		overlapp: float
			Bunch overlap
		phase: float
			Bunch phase
		wake_scale_t: float
			Wakefield scaling transverse
		wake_scale_l: float
			Wakefield scaling longitudinal
		beta_x: float
			Horizontal beta function at entrance (required)
		alpha_x: float
			Horizontal alpha at entrance (required)
		emitt_x: float
			Horizontal emittance at entrance (required)
		beta_y: float
			Vertical beta function at entrance (required)
		alpha_y: float
			Vertical alpha at entrance (required)
		emitt_y: float
			Vertical emittance at entrance (required)
		beamload: ?
			Spline containing the longtudinal beam loading

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command	
		'''
		_options_list = ['macroparticles', 'silent', 'energyspread', 'ecut', 'energy_distribution', 'file', 'bunches', 'chargelist', 'slices', 'e0', 'charge',
		'particles', 'last_wgt', 'distance', 'overlapp', 'phase', 'wake_scale_t', 'wake_scale_l', 'beta_x', 'alpha_x', 'emitt_x', 'beta_y', 'alpha_y', 'emitt_y',
		'beamload']

		self.run_command(self.__construct_command("InjectorBeam " + beam_name, _options_list, **command_details))

	def SetRfGradientSingle(self, beam_name, var1, l):
		'''
			Corresponds to 'SetRFGradientSingle' in Placet TCL.

			I could not find any docs on this function, sources are not clear either.
			Wrapping it as it is
		'''

		self.run_command(self.__construct_command("SetRfGradientSingle " + beam_name + " " + str(var1) + " " + str(l), []))

	def BeamRead(self, **command_details):
		'''
			Corresponds to 'BeamRead' command in Placet TCL

			The full list of the command parameters:

			file					- The full list of the command parameters:
			binary					- If not zero read in binary format
			binary_stream			- Name of the file where to read particles from as a binary stream
			beam					- Name of the beam to be read

			Before calling BeamRead, the beam has to be created
		'''
		_options_list = ['file', 'binary', 'binary_stream', 'beam']

		sleep(0.3)	#needed to make sure the there is no file lock issues
		self.run_command(self.__construct_command("BeamRead", _options_list, **command_details))

	def BeamSaveAll(self, **command_details):
		"""
		Run the 'BeamSaveAll' command in Placet TCL
			Correspons to 'BeamSaveAll' command in Placet TCL

			The full list of the command parameters:
			file					- File containing beam to be saved
			beam					- Name of the beam to be saved
			header					- If set to 1 write a header into the file
			axis					- If set to 1 subtract the mean position and offset
			binary					- If set to 1 binary data is saved
			bunches					- If set to 1 each bunch is saved in a different file

			Output consists of:
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

		//**// TO UPDATE DESCRIPTION //**//

		"""
		_options_list = ['file', 'beam', 'header', 'axis', 'binary', 'bunches']

		self.run_command(self.__construct_command("BeamSaveAll", _options_list, **command_details))

	def BeamDump(self, **command_details):
		"""
		Run the 'BeamDump' command in Placet TCL
		
		Additional parameters
		---------------------
		file: str
			Name of the file from where to write the particles
		beam: str
			Name of the beam into which to read the particles
		xaxis: int
			If not zero remove mean horizontal angle and offset
		yaxis: int
			If not zero remove mean vertical angle and offset
		binary: int
			If not zero write in binary format
		binary_stream: str
			Name of the file where to write particles to as a binary stream
		losses: int
			If not zero write also the lost particles into the file
		seed: int
			Seed to be used for transforming slices to rays
		type: int
			If 1 the particles distribution in energy and z comes from continuous slices
		rotate_x: float
			rotate the bunch in the s x plane [rad]
		rotate_y: float
			rotate the bunch in the s y plane [rad]

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command	
		
		"""
		_options_list = ['file', 'beam', 'xaxis', 'yaxis', 'binary', 'binary_stream', 'losses', 'seed', 'type', 'rotate_x', 'rotate_y']

		self.run_command(self.__construct_command("BeamDump", _options_list, **command_details))

	@execution_comfirmation
	def TclCall(self, **command_details):
		"""
		Run the 'TclCall' command in Placet TCL
		
		Sets the callback function for the for the tracking (Entracnce/exit ?)
		...

		Additional parameters
		---------------------
		script: str
			The loaction of the script
		"""
		self.run_command(self.__construct_command("TclCall", ['script'], **command_details))

	def TwissMain(self, **command_details):
		'''
			Corresponds to 'TwissMain' command in Placet TCL

			//**// Needs to be updated //**//
		'''
		self.run_command(self.__construct_command("TwissMain", ['file'], **command_details))

	def GetTransferMatrix(self, **command_details):
		'''
			Corresponds to 'GetTransferMatrix' command in Placet TCL executed in the form
			set tmp [GetTransferMatrix ..]
			puts $tmp

			The full list of the command parameters:
			beamline				- Name of the beamline to be saved
			start					- Element to start from
			end						- Element to end to

			---
			If the beamline is not given, the default beamline is taken
		'''
		_options_list = ['beamline', 'start', 'end']
			
		assert 'beamline' in command_details, "beamline is not specified"

		matrix, res_matrix = self.__set_puts_command("GetTransferMatrix", _options_list, **command_details).replace("\n", "").replace("\r", ""), []
		for x in matrix.split("}"):
			if x == '':
				continue
			data = x.replace("{", "")
			row = []
			for y in data.split():
				row.append(float(y))
			res_matrix.append(row)
		return res_matrix

	def BeamSetToOffset(self, **command_details):
		'''
			Corresponds to 'BeamSetToOffset' command in Placet TCL
		'''
		_options_list = ['beam', 'x', 'y', 'angle_x', 'angle_y', 'start', 'end']

		self.run_command(self.__construct_command("BeamSetToOffset", _options_list, **command_details))

	def ElementSetToOffset(self, index, **command_details):
		'''
			Corresponds to 'ElementSetToOffset' command in Placet TCL

			The full list of the command parameters:
			x					- Horizontal offset
			y					- Vertical offset
			xp					- Horizontal offset in angle [urad]
			yp					- Vertical offset in angle [urad]
			roll				- Roll angle [urad]
			angle_x				- Same as -xp [backward compatibility]
			angle_y				- Same as -yp [backward compatibility]
		'''
		_options_list = ['x', 'y', 'xp', 'yp', 'roll', 'angle_x', 'angle_y']

		self.run_command(self.__construct_command("ElementSetToOffset " + str(index), _options_list, **command_details))

	def ElementAddOffset(self, index, **command_details):
		'''
			Corresponds to 'ElementAddOffset' command in Placet TCL

			The full list of the command parameters:
			x					- Horizontal offset
			y					- Vertical offset
			xp					- Horizontal offset in angle [urad]
			yp					- Vertical offset in angle [urad]
			roll				- Roll angle [urad]
			angle_x				- Same as -xp [backward compatibility]
			angle_y				- Same as -yp [backward compatibility]
		'''
		_options_list = ['x', 'y', 'xp', 'yp', 'roll', 'angle_x', 'angle_y']

		self.run_command(self.__construct_command("ElementAddOffset " + str(index), _options_list, **command_details))

	@execution_comfirmation
	def BpmReadings(self, **command_details):
		"""
		Run the 'BpmReadings' command in Placet TCL

		Additional parameters
		---------------------
		file: str
			The name of the file to store the bpm readings

		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		self.run_command(self.__construct_command("BpmReadings", ['file'], **command_details))

	def MoveGirder(self, **command_details):
		'''
			Corresponds to 'MoveGirder' command in Placet TCL

			the full list of the command parameters:

			file				- File to read
			vertical_only		- If not 0 only vertical plane is in the file
			binary				- If not 0 read as binary file
			scale				- Scaling factor for the motion
		'''
		_options_list = ['file', 'vertical_only', 'binary', 'scale']

		self.run_command(self.__construct_command("MoveGirder", _options_list, **command_details))

	def BpmRealign(self, **command_details):
		"""
		Run the 'BpmRealign' command in Placet TCL
		
		Additional parameters
		---------------------
		error_x: float
			Error in horizontal plane
		error_y: float
			Error in vertical plane
		bunch: int
			Which bunch to use as a reference (-1: mean of all bunches)
		
		//**//Inherits the parameters from Placet._exec_params. As per 14.11.2022 they are listed below//*//
		timeout: float
			The amount of time dedicated to executing the command, before raising the Exception.
		additional_lineskip: int
			The amount of the lines in the output to skip after executing the command
		"""
		_options_list = ['error_x', 'error_y', 'bunch']

		self.run_command(self.__construct_command("BpmRealign", _options_list, **command_details))

	"""Custom commands"""
	def get_element_transverse_matrix(self, index, **command_details):
		'''
			Returns the Tranfer matrix of an element with a given index
		'''
		return self.GetTransferMatrix(beamline = command_details.get('beamline'), start = index, end = index)

	@execution_comfirmation
	def wake_calc(self, filename, charge, a, b, sigma_z, n_slices, **command_details):
		'''
			Corresponds to a custom function calc{} in wake_calc.tcl in Placet TCL
			Is used to evaluate the wakefields and writes the output to a file

			charge
			//**// Update the description //**//
		'''
		
		self.run_command(self.__construct_command("calc " + filename + " " + str(charge) + " " + str(a) + " " + str(b) + " " + str(sigma_z) + " " + str(n_slices), [], **command_details))
		return filename

	def declare_proc(self, proc, **command_details):
		"""
		Declare a custom procedure in Placet TCL

		Parameters
		----------
		proc: func
			The function in Python.

			The content of the created procedure consists of the Placet commands that Python runs.
			The parameter addditional_lineskip = 0 is passed, since the commands in proc() will not produce any output.

			The function used for proc declaration should not have any return value
		
		Additional parameters
		---------------------
		name: str
			Name to be used for the procedure creation in Placet.
			If is not defined, the proc.__name__ is used as the name

		Additional parameters
		---------------------
		/**/ Could be any paramater that proc accepts /**/

		"""
		self.run_command(PlacetCommand("proc " + command_details.get("name", proc.__name__)  + " {} {\n", type = "custom", additional_lineskip = 0, timeout = 1))
		proc(**dict(command_details, additional_lineskip = 0, no_expect = True))
		self.run_command(PlacetCommand("}\n", type = "custom", additional_lineskip = 0, no_expect = True))

	"""extra commands"""
	def _custom_command(self, command, **command_details):
		'''
			Executes a custom command in Placet
		'''
		self.run_command(PlacetCommand(command, **command_details))


def investigation():
	pass

if __name__ == "__main__":
	investigation()