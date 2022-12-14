from .communicator import Communicator

import time
from functools import wraps

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # python 2.x

class Placetpy(Communicator):
	"""
	A class used to interact with Placet process running in background

	Extends Communicator to run Placet and Placet commands
	...
	
	Methods
	-------
	run_command(command, skipline = True)
		Run the given command in Placet
	"""
	_INTRO_LINES = 19
	def __init__(self, name = "placet", **kwargs):
		"""

		"""
		super(Placetpy, self).__init__(name, **kwargs)

		#skipping the program intro
		for i in range(self._INTRO_LINES):
			self.readline()

	def logging(func):
		"""Logging decorator used, when debug mode is on"""
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			start = time.time()
			res = func(self, *args, **kwargs)
			run_time = time.time() - start
			if self.debug_mode:
				exec_summ = dict(function = func.__name__, arguments = [args, kwargs], run_time = run_time, res = res)
				self.debug_data = self.debug_data.append(exec_summ, ignore_index = True)
				print(exec_summ)
			return res
		return wrapper

	@logging
	def run_command(self, command, skipline = True):
		"""
		Run the given command in Placet.

		Does not return any value.

		Parameters
		----------
		command: PlacetCommand
			The command to pass to Placet.
			Has to be of PlacetCommand type
		skipline: bool, default True
			If True invokes skipline() to read the written command from the buffer
		"""
		assert isinstance(command, PlacetCommand), "command must be of the type 'PlacetCommand'"
		
		opt = {}
		if command.timeout is not None:
			opt['timeout'] = command.timeout

		self.writeline(command.command, skipline, **opt)
		for x in range(command.additional_lineskip):
			self.skipline(**opt)
	
class PlacetCommand():
	"""
	A class to to classify the Placet commands

	Attributes
	----------
	command: str
		A line with Placet command, including all the options
	timeout: float
		The typical time margin for the execution time of the command. 

		Is passed further to Placetpy - if execution takes longer than timeout, throws an exception
	type: str
		The type of the command. Corresponds to the command name, without any options
	additional_lineskip: int
		The number of lines that the command produces when executed. Most of the time
	
	[23.11.2022] - Gotta revise the list of commands - some are missing. The solution is to check every time if command is in the commands list.

	"""
	command_types = ["custom", "set", "BeamlineNew", "BeamlineSet", "source", "puts", "BeamDump", "ElementGetAttribute", "WriteGirderLength", "SurveyErrorSet", "Clic", "Zero", "SaveAllPositions", 
	"InterGirderMove", "TestNoCorrection", "RandomReset", "TestSimpleCorrection", "ReadAllPositions", "QuadrupoleSetStrength", "InjectorBeam", "BeamRead", "wake_calc", "SetRfGradientSingle",
	"make_beam_particles", "BeamSaveAll", "TestMeasuredCorrection", "GetTransferMatrix", "BpmNumberList", "TwissPlotStep", "FirstOrder", "BeamSetToOffset", "ElementSetToOffset",
	"ElementAddOffset", "BpmReadings", "MoveGirder", "TestFreeCorrection", "BpmRealign", "TestRfAlignment", "QuadrupoleSetStrengthList", "CavitySetGradientList", "CavitySetPhaseList",
	"ElementSetAttributes", "TclCall", "TwissMain"]

	#options that affect the execution/parsing of the commands
	optional_parameters = ['timeout', 'additional_lineskip']

	def __init__(self, command, **kwargs):
		"""
		
		Parameters
		----------
		command: str
			The command including all the options as a string
		
		Additional parameters
		---------------------
		timeout: float
			A timeout for the command execution in Placet
		type: str
			A command name without any parameters
		additional_lineskip: int
			The number of lines of the Placet output to skip after writing the command

			Each command type has its additional_lineskip associated with it. The value passed here will overwrite it.
		"""
		self.command = command	
		self.timeout = kwargs.get('timeout', None)
		self.type = kwargs.get("type") if "type" in kwargs else self._get_command_type(command) 
		self.additional_lineskip = kwargs.get("additional_lineskip") if "additional_lineskip" in kwargs else self._additional_lineskip(self.type)

	def _additional_lineskip(self, command_type):
		"""
		Assign the default value of additional_lineskip to a command.

		If the command_type is in the list returns the default value, otherwise 0.
		
		Parameters
		----------
		command_type: str
			The command type

		Returns
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

	def _get_command_type(self, command) -> str:
		"""
		Get the type of the command based on the first word in the command.

		Parameters
		----------
		command: str
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

	def __str__(self):
		return str(self.__dict__)

	__repr__ = __str__


def test():
	placet = Placetpy(save_log = True)
	placet.writeline("BeamlineNew")
#	print(placet.readline())
#	print(placet.readline())
#	print(placet.readline())
#	print(float(placet.readline()))

def investigation():
	placet = Placetpy(save_logs = True, debug_mode = True, send_delay = None)

	for i in range(1000):
		placet.writeline("set tmp 5\n")

#	placet.save_debug_info("debug_data_py_placet_1000.pkl")
	placet.close()

if __name__  == "__main__":
#	test()
	investigation()