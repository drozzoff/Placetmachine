from functools import wraps
from typing import Callable, Optional
from placetmachine.placet import Communicator


class PlacetCommand():
	"""
	A class used to classify the **Placet** commands.

	Attributes
	----------
	command : str
		A line with Placet command, including all the options
	timeout : float
		The typical time margin for the execution time of the command. 
		Is passed further to `Placetpy` - if execution takes longer than timeout, throws an exception
	type : str
		The type of the command. Corresponds to the command name, without any options
	additional_lineskip : int
		The number of lines that the command produces when executed.
	
	"""
	command_types = ["custom", "set", "BeamlineNew", "BeamlineSet", "source", "puts", "BeamDump", "ElementGetAttribute", "WriteGirderLength", "SurveyErrorSet", "Clic", "Zero", "SaveAllPositions", 
					"InterGirderMove", "TestNoCorrection", "RandomReset", "TestSimpleCorrection", "ReadAllPositions", "QuadrupoleSetStrength", "InjectorBeam", "BeamRead", "wake_calc", "SetRfGradientSingle",
	"make_beam_particles", "BeamSaveAll", "TestMeasuredCorrection", "GetTransferMatrix", "BpmNumberList", "TwissPlotStep", "FirstOrder", "BeamSetToOffset", "ElementSetToOffset",
	"ElementAddOffset", "BpmReadings", "MoveGirder", "TestFreeCorrection", "BpmRealign", "TestRfAlignment", "QuadrupoleSetStrengthList", "CavitySetGradientList", "CavitySetPhaseList",
	"ElementSetAttributes", "TclCall", "TwissMain"]

	#options that affect the execution/parsing of the commands
	optional_parameters = ['timeout', 'additional_lineskip', 'expect_after', 'expect_before', 'no_expect']

	def __init__(self, command: str, **kwargs):
		"""
		Parameters
		----------
		command
			The command including all the options as a string.
		
		Other parameters
		----------------
		timeout : Optional[float]
			A timeout for the command execution in Placet.
		type : str
			A command type. Correspons to the command name without any parameters.
			If not provided, is evaluated automatically.
		additional_lineskip : int
			The number of lines of the Placet output to skip after writing the command.
			If not provided, is evaluated automatically based on the type of a command.
		expect_before : bool
			If `True` (default is `True`), `expect` command is invoked before 'writing' the command.
		expect_after : bool
			If `True` (default is `False`), `expect` command is invoked after 'writing' the command.
		no_expect : bool
			If `True` (default is `False`), `expect` command for the command prompt is not invoked neither before or after doing 'writing'.
			Overwrites `expect_before` and `expect_after` parameters.
		"""
		self.command = command
		self.timeout = kwargs.get('timeout', None)
		self.type = kwargs.get("type") if "type" in kwargs else self._get_command_type(command) 
		self.additional_lineskip = kwargs.get("additional_lineskip") if "additional_lineskip" in kwargs else self._additional_lineskip(self.type)
		self.no_expect = kwargs.get('no_expect', False)
		self.expect_before = kwargs.get('expect_before', True)
		self.expect_after = kwargs.get('expect_after', False)

	def _additional_lineskip(self, command_type: str) -> int:
		"""
		Assign the default value of additional_lineskip to a command.

		If the command_type is in the list returns the default value, otherwise 0.
		
		Parameters
		----------
		command_type
			The command type.

		Returns
		-------
		int
			The value of the additional_lineskip.
		"""
		if command_type in ["set", "RandomReset"]:
			return 1
		elif command_type in ["BeamlineNew", "puts", "BeamDump", "ElementGetAttribute", "ElementSetAttribute", "WriteGirderLength", "Clic", "Zero", "SaveAllPositions", "InterGirderMove", 
		"TestNoCorrection", "ReadAllPositions", "QuadrupoleSetStrength", "InjectorBeam", "BeamRead", "SetRfGradientSingle", "make_beam_particles", "BeamDump", "BeamSaveAll",
		"GetTransferMatrix", "BpmNumberList", "TwissPlotStep", "FirstOrder", "BeamSetToOffset", "ElementSetToOffset", "ElementAddOffset", "BpmReadings", "MoveGirder", "BpmRealign",
		"QuadrupoleSetStrengthList", "CavitySetGradientList", "CavitySetPhaseList", "ElementSetAttributes", "TclCall", "TwissMain"]:
			return 0
		elif command_type in ["BeamlineSet", "TestMeasuredCorrection", "TestFreeCorrection", "TestRfAlignment"]:
			return 2
		elif command_type in ["TestSimpleCorrection"]:
			return 3
		elif command_type in ["SurveyErrorSet"]:
			return 27
		else:
			return 0

	def _get_command_type(self, command: str) -> str:
		"""
		Get the type of the command based on the first word in the command.

		Parameters
		----------
		command
			The full command, including parameters
		
		Returns
		-------
		str
			The type of the command
		"""
		keyword = command.split()[0]
		if keyword in self.command_types:
			return keyword
		else:
			raise ValueError("Command " + keyword + " does not exist!")

	def __repr__(self):
		return f"PlacetCommand({repr(self.command)}, timeout = {self.timeout}, type = '{self.type}', additional_lineskip = {self.additional_lineskip}, expect_before = {self.expect_before}, expect_after = {self.expect_after}, no_expect = {self.no_expect})"	
	
	def __str__(self):
		return f"PlacetCommand(command = {repr(self.command)})"

