from functools import wraps
from abc import ABC, abstractmethod
import pandas as pd
from typing import Callable, List
import pexpect


def alive_check(func: Callable) -> Callable:
	"""
	Decorator that checks if the child process is alive before interacting with it.

	Used with [`writeline()`][placetmachine.placet.communicator.Communicator.writeline], 
	[`readline()`][placetmachine.placet.communicator.Communicator.readline], and 
	[`readlines()`][placetmachine.placet.communicator.Communicator.readlines].
	"""
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		if self.isalive():
			return func(self, *args, **kwargs)
		else:
			raise Exception(f"The process is dead. Restart it before running '{func.__name__}'.")
	
	return wrapper

def logging(func: Callable) -> Callable:
	"""
	Decorator that logs the execution of [`writeline()`][placetmachine.placet.communicator.Communicator.writeline], 
	[`readline()`][placetmachine.placet.communicator.Communicator.readline], and 
	[`readlines()`][placetmachine.placet.communicator.Communicator.readlines].
	"""
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		if self.debug_mode:
			exec_summ = dict(function = func.__name__, arguments = [args, kwargs])
			self.debug_data = self.debug_data.append(exec_summ, ignore_index = True)
			print(f"\t{exec_summ}")

		res = func(self, *args, **kwargs)

		return res

	return wrapper

