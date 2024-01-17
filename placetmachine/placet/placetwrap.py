from functools import wraps
from time import sleep, time
from typing import Callable, List, Optional
import pandas as pd
from placetmachine.placet import Placetpy, PlacetCommand


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

def _generate_command(command_name: str, param_list: List[str], **command_details) -> str:
	"""
	Generate the command for Placet.

	Parameters
	----------
	command_name
		The name of the command.
	param_list
		The list of the parameters that the command accepts.
	
	Other parameters
	----------------
	no_nextline: bool
		If `True` does not insert end-of-line symbol ('\n') at the end of command.
	any_kwarg
		Accepts any keyword argument that is listed in `param_list`.

	Return
	------
	str
		The constructed command.

	"""
	res = command_name
	for key in _extract_subset(param_list, command_details):
		res += f" -{key} {command_details[key]}"
	
	if command_details.get('no_nextline', False):
		return res
	
	res += "\n"
	return res

class Placet(Placetpy):
	"""
	A class used to wrap the **Placet** commands in a usable format within Python.

	Further extends [`Placetpy`][placetmachine.placet.pyplacet.Placetpy] by wrapping the commands.

	"""
	def __init__(self, **Placetpy_params):
		"""
		Other parameters
		----------------
		show_intro : bool
			If `True` (defauls is `True`), prints the welcome message of Placet at the start.
		debug_mode : bool
			If `True` (default is `False`), runs `Placet` in debug mode. 
		save_logs : bool
			If `True` (default is `True`) , invoking [`save_debug_info()`][placetmachine.placet.placetwrap.Placet.save_debug_info].
		send_delay : float
			The time delay before each data transfer to a child process (sometimes needed for stability).
			Default is `Placet._BUFFER_MAXSIZE`.
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


	def __construct_command(self, command: str, command_params: List[str], **command_details):
		"""
		Generic function for creating a `PlacetCommand`.
		
		- The **Placet** command is constructed and the command parameters are extracted from `command_details`.
		- The computing/parsing details of the command are extracted from command_details, based on the Placet._exec_params

		Parameters
		----------
		command
			Command name.
		command_params
			The full list of the arguments the corresponding command in the Placet TCL can take.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand]
		"""
		return PlacetCommand(_generate_command(command, command_params, **command_details), **dict(_extract_dict(self._exec_params, command_details), type = command.split()[0]))

	def __set_puts_command(self, command: str, command_params: List[str], **command_details):
		"""
		Generic function for executing the "set-put" chain of commands in **Placet**.

		Eg:
		```
		set tmp [command param1 param2 ..]
		puts $tmp
		```
		The data read with the last `puts` is returned.

		Parameters
		----------
		command
			Command name.
		command_params
			The full list of the arguments the corresponding command in the Placet can take.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand]

		"""
		self.set("tmp", "[" + _generate_command(command, command_params, **dict(command_details, no_nextline = True)) + "]")
		return self.puts("tmp")

	def TwissPlotStep(self, **command_details):
		"""
		Run "TwissPlotStep" command in Placet.

		Evaluates the Twiss parameters along the beamline and saves them into a file.

		Other parameters
		----------------
		beam : str
			Name of the beam to use for the calculation. **Required**
		file : str
			Name of the file where to store the results.
		step : float
			Step size to be taken for the calculation. If less than 0 the parameters will be plotted only in the centres of the quadrupoles.
		start : int
			**(?)** First particle for twiss computation.
		end : int
			**(?)** Last particle for twiss computation.
		list : List[int]
			Save the twiss parameters only at the selected elements.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		
		The output file produces with this command is composed of:

		1. Element number .
		2. s: [m] Distance in the beam line.
		3. E(s): energy [GeV] ( central slice or average energy for particle beam).
		4. beta_x_m(s) [m] (of central slice ).
		5. alpha_x_m(s) [m] (of central slice ).
		6. beta_x_i(s) [m] (of average over slices).
		7. alpha_x_i(s) [m] (of average over slices).
		8. beta_y_m(s) [m] (of central slice ).
		9. alpha_y_m(s) [m] (of central slice ).
		10. beta_y_i(s) [m] (of average over slices).
		11. alpha_y_i(s) [m] (of average over slices).
		12. disp_x(s) [m/GeV] (of average over slices).
		13. disp_xp(s) [rad/GeV] (of average over slices).
		14. disp_y(s) [m/GeV] (of average over slices).
		15. disp_yp(s) [rad/GeV] (of average over slices).
		"""
		_options_list = ['file', 'beam', 'step', 'start', 'end', 'list']

		if not 'file' in command_details:
			raise ValueError("'file' is not specified")

		self.run_command(self.__construct_command("TwissPlotStep", _options_list, **dict(command_details, expect_after = True)))

	def FirstOrder(self, **command_details):
		"""
		Run "FirstOrder" command in Placet.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("FirstOrder 1", [], **command_details))

	def set(self, variable: str, value: float, **command_details):
		"""
		Run 'set' command in TCL.

		Set the given variable to the given value in Placet.

		Parameters
		----------
		variable
			Variable to to be set.
		value
			The value the variable to be set to.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		value
			The value that was set.
		"""
		self.run_command(self.__construct_command("set " + variable + " " + str(value), [], **command_details))
		return value

	def set_list(self, name: str, **command_details):
		"""
		Declare the dictionary in Placet

		Parameters
		----------
		name
			Name of the dictionary.

		All the keyword variables provided are going to be declared int the dictionary in Placet.
		"""
		for key in command_details:
			self.set(f"{name}({key})", command_details[key])

	def puts(self, variable: str, **command_details) -> str:
		"""
		Run the 'puts' command in Placet.

		Prints the given variable in Placet, reads it and returns.
		
		Parameters
		----------
		variable
			Variable to evaluate
	
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		str
			The value Placet returned.
		"""
		self.run_command(self.__construct_command("puts $" + variable, [], **command_details))

		if command_details.get('no_read', False):
			return None

		#in case the output is one line	
		if 'timeout' in command_details:
			return self.readline(command_details.get('timeout'))
		else:
			return self.readline() 

	def source(self, filename: str, **command_details):
		"""
		Run the 'source' command in Placet.

		'Sources' the given file into Placet.

		Parameters
		----------
		filename
			Name of the file to read.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("source " + filename, [], **command_details))

#	@logging
	def TestNoCorrection(self, **command_details) -> pd.DataFrame:
		"""
		Run the 'TestNoCorrection' command in Placet.

		It is used to do the beam tracking without applying any corrections.
		
		The default time to executing each command in the chain here is set to 20s (might be changed later). 
		Parameters' description is taken from Placet manual.

		Other parameters
		----------------
		machines : int
			Number of machines to simulate. Defauls is **1**.
		beam : str
			Name of the beam to be used for tracking. **Required**
		survey : str
			Type of prealignment survey to be used. Default is `None`.
			It could be either built-in surveys from Placet, like 
			```
			["None", "Zero", "Clic", "Nlc", "Atl", "AtlZero", "Atl2", "AtlZero2,
			"Earth"]
			``` 
			or any procedure that was declared in Placet prior to the current
			function call.
		emitt_file : str
			Filename for the results' file. Defaults to NULL (no output).
		bpm_res : float
			BPM resolution. Default is **0.0**.
		format : float
			Format of the file output. (?)

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		DataFrame
			The tracking results after running TestNoCorrection.

			The columns of the resulting `DataFrame`:
			`['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']`
			The number of rows correspond to the number of the machines simulated.

		"""
		if not 'beam' in command_details:
			raise Exception("'beam' parameter is missing")
		
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
		Run the 'TestSimpleCorrection' command in Placet.

		It is used to apply the one-to-one (1-2-1) alignmet to the beamline.
		
		The default time to executing each command in the chain is set to 120s (might be changed later).
		Parameters' description is taken from the Placet manual.

		Other parameters
		----------------
		beam : str
			Name of the beam to be used for correction. **Required**
		machines : int
			Number of machines to simulate. Default is **1**.
		start : int
			First element to be corrected.
		end : int
			Last element but one to be corrected (<0: go to the end).
		interleave : int
			Used to switch on interleaved bins (correcting only focusing quadrupoles). (?)
		binlength : int
			Number of quadrupoles per bin.
		binoverlap : int
			Overlap of bins in no of quadrupoles.
		jitter_x : float
			Vertical beam jitter [micro meter].
		jitter_y : float
			Horizontal beam jitter [micro meter].
		bpm_resolution : float
			BPM resolution [micro meter].
		testbeam : str
			Name of the beam to be used for evaluating the corrected beamline.
		survey : str
			Type of prealignment survey to be used.
		emitt_file : str
			Filename for the results.
		bin_last : str
			Filename for the results.
		bin_file_out : str
			Filename for the bin information.
		bin_file_in : str
			Filename for the bin information.
		correctors : list
			List of correctors to be used.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		DataFrame
			The tracking results after running TestSimpleCorrection

			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']

			The number of rows correspond to the number of the machines simulated.

		"""
		if not 'beam' in command_details:
			raise Exception("'beam' parameter is missing")

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
		Run the 'TestMeasuredCorrection' command in Placet.

		It performes a complicated (and not obvious) correction of the beamline alignment.
		Normally is used for the DFS.
		
		The parameters' description is taken from the Placet Manual.

		Other parameters
		----------------		
		machines : int
			Number of machines to simulate. Default is **1**.
		start : int
			First element to be corrected.
		end : int
			Last element but one to be corrected (<0: go to the end).
		binlength : int
			Number of quadrupoles per bin.
		correct_full_bin : int
			If not zero the whole bin will be corrected.
		binoverlap : int
			Overlap of bins in no of quadrupoles.
		jitter_x : float
			Vertical beam jitter [micro meter].
		jitter_y : float
			Horizontal beam jitter [micro meter].
		bpm_resolution : float
			BPM resolution [micro meter].
		rf_align : int(?)
			Align the RF after the correction. (?)
		no_acc : int(?)
			Switch RF off in corrected subsection. (?)
		beam0 : str
			Name of the main beam to be used for correction.
		beam1 : str
			Name of the first help beam to be used for correction.
		beam2 : str
			Name of the second help beam to be used for correction.
		cbeam0 : str
			Name of the main beam to be used for correction.
		cbeam1 : str
			Name of the first help beam to be used for correction.
		cbeam2 : str
			Name of the second help beam to be used for correction.
		gradient1 : float
			Gradient for beam1.
		gradient2 : float
			Gradient for beam2.
		survey : str
			Type of prealignment survey to be used defaults to CLIC.
		emitt_file : str
			Filename for the results defaults to NULL (no output).
		wgt0 : float
			Weight for the BPM position.
		wgt1 : float
			Weight for the BPM resolution.
		wgt2 : float
			Second weight for the BPM resolution.
		pwgt : float
			Weight for the old position.
		quad_set0 : list(?)
			List of quadrupole strengths to be used.
		quad_set1 : list(?)
			List of quadrupole strengths to be used.
		quad_set2 : list(?)
			List of quadrupole strengths to be used.
		load_bins : str
			File with bin information to be loaded.
		save_bins : str
			File with bin information to be stored.
		gradient_list0 : list(?)
			Cavity gradients for beam 0.
		gradient_list1 : list(?)
			Cavity gradients for beam 1.
		gradient_list2 : list(?)
			Cavity gradients for beam 2.
		bin_iterations : int
			Number of iterations for each bin.
		beamline_iterations : int
			Number of iterations for each machine.
		correctors : list
			List of correctors to be used.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		DataFrame
			The tracking results after running TestSimpleCorrection

			The columns of the resulting DataFrame:
			['correction', 'beam', 'survey', 'positions_file', 'emittx', 'emitty']

			The number of rows correspond to the number of the machines simulated.
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
				'beam': command_details.get('beam0'),
				'survey': command_details.get('survey', None),
				'positions_file': command_details.get("errors_file", None), 
				'emittx': None, 
				'emitty': float(self.readline(timeout).split()[-2])}, index = [i])
			data_log = pd.concat([data_log, track_tmp])
		self.skipline()	#sum of the simulations over several machines
		return data_log

	def TestRfAlignment(self, **command_details) -> None:
		"""
		Run the 'TestRfAlignment' command in Placet.	

		It performs the RF alignment on the beamline.

		The command TestRfAlignment does not produce any output inside Placet.

		Other parameters
		----------------
		beam : str
			Name of the beam to be used for correction. **Required**
		testbeam : str
			Name of the beam to be used for evaluating the corrected beamline.
		machines : int
			Number of machines.
		binlength : int
			Length of the correction bins.
		wgt0 : float
			Weight for the BPM position.
		wgt1 : float
			Weight for the BPM resolution.
		pwgt : float
			Weight for the old position.
		girder : int
			Girder alignment model: 
			0 - none; 1 - per girder; 2 - per bin
		bpm_resolution : float
			BPM resolution [micro meter].
		survey : str
			Type of prealignment survey to be used.
		emitt_file : str
			Filename for the results defaults to NULL (no output).
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_extra_time, _options_list = 120, ['beam', 'testbeam', 'machines', 'binlength', 'wgt0', 'wgt1', 'pwgt', 'girder', 'bpm_resolution', 'survey', 'emitt_file']
		self.run_command(self.__construct_command("TestRfAlignment", _options_list, **command_details))

	def BeamlineNew(self, **command_details):
		"""
		Run 'BeamlineNew' command in Placet.

		It is required to be called before starting declaring the beamline. All the elements declared afterwards are going to be included in the 
		new beamline.
			
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("BeamlineNew", [], **command_details))

	def BeamlineSet(self, **command_details) -> str:
		"""
		Run	'BeamlineSet' command in Placet TCL.

		Fixes the beamline. This command is used to do some initial calculations. It must be called **once but only once** for a given beamline in a run.
		
		Other parameters
		----------------
		name : str
			Name of the beamline to create. **Required**
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		"""
		if not 'name' in command_details:
			raise Exception("'name' parameter is missing")

		self.run_command(self.__construct_command("BeamlineSet", ['name'], **command_details))
		return command_details.get('name')

	def QuadrupoleNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'QuadrupoleNumberList' command in Placet.

		It returns the list quadrupoles IDs.
		
		The following chain is executed:
		```
		% set tmp [QuadrupoleNumberList]
		% puts $tmp
		```
		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the quadrupoles IDs.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("QuadrupoleNumberList", [], **command_details).split()))

	def CavityNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'CavityNumberList' command in Placet.

		It returns the list cavities IDs.
		
		The following chain is executed:
		```
		% set tmp [CavityNumberList]
		% puts $tmp
		```
		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the cavities IDs.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CavityNumberList", [], **command_details).split()))

	def BpmNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'BpmNumberList' command in Placet.

		It returns the list BPMs IDs.

		The following chain is executed:
		```
		% set tmp [BpmNumberList]
		% puts $tmp
		```
		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the BPMs IDs.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("BpmNumberList", [], **command_details).split()))

	def DipoleNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'DipoleNumberList' command in Placet.

		It returns the list dipoles IDs.
		
		The following chain is executed:
		```
		% set tmp [DipoleNumberList]
		% puts $tmp
		```

		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the dipoles IDs.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("DipoleNumberList", [], **command_details).split()))

	def MultipoleNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'MultipoleNumberList' command in Placet.

		It returns the list multipoles IDs.
		
		The following chain is executed:
		```
		% set tmp [MultipoleNumberList -orded order]
		% puts $tmp
		```

		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other parameters
		----------------
		order : int
			Order of the multipoles. **Required**
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the multipoles IDs.
		"""
		if not 'order' in command_details:
			raise Exception("'order' parameter is missing.")
		
		return list(map(lambda x: int(x), self.__set_puts_command("MultipoleNumberList", ['order'], **command_details).split()))

	def CollimatorNumberList(self, **command_details) -> List[int]:
		"""
		Run the 'CollimatorNumberList' command in Placet.

		It returns the list collimators IDs.
		
		The following chain is executed:
		```
		% set tmp [CollimatorNumberList]
		% puts $tmp
		```
		
		*An alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[int]
			The list with the colimators IDs.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CollimatorNumberList", [], **command_details).split()))

	def CavityGetPhaseList(self, **command_details) -> List[float]:
		"""
		Run the 'CavityGetPhaseList' command in Placet.
		
		It returns the list with the cavities' phases.

		The following chain is executed:
		```
		% set tmp [CavityGetPhaseList]
		% puts $tmp
		```

		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[float]
			The list of the cavities phases.
		"""
		return list(map(lambda x: int(x), self.__set_puts_command("CavityGetPhaseList", [], **command_details)))

	def QuadrupoleGetStrength(self, quad_number: int, **command_details) -> float:
		"""
		Run 'QuadrupoleGetStrength' command in Placet.

		It returns the strength of the quadrupole with the given number.

		The following chain is executed:
		```
		% set tmp [QuadrupoleGetStrength quad_number]
		% puts $tmp
		```

		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*

		Parameters
		----------
		quad_number
			The quad ID.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		float
			Quadrupole strength.

		***Needs to be verified!***
		"""
		return float(self.__set_puts_command("QuadrupoleGetStrength " + str(quad_number), [], **command_details).split()[-1])

	def QuadrupoleSetStrength(self, quad_number: int, value: float, **command_details):
		"""
		Run 'QuadrupoleSetStrength' command in Placet.

		It sets the given strength os the quadrupole of the given number.

		Parameters
		----------
		quad_number
			The quadrupole ID.
		value
			Quadrupole new strengths.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(PlacetCommand("QuadrupoleSetStrength " + str(quad_number) + " " + str(value) + "\n"))

	def QuadrupoleSetStrengthList(self, values_list: List[float], **command_details):
		"""
		Run the 'QuadrupoleSetStrengthList' in Placet.

		It sets the strengths of the quadrupoles according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet throws an error.
		
		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*

		Parameters
		----------
		values_list : List[float]
			The list with the quadrupoles strengths.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("QuadrupoleSetStrengthList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def CavitySetGradientList(self, values_list, **command_details):
		"""
		Run the 'CavitySetGradientList' command in Placet.

		It sets the gradients of the cavities according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet throws an error

		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*

		Parameters
		----------
		values_list: list(float)
			The list with cavities gradients

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("CavitySetGradientList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def CavitySetPhaseList(self, values_list: List[float], **command_details):
		"""
		Run the 'CavitySetPhaseList' command in Placet.

		It sets the phases of the cavities according to the input data.
		The length of the list must correspond to the number of cavities, otherwise Placet would throw an error

		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*

		Parameters
		----------
		values_list
			The list with cavities gradients.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("CavitySetPhaseList " + "{".join(list(map(lambda x: " " + str(x), values_list))) + "}", [], **command_details))

	def ElementGetAttribute(self, element_id: int, parameter: str, **command_details) -> float:
		"""
		Run 'ElementGetAttribute' command in Placet.

		It extracts the value of the element's parameter with the given id.
		
		*A better alternative is the use of [`Beamline`][placetmachine.lattice.lattice.Beamline].*

		Parameters
		----------
		element_id
			ID of an element.
		parameter
			Parameter to extract
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		float
			The extracted value.
		"""
		self.run_command(self.__construct_command("ElementGetAttribute " + str(element_id) + " -" + parameter, []), **command_details)
		return float(self.readline().split()[-1])

	def ElementSetAttributes(self, element_id: int, **command_details):
		"""
		Run 'ElementSetAttributes' command in Placet.

		It sets the given parameters in `command_details` to the given element.
		
		The full list of the possible arguments (depends on the element type) is:
		```
		['name', 's', 'x', 'y', 'xp', 'yp', 'roll', 'length', 'synrad', 'six_dim', 'thin_lens', 'e0', 'aperture_x', 'aperture_y', 'aperture_losses', 'aperture_shape',
		'strength', 'tilt', 'hcorrector', 'hcorrector_step_size', 'vcorrector', 'vcorrector_step_size', 'angle', 'E1', 'E2', 'K', 'K2', 'resolution', 'reading_x', 
		'reading_y', 'scale_x', 'scale_y', 'store_bunches', 'gradient', 'phase', 'type', 'lambda', 'frequency', 'strength_x', 'strength_y', 'steps']
		```

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
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
		"""
		Run 'WriteGirderLength' command in Placet.

		***Needs to checked***
		"""
		if not 'file' in command_details:
			raise Exception("'file' parameter is missing")

		_options_list = ['file', 'binary', 'beginning_only', 'absolute_position']		

		self.run_command(self.__construct_command("WriteGirderLength", _options_list, **command_details))

	def SurveyErrorSet(self, **command_details):
		"""
		Run 'SurveyErrorSet' command in Placet.

		It sets the alignment errors for the beamline.	
		When the command is invoked - it overwrittes the values already in memory. That means if one calls it with `cavity_y = 5.0` that means that
		`cavity_y` property will be overwritten, others will be kept unchanged. So the values not declared are zeros by default.
		
		*The descriptions taken from the Placet Manual*

		Other parameters
		----------------
		quadrupole_x : float
			Horizontal quadrupole position error [micro m].
		quadrupole_y : float
			Vertical quadrupole position error [micro m].
		quadrupole_xp : float
			Horizontal quadrupole angle error [micro radian].
		quadrupole_yp : float
			Vertical quadrupole angle error [micro radian].
		quadrupole_roll : float
			Quadrupole roll around longitudinal axis [micro radian].
		cavity_x : float
			Horizontal structure position error [micro m].
		cavity_realign_x : float
			Horizontal structure position error after realignment [micro m].
		cavity_y : float
			Vertical structure position error [micro m].
		cavity_realign_y : float
			Vertical structure position error after realignment [micro m].
		cavity_xp : float
			Horizontal structure angle error [micro radian].
		cavity_yp : float
			Vertical structure angle error [micro radian].
		cavity_dipole_x : float
			Horizontal dipole kick [rad*GeV].
		cavity_dipole_y : float
			Vertical dipole kick [rad*GeV].
		piece_x : float
			Horizontal structure piece error [micro m].
		piece_xp : float
			Horizontal structure piece angle error [micro radian].
		piece_y : float
			Vertical structure piece error [micro m].
		piece_yp : float
			Vertical structure piece angle error [micro radian].
		bpm_x : float
			Horizontal BPM position error [micro m].
		bpm_y : float
			Vertical BPM position error [micro m].
		bpm_xp : float
			Horizontal BPM angle error [micro radian].
		bpm_yp : float
			Vertical BPM angle error [micro radian].
		bpm_roll : float
			BPM roll around longitudinal axis [micro radian].
		sbend_x : float
			Horizontal sbend position error [micro m].
		sbend_y : float
			Vertical sbend position error [micro m].
		sbend_xp : float
			Horizontal sbend angle error [micro radian].
		sbend_yp : float
			Vertical sbend angle error [micro radian].
		sbend_roll : float
			Sbend roll around longitudinal axis [micro radian].
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['quadrupole_x', 'quadrupole_y', 'quadrupole_xp', 'quadrupole_yp', 'quadrupole_roll', 'cavity_x', 'cavity_realign_x', 'cavity_y', 'cavity_realign_y', 
		'cavity_xp', 'cavity_yp', 'cavity_dipole_x', 'cavity_dipole_y', 'piece_x', 'piece_xp', 'piece_y', 'piece_yp', 'bpm_x', 'bpm_y', 'bpm_xp', 'bpm_yp', 'bpm_roll',
		'sbend_x', 'sbend_y', 'sbend_xp', 'sbend_yp', 'sbend_roll']

		self.run_command(self.__construct_command("SurveyErrorSet", _options_list, **command_details))


	def Clic(self, **command_details):
		"""
		Run 'Clic' command in Placet.

		It sets the beamline misalignment according to the CLIC setup.
		
		Other parameters
		----------------
		start : int
			The ID of the first element to apply the misalignments.
		end : int
			The ID of the last element to apply the misalignments.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['start', 'end']

		self.run_command(self.__construct_command("Clic", _options_list, **command_details))

	def Zero(self, **command_details):
		"""
		Run 'Zero' command in Placet.

		It resets the beamline misalignments to zeros.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("Zero", [], **command_details))

	def SaveAllPositions(self, **command_details):
		"""
		Run 'SaveAllPositions' command in Placet.

		It saves all the elements positions into a file.

		Other parameters
		----------------
		file : str
			Filename to write. **Required**
		binary : int
			If not 0 save as binary file.
		nodrift : int
			If not 0 drift positions will not be saved.
		vertical_only : int
			If not 0 only vertical information will be saved.
		positions_only : int
			If not 0 only positions will be saved.
		cav_bpm : int
			If not 0 positions of structure BPMs will be saved.
		cav_grad_phas : int
			If not 0 gradient and phase of structure will be saved.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		if not 'file' in command_details:
			raise Exception("'file' parameter is missing")
		_options_list = ['file', 'binary', 'nodrift', 'vertical_only', 'positions_only', 'cav_bpm', 'cav_grad_phas']
		
		self.run_command(self.__construct_command("SaveAllPositions", _options_list, **dict(command_details, expect_after = True)))

	def ReadAllPositions(self, **command_details):
		"""
		Run 'ReadAllPositions' command in Placet.

		Reads the elements' positions from a file and applies them to a beamline.
		
		Other parameters
		----------------
		file : str
			Filename to read. **Required**
		binary : int
			If not 0 read as binary file.
		nodrift : int
			If not 0 drift positions are not read.
		nomultipole : int
			If not 0, multipoles are not read.
		vertical_only : int
			If not 0 only vertical information are read.
		positions_only : int
			If not 0 only positions are read.
		cav_bpm : int
			If not 0 positions of structure BPMs are read.
		cav_grad_phas : int
			If not 0 gradient and phase of structure are read.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		if not 'file' in command_details:
			raise Exception("'file' parameter is missing")
		_options_list = ['file', 'binary', 'nodrift', 'nomultipole', 'vertical_only', 'positions_only', 'cav_bpm', 'cav_grad_phas']

		self.run_command(self.__construct_command("ReadAllPositions", _options_list, **command_details))

	def InterGirderMove(self, **command_details):
		"""
		Run the 'InterGirderMove' command in Placet.

		It sets the alignment properties of the girder endpoints wrt the reference wire and itselves.

		Other parameters
		----------------
		scatter_x : float
			Sigma of Gaussian scattering in x view of the intersubsections between girders [micrometers].
		scatter_y : float
			Sigma of Gaussian scattering in y view of the intersubsections between girders [micrometers].
		flo_x : float
			Sigma of Gaussian scattering in x view of the girder connection around the intersubsection point [micrometers].
		flo_y : float
			Sigma of Gaussian scattering in y view of the girder connection around the intersubsection point [micrometers].
		cav_only : int
			If not zero move only the cavities on the girder.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['scatter_x', 'scatter_y', 'flo_x', 'flo_y', 'cav_only']

		self.run_command(self.__construct_command("InterGirderMove", _options_list, **command_details))

	def RandomReset(self, **command_details):
		"""
		Run the 'RandomReset' command in Placet.
		
		Resets the errors seed number in Placet.

		Other parameters
		----------------
		seed : int
			The seed number to set.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['seed']

		self.run_command(self.__construct_command("RandomReset", _options_list, **command_details))