def error_seeker(func: Callable) -> Callable:
	"""
	Decorator that checks for the words "error"/"warning" in PLACET output.

	Checks the output of the decorated function.

	If containts "ERROR", throws an exception.
	If containts "WARNING", throws an exception.
	"""
	@wraps(func)
	def wrapper(self, timeout: float = None):
		res = func(self, timeout) if timeout is not None else func(self)

		if "error".casefold() in list(map(lambda x: x.casefold(), res.split())):
			self.process.close()
			raise Exception("Process exited with an error message:\n" + res)
		if "warning".casefold() in list(map(lambda x: x.casefold(), res.split())):
			self.process.close()
			raise Exception("Process encountered a warning:\n" + res)
		return res
	return wrapper

def logging(func: Callable) -> Callable:
	"""
	Logging decorator. 
	
	By default does not do anything. When debug mode is invoked prints the functions'
	execution summary
	"""
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		if self.debug_mode:
			exec_summ = dict(function = func.__name__, arguments = [args, kwargs])
			print(exec_summ)
			self.debug_data = self.debug_data.append(exec_summ, ignore_index = True)
#				print(json.dumps(exec_summ, indent = 4, sort_keys = True))

		res = func(self, *args, **kwargs)
		
		return res
	
	return wrapper

class Placetpy(Communicator):	
	"""
	A class used to interact with **Placet** process running in background.

	Extends [`Communicator`][placetmachine.placet.communicator.Communicator] to run **Placet**
	and its commands of the proper format.
	"""
	_INTRO_LINES = 19
	def __init__(self, name: str = "placet", **kwargs):
		"""
		Parameters
		----------
		name
			The name of the process to start. Should be the command starting **Placet** interactive shell.

		Other parameters
		----------------
		show_intro : bool
			If `True` (defauls is `True`), prints the welcome message of Placet at the start.
		debug_mode : bool
			If `True` (default is `False`), runs `Placetpy` in debug mode. 
		save_logs : bool
			If `True` (default is `True`) , invoking [`save_debug_info()`][placetmachine.placet.pyplacet.Placetpy.save_debug_info].
		send_delay : float
			The time delay before each data transfer to a child process (sometimes needed for stability).
			Default is `Placetpy._BUFFER_MAXSIZE`.
		"""
		super(Placetpy, self).__init__(name, **kwargs)
		self._show_intro = kwargs.get("show_intro", True)

		self.__read_intro()

	def __read_intro(self):
		#skipping the program intro
		for i in range(self._INTRO_LINES):
			tmp = self.readline()
			if self._show_intro:
				print(tmp, end = "")

	def restart(self):
		"""Restart the child process."""
		self._restart()
		self.__read_intro()

	@error_seeker
	def readline(self, timeout: float = Communicator._BASE_TIMEOUT):
		"""
		Read the line from **Placet** process.

		Parameters
		----------
		timeout
			Timeout of the reader before raising the exception.
			*No effect anymore. The parameter is kept for compatibility.*

		Returns
		-------
		str
			The line of the data received from the child process.
		"""
		return self._readline()

	@logging
	def run_command(self, command: PlacetCommand, skipline: bool = True):
		"""
		Run the given command in **Placet**.

		**Does not return any value.**
		The output after the execution is up to the user to read with [`readline()`][placetmachine.placet.pyplacet.Placetpy.readline]
		or [`readlines()`][placetmachine.placet.pyplacet.Placetpy.readlines].

		Parameters
		----------
		command
			The command to pass to Placet.
		skipline
			If `True` invokes [`skipline()`][placetmachine.placet.pyplacet.Placetpy.skipline] to read the command back from the buffer.
			This option is needed when the process writes the command it 'writes' into the out buffer.
		"""
		opt = {
			'no_expect': command.no_expect,
			'expect_before': command.expect_before,
			'expect_after': command.expect_after
		}
		if command.timeout is not None:
			opt['timeout'] = command.timeout

		self.writeline(command.command, skipline, **opt)
		for x in range(command.additional_lineskip):
			self.skipline()
	
	def __repr__(self):
		return f"Placetpy('{self._process_name}', debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay}, show_intro = {self._show_intro})"

	def __str__(self):
		return f"Placetpy(process_name = '{self._process_name}', is_alive = {self.isalive()})"