class Communicator(ABC):
	"""
	A class used to interact with the process spawned with [`Pexpect`](https://github.com/pexpect/pexpect).
	
	Attributes
	----------
	process : pexpect.spawn
		The child process spawned with pexpect.
	debug_mode : bool
		If True, running in debug mode.

	"""
	_BASE_TIMEOUT = 100
	_BUFFER_MAXSIZE = 1000
	_DELAY_BEFORE_SEND = 0.1
	_TERMINAL_SPECIAL_SYMBOL = "% "

	__expect_block = False
	def __init__(self, process_name: str, **kwargs):
		"""
		Parameters
		----------
		process_name
			Name of the child process

		Other parameters
		----------------
		debug_mode : bool
			If `True` (default is `False`), runs `Communicator` in debug mode. 
		save_logs : bool
			If `True` (default is `True`) , invoking [`save_debug_info()`][placetmachine.placet.communicator.Communicator.save_debug_info].
		send_delay : float
			The time delay before each data transfer to a child process (sometimes needed for stability).
			Default is `Communicator._BUFFER_MAXSIZE`.
		"""
		self._debug_mode = kwargs.get('debug_mode', False)
		self._process_name = process_name
		self._save_logs = kwargs.get("save_logs", True)
		self._send_delay = kwargs.get('send_delay', self._DELAY_BEFORE_SEND)
		self.__init()

	def __init(self):
		self.process = pexpect.spawnu(self._process_name, timeout = None, encoding = 'utf-8')

		self.__debug_init()

		if self._save_logs or self.debug_mode:
			self.save_logs()

		self.add_send_delay(self._send_delay)

	def __debug_init(self):
		if self.debug_mode:
			print(f"Debug mode is on. Running the process '{self._process_name}', debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay}")
			self.debug_data = pd.DataFrame(columns = ['function', 'arguments', 'run_time', "res"])

	@property
	def debug_mode(self) -> bool:
		return self._debug_mode

	@debug_mode.setter
	def debug_mode(self, value: bool):
		if self._debug_mode == False and value == True:
			# debug mode being switched on
			self._debug_mode = value
			self.__debug_init()
		if self._debug_mode == True and value == False:
			# debug mode being switched off
			print("Debug mode is switched off")
			self._debug_mode = value
		

	def _restart(self):
		"""Restart the child process"""
		if self.isalive():
			self.close()

		self.__init()

	def add_send_delay(self, time: float = _DELAY_BEFORE_SEND):
		"""
		Add the time delay before each data transfer.
		
		Parameters
		----------
		time
			The time delay.
		"""
		self.process.delaybeforesend = time

	def save_logs(self):
		"""
		Open the files to store the log data of a child process

		By default, the names are "log_send.txt" for logfile_send and "log_read.txt" for logfile_read.
		"""
		self.process.logfile_send = open("log_send.txt", "w")
		self.process.logfile_read = open("log_read.txt", "w")

	@logging
	@alive_check
	def writeline(self, command: str, skipline: bool = True, timeout: float = _BASE_TIMEOUT, **kwargs) -> str:
		"""
		Send the line to a child process.
		
		There is an `expect` call to search for a prompt defined in `Communicator._TERMINAL_SPECIAL_SYMBOL` (default value is '% ')
		before writing to a process - `process.write()`. Doing so, we make sure that we do not try to write while the process 
		is still busy with the previous command. We set the default timeout of `Communicator._BASE_TIMEOUT`.
		
		The optional parameters `expect_before` and `expect_after` used to specify when to use the expect command
		in between writing the command.
		There has to be always 1 `expect` call after command execution. By default, one `expect` call is used before
		writing the command. In certain situations, one would want to do the `expect` call after the command is written.
		The parameter `__expect_block` controls the use of `expect` commands - making sure, only 1 expect command is 
		executed in between 2 commands.

		Parameters
		----------
		command
			Command to execute
		skipline
			If True, reads the command that was sent to a child process from child's process output
			This flag depends on the default running mode of pexpect. By default, it outputs to stdout what was just
			send to stdin
		timeout
			Timeout of the reader before raising the exception.
			*[30.11.2022] - No effect anymore. The parameter is kept for compatibility.*
		
		Other parameters
		----------------
		expect_before : bool
			If `True` (default is `True`), `expect` is invoked before writing the command.
		expect_after : bool
			If `True` (default is `False`), `expect` is invoked after writing the command.
		no_expect : bool
			If `True` (default is `False`), no `expect` is invoked, ignoring `__expect_block`

		Returns
		-------
		str
			The command that was sent to a child process
		"""
		no_expect = kwargs.get('no_expect', False)
		if kwargs.get('expect_before', True) and not self.__expect_block and not no_expect:
			self.process.expect(self._TERMINAL_SPECIAL_SYMBOL, timeout = self._BASE_TIMEOUT)

		self.flush()

		self.process.write(command)

		if skipline: self.skipline(timeout)
		self.__expect_block = False

		if kwargs.get('expect_after', False) and not no_expect:
			self.process.expect(self._TERMINAL_SPECIAL_SYMBOL, timeout = self._BASE_TIMEOUT)
			self.__expect_block = True

		return command

	def isalive(self) -> bool:
		return self.process.isalive()

	def __terminate(self):
		"""Terminate the child process."""
		if self.isalive():
			self.process.terminate()

	def close(self):
		"""Close all the associated threads running."""
		self.__terminate()

	@logging
	@alive_check
	def _readline(self, timeout: float = _BASE_TIMEOUT) -> str:
		"""
		Read the line from the child process.

		Parameters
		----------
		timeout:
			Timeout of the reader before raising the exception.
			*[30.11.2022] - No effect anymore. The parameter is kept for compatibility.*

		Returns
		-------
		str
			The line of the data received from the child process.
		"""

		return self.process.readline()
	
	@logging
	@alive_check
	def skipline(self, timeout: float = _BASE_TIMEOUT):
		"""
		Skip the line of the child's process output.
		
		Parameters
		----------
		timeout
			Timeout of the reader before raising the exception.
			*[30.11.2022] - No effect anymore. The parameter is kept for compatibility.*
		"""
		self._readline(timeout)

	@abstractmethod
	def readline(self) -> str:
		"""
		Read the line from the child process.

		Returns
		-------
		str
			The line of the data received from the child process.
		"""
		pass

	@logging
	@alive_check
	def readlines(self, N_lines: int, timeout: float = _BASE_TIMEOUT) -> List[str]:
		"""
		Read several lines from the child process.
		
		Parameters
		----------
		N_lines
			Number of lines to read.
		timeout
			Timeout of the reader before raising the exception.
			[30.11.2022] - No effect anymore. The parameter is kept for compatibility.

		Returns
		-------
		list
			The list of the lines received from the child process.
		"""
		res = []
		for i in range(N_lines):
			res.append(self._readline(timeout))
		return res

	def flush(self):
		"""Flush the child process buffer"""
		self.process.flush()

	def save_debug_info(self, filename: str = "debug_data.pkl"):
		"""
		Save the debug info to a files.
		
		Parameters
		----------
		filename
			Name of the file.
		"""
		if self.debug_mode:
			self.debug_data.to_pickle(filename)

	def __repr__(self):
		return f"Communicator('{self._process_name}', debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay})"

	def __str__(self):
		return f"Communicator(process_name = '{self._process_name}', is_alive = {self.isalive()})"