#		self.errors_seed = command_details.get('seed')

	def InjectorBeam(self, beam_name, **command_details):
		"""
		Run the 'InjectorBeam' command in Placet.

		Creates a new macroparticle beam in Placet based on the template of the InjectorBeam. 
		It is typically used to create any type of beam.
		
		*The list of parameters is taken from Placet manual.*

		Other parameters
		----------------
		macroparticles : int
			Number of macroparticles per slice.
		silent : int (?)
			Suppress output at beam creation.
		energyspread : float
			Energy spread of initial beam, minus value is linear spread, positive gaussian spread.
		ecut : float
			Cut of the energy spread of initial beam.
		energy_distribution : float
			Energy distribution of initial beam.
		file : str
			Filename for the single bunch parameters.
		bunches : int
			Number of bunches.
		chargelist : str
			List of bunch charges (required).
		slices : int
			Number of slices.
		e0 : float
			Beam energy at entrance.
		charge : float
			Bunch charge.
		particles : int
			Number of particles for particle beam.
		last_wgt : float
			Weight of the last bunch for the emittance.
		distance : float
			Bunch distance.
		overlapp : float
			Bunch overlap.
		phase : float
			Bunch phase.
		wake_scale_t : float
			Wakefield scaling transverse.
		wake_scale_l : float
			Wakefield scaling longitudinal.
		beta_x : float
			Horizontal beta function at entrance (required).
		alpha_x : float
			Horizontal alpha at entrance (required).
		emitt_x : float
			Horizontal emittance at entrance (required).
		beta_y : float
			Vertical beta function at entrance (required).
		alpha_y : float
			Vertical alpha at entrance (required).
		emitt_y : float
			Vertical emittance at entrance (required).
		beamload : int
			Spline containing the longtudinal beam loading.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['macroparticles', 'silent', 'energyspread', 'ecut', 'energy_distribution', 'file', 'bunches', 'chargelist', 'slices', 'e0', 'charge',
		'particles', 'last_wgt', 'distance', 'overlapp', 'phase', 'wake_scale_t', 'wake_scale_l', 'beta_x', 'alpha_x', 'emitt_x', 'beta_y', 'alpha_y', 'emitt_y',
		'beamload']

		self.run_command(self.__construct_command("InjectorBeam " + beam_name, _options_list, **command_details))

	def SetRfGradientSingle(self, beam_name: str, var1: float, l: float):
		"""
		Run 'SetRFGradientSingle' command in Placet.

		***This function is not documented. Placet sources are not clear either. It is wrapped as it is.***

		Parameters
		----------
		beam_name
			Beam name.
		var1
			No idea.
		l
			No idea.
		"""

		self.run_command(self.__construct_command("SetRfGradientSingle " + beam_name + " " + str(var1) + " " + str(l), []))

	def BeamRead(self, **command_details):
		"""
		Run 'BeamRead' command in Placet.

		Reads the beam from a file. Before calling 'BeamRead', the beam has to be created

		Other parameters
		----------------
		file : str					
			The name of the file to read.
		binary : int
			If not zero read in binary format.
		binary_stream : str
			Name of the file where to read particles from as a binary stream.
		beam : str
			Name of the beam to be read.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['file', 'binary', 'binary_stream', 'beam']

		sleep(0.3)	#needed to make sure the there is no file lock issues
		self.run_command(self.__construct_command("BeamRead", _options_list, **command_details))

	def BeamSaveAll(self, **command_details):
		"""
		Run the 'BeamSaveAll' command in Placet.

		It saves the macroparticle beam to a file.

		Other parameters
		----------------
		file : str
		 	File containing beam to be saved.
		beam : str
			Name of the beam to be saved.
		header : int
			If set to 1 write a header into the file.
		axis : int
			If set to 1 subtract the mean position and offset.
		binary : int
			If set to 1 binary data is saved.
		bunches : int
			If set to 1 each bunch is saved in a different file.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		The output file consists of:

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
		"""
		_options_list = ['file', 'beam', 'header', 'axis', 'binary', 'bunches']

		self.run_command(self.__construct_command("BeamSaveAll", _options_list, **command_details))

	def BeamDump(self, **command_details):
		"""
		Run the 'BeamDump' command in Placet.

		Saves the particle beam coordinates.
		
		Other parameters
		----------------
		file : str
			Name of the file from where to write the particles.
		beam : str
			Name of the beam into which to read the particles.
		xaxis : int
			If not zero remove mean horizontal angle and offset.
		yaxis : int
			If not zero remove mean vertical angle and offset.
		binary : int
			If not zero write in binary format.
		binary_stream : str
			Name of the file where to write particles to as a binary stream.
		losses : int
			If not zero write also the lost particles into the file.
		seed : int
			Seed to be used for transforming slices to rays.
		type : int
			If 1 the particles distribution in energy and z comes from continuous slices.
		rotate_x : float
			rotate the bunch in the s x plane [rad].
		rotate_y : float
			rotate the bunch in the s y plane [rad].

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['file', 'beam', 'xaxis', 'yaxis', 'binary', 'binary_stream', 'losses', 'seed', 'type', 'rotate_x', 'rotate_y']

		self.run_command(self.__construct_command("BeamDump", _options_list, **command_details))

	def TclCall(self, **command_details):
		"""
		Run the 'TclCall' command in Placet.

		Essentially sets up the callback function for the tracking.
		Not sure when it is invoked (entrance or exit). It works for the beamline ext though.

		Other parameters
		----------------
		script : str
			The name of the script to be used as a callback.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("TclCall", ['script'], **command_details))

	def TwissMain(self, **command_details):
		"""
		Run 'TwissMain' command in Placet.

		Not sure if it even works. Last checks showed it produces a blank file.

		Other parameters
		----------------
		file : str
			The name of the file to write the Twiss.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("TwissMain", ['file'], **command_details))

	def GetTransferMatrix(self, **command_details) -> List[float]:
		"""
		Run'GetTransferMatrix' command in Placet.

		Evaluates the transfer matrix between the given elements.

		The foolowing chain is executed:
		```
		% set tmp [GetTransferMatrix ..]
		% puts $tmp
		```

		Other parameters
		----------------
		beamline : str
			Name of the beamline to be saved. **Required**
		start : int
			Element to start from.
		end : int
			Element to end to.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		List[float]
			Resulting transfer matrix.
		"""
		_options_list = ['beamline', 'start', 'end']
			
		if not 'beamline' in command_details:
			raise Exception("'beamline' parameter is missing")

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
		"""
		Run 'BeamSetToOffset' command in Placet.

		Offsets the beam according to the given settings.

		Other parameters
		----------------
		beam : str
			The name of the beam.
		x : float
			x in microns.
		y : float
			y in microns.
		angle_x : float
			Horizontal angle in microrads.
		angle_y : float
			Vertical angle in microrads.
		start : int
			First element to misalign the  beam at.
		end : int
			Last element to misalign the beam at.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['beam', 'x', 'y', 'angle_x', 'angle_y', 'start', 'end']

		self.run_command(self.__construct_command("BeamSetToOffset", _options_list, **command_details))

	def ElementSetToOffset(self, index: int, **command_details):
		"""
		Run 'ElementSetToOffset' command in Placet.

		Sets the given offsets to a given element.

		Parameters
		----------
		index
			The element ID.
		
		Other parameters
		----------------
		x : float
			Horizontal offset.
		y : float
			Vertical offset.
		xp : float
			Horizontal offset in angle [urad].
		yp : float
			Vertical offset in angle [urad].
		roll : float
			Roll angle [urad].
		angle_x : float
			Same as -xp [backward compatibility].
		angle_y : float
			Same as -yp [backward compatibility].

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['x', 'y', 'xp', 'yp', 'roll', 'angle_x', 'angle_y']

		self.run_command(self.__construct_command("ElementSetToOffset " + str(index), _options_list, **command_details))

	def ElementAddOffset(self, index, **command_details):
		"""
		Run 'ElementAddOffset' command in Placet.

		Adds the given offsets to the current ones of the given element.

		Parameters
		----------
		index
			The element ID.
		
		Other parameters
		----------------
		x : float
			Horizontal offset.
		y : float
			Vertical offset.
		xp : float
			Horizontal offset in angle [urad].
		yp : float
			Vertical offset in angle [urad].
		roll : float
			Roll angle [urad].
		angle_x : float
			Same as -xp [backward compatibility].
		angle_y : float
			Same as -yp [backward compatibility].

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['x', 'y', 'xp', 'yp', 'roll', 'angle_x', 'angle_y']

		self.run_command(self.__construct_command("ElementAddOffset " + str(index), _options_list, **command_details))

	def BpmReadings(self, **command_details):
		"""
		Run the 'BpmReadings' command in Placet.

		Reads the reading on the BPMs available in the beamlimne. Before doing so, Placet must run any kind of tracking.

		Other parameters
		----------------
		file : str
			The name of the file to store the bpm readings.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(self.__construct_command("BpmReadings", ['file'], **dict(command_details, expect_after = True)))

	def MoveGirder(self, **command_details):
		"""
		Run 'MoveGirder' command in Placet.

		Other parameters
		----------------
		file : str
			File to read.
		vertical_only : int
			If not 0 only vertical plane is in the file.
		binary : int
			If not 0 read as binary file.
		scale : float
			Scaling factor for the motion.
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['file', 'vertical_only', 'binary', 'scale']

		self.run_command(self.__construct_command("MoveGirder", _options_list, **command_details))

	def BpmRealign(self, **command_details):
		"""
		Run the 'BpmRealign' command in Placet TCL.

		Realigns the BPMs tranversaly such that their centers are aligned with the current beam orbit.
		
		Other parameters
		----------------
		error_x : float
			Error in horizontal plane.
		error_y : float
			Error in vertical plane.
		bunch : int
			Which bunch to use as a reference (-1: mean of all bunches).
		
		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		_options_list = ['error_x', 'error_y', 'bunch']

		self.run_command(self.__construct_command("BpmRealign", _options_list, **command_details))

	"""Custom commands"""
	def get_element_transverse_matrix(self, index : int, **command_details) -> List[float]:
		"""
		Evaluate the Transfer matrix of a given element.
		
		Parameters
		----------
		index
			An element ID.
		
		Other parameters
		----------------
		beamline : str
			A name of the beamline.

		Returns
		-------
		List[float]
			Resulting transfer matrix.
		"""
		return self.GetTransferMatrix(beamline = command_details.get('beamline'), start = index, end = index)

	def wake_calc(self, filename : str, charge : float, a : float, b : float, sigma_z : float, n_slices : int, **command_details) -> str:
		"""
		Run a custom function calc{} from "wake_calc.tcl" in Placet.

		It is used to evaluate the wakefields and write the output to a file.
		The resulting file contains the slices weights and wakefiled parameters.

		Parameters
		----------
		filename
			The name of the file to produce.
		charge
			The bunch charge.
		a
			To check.
		b
			To check.
		sigma_z
			Bunch length in microns.
		n_slices
			Number of slices.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].

		Returns
		-------
		str
			The name of the generated file.
		"""
		
		self.run_command(self.__construct_command("calc " + filename + " " + str(charge) + " " + str(a) + " " + str(b) + " " + str(sigma_z) + " " + str(n_slices), [], **command_details))
		return filename

	def declare_proc(self, proc : Callable, **command_details):
		"""
		Declare a custom procedure in Placet.

		Parameters
		----------
		proc: func
			The function in Python.

			The content of the created procedure consists of the Placet commands that Python runs.
			The parameter `addditional_lineskip = 0` is passed, since the commands within `proc()` environment in Placet
			do not produce any output.

			The function used for proc declaration should not have any return value, otherwise the execution is going
			to be blocked.
		
		Other parameters
		----------------
		name : str
			Name of the created procedure in Placet.
			If is not defined, the `proc.__name__` is used as the name.

		Other arguments accepted are inherited from `PlacetCommand` but some of them will be forcely overwritten. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(PlacetCommand("proc " + command_details.get("name", proc.__name__)  + " {} {\n", type = "custom", additional_lineskip = 0, timeout = 1))
		proc(**dict(command_details, additional_lineskip = 0, no_expect = True))
		self.run_command(PlacetCommand("}\n", type = "custom", additional_lineskip = 0, no_expect = True))

	"""extra commands"""
	def _custom_command(self, command : str, **command_details):
		"""
		Execute a custom command in Placet.

		Parameters
		----------
		command
			Command to execute.

		Other arguments accepted are inherited from `PlacetCommand`. See the list [optional parameters][placetmachine.placet.pyplacet.PlacetCommand].
		"""
		self.run_command(PlacetCommand(command, **command_details))
