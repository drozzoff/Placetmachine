import pexpect
import time
import pandas as pd
from functools import wraps
import json


class Communicator(object):
	"""
	A class used to interact with the process spawned with Pexpect
	
	...

	Attributes
	----------
	process: pexpect.spawn
		The child process spawned with pexpect
	debug_mode: bool, default False
		If True, running in debug mode

	Methods
	-------
	add_send_delay(time = _DELAY_BEFORE_SEND)
		Add the time delay before sending the data to child process
	save_logs()
		Create the files for logging the terminal in/out-put
	readline(timeout = _BASE_TIMEOUT)
		Read the line received from a child process
	readlines(N_lines, timeout = _BASE_TIMEOUT)
		Read several lines received from a child process
	skipline(timeout = _BASE_TIMEOUT)
		Same to readline, but no return
	writeline(command, skipline = True, timeout = _BASE_TIMEOUT)
		Write the line to a child process
	close()
		Finish the runnning processes and terminate the child process
	save_debug_info(filename = "debug_data.pkl")
		Save the debug data to a file

	"""
	_BASE_TIMEOUT = 100
	_BUFFER_MAXSIZE = 1000
	_DELAY_BEFORE_SEND = 0.1
	_TERMINAL_SPECIAL_SYMBOL = "% "

	__expect_block = False
	def __init__(self, process_name, **kwargs):
		"""
		29.11.2022	- New version of the communicator without the daemon running in the background

		Parameters
		----------
		process_name: str
			name of the child process

		Additional parameters
		---------------------
		debug_mode: bool, default False
			If True, runs Communicator in debug mode
		save_logs: bool, default True
			If True, invoking save_debug_info()
		send_delay: float, default Communicator._BUFFER_MAXSIZE
			The time delay before each data transfer to a child process (sometimes needed for stability)
		"""
		self._process_name, self.debug_mode = process_name, kwargs.get('debug_mode', False),
		self._save_logs = kwargs.get("save_logs", True)
		self._send_delay = kwargs.get('send_delay', self._DELAY_BEFORE_SEND)
		self.__init()

	def __init(self):
		self.process = pexpect.spawnu(self._process_name, timeout = None, encoding = 'utf-8')

		if self.debug_mode:
			print(f"Debug mode is on. Running the process {self._process_name}, debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay}")
			self.debug_data = pd.DataFrame(columns = ['function', 'arguments', 'run_time', "res"])

		if self._save_logs or self.debug_mode:
			self.save_logs()

		self.add_send_delay(self._send_delay)

	def _restart(self):
		"""Restart the child process"""
		if self.isalive():
			self.close()

		self.__init()

	def logging(func):
		"""Log the functions running"""
		@wraps(func)
		def wrapper(self, *args, **kwargs):
			start = time.time()
			res = func(self, *args, **kwargs)
			run_time = time.time() - start
			if self.debug_mode:
				exec_summ = dict(function = func.__name__, arguments = [args, kwargs], run_time = run_time, res = res)
				self.debug_data = self.debug_data.append(exec_summ, ignore_index = True)
				print(json.dumps(exec_summ, indent = 4, sort_keys = True))
			return res

		@wraps(func)
		def wrapper_2(self, *args, **kwargs):
			if self.debug_mode:
				exec_summ = dict(function = func.__name__, arguments = [args, kwargs])
				self.debug_data = self.debug_data.append(exec_summ, ignore_index = True)
				print("\t" + str(exec_summ))

			res = func(self, *args, **kwargs)

			return res

		return wrapper_2

	def add_send_delay(self, time = _DELAY_BEFORE_SEND):
		"""Add the time delay before each data transfer"""
		self.process.delaybeforesend = time

	def save_logs(self):
		"""
		Open the files to store the log data of a child process

		default names are "log_send.txt" for logfile_send and "log_read.txt" for logfile_read
		"""
		self.process.logfile_send = open("log_send.txt", "w")
		self.process.logfile_read = open("log_read.txt", "w")

	@logging
	def writeline(self, command, skipline = True, timeout = _BASE_TIMEOUT, **kwargs) -> str:
		"""
		Send the line to a child process
		
		[10.03.2023] - Added the expect to search for a prompt given in _TERMINAL_SPECIAL_SYMBOL before invoking
						`self.process.write()`.
						Doing so, we make sure that we do not try to write while the process is still busy with the
						previous command.
						We set the default timeout of Communicator._BASE_TIMEOUT.
						Ideally, this should fix the issue, when we run the commands that do not produce any output
						in the terminal.
		
		The optional parameters 'expect_before' and 'expect_after' used to specify when to use the expect command
		in between writing the command
		There has to be always 1 'expect' call after command execution. By default, one 'expect' call is used before
		writing the command. In certain situations, one would want to do the 'expect' call after the command is written.
		The parameter __expect_block controls the use of 'expect' commands - making sure, only 1 expect command is 
		invoked in between commands. But, with 'no_expect' one can skip this limitation.
		..........

		Parameters
		----------
		command: str
			Command to execute
		skipline: bool, default True
			If True, reads the command that was sent to a child process from child's process output
			This flag depends on the default running mode of pexpect. By default, it outputs to stdout what was just
			send to stdin
		timeout: float, default _BASE_TIMEOUT
			Timeout of the reader before raising the exception.
			[30.11.2022] - No effect anymore. The parameter is kept for compatibility.
		
		Additional parameters
		---------------------
		expect_before: bool default True
			If True, expect is invoked before writing the command.
		expect_after: bool default False
			If True, expect is invoked after writing the command.
		no_expect: bool, False
			If True, no expect is invoked, ignoring __expect_block

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

	def isalive(self):
		return self.process.isalive()

	def __terminate(self):
		"""Terminate the child process"""
		if self.isalive():
			self.process.terminate()

	def close(self):
		"""Close all the associated threads running"""
		self.__terminate()

	@logging
	def skipline(self, timeout = _BASE_TIMEOUT):
		"""
		Skip the line of the child's process output.
		
		Paramaters
		----------
		timeout: float, default Communicator._BASE_TIMEOUT
			Timeout of the reader before raising the exception.
			[30.11.2022] - No effect anymore. The parameter is kept for compatibility.
		"""
		self.readline(timeout)

	def __error_seeker(func):
		"""
		Wrapper for readline().

		Checks if the output does not contain an error.

		If containts "ERROR", throws an exception
		If containts "WARNING", throws an exception
		"""
		@wraps(func)
		def wrapper(self, timeout = None):
			res = func(self, timeout) if timeout is not None else func(self)

			if "error".casefold() in list(map(lambda x: x.casefold(), res.split())):
				raise Exception("Process exited with an error message:\n" + res)
			if "warning".casefold() in list(map(lambda x: x.casefold(), res.split())):
				raise Exception("Process encountered a warning:\n" + res)
			return res
		return wrapper

	@logging
	@__error_seeker
	def readline(self, timeout = _BASE_TIMEOUT) -> str:
		"""
		Read the line from the child process.

		Parameters
		----------
		timeout: float, default Communicator._BASE_TIMEOUT
			Timeout of the reader before raising the exception.
			[30.11.2022] - No effect anymore. The parameter is kept for compatibility.

		Returns
		-------
		str
			The line of the data received from the child process.
		"""

		return self.process.readline()

	@logging
	def readlines(self, N_lines, timeout = _BASE_TIMEOUT) -> list:
		"""
		Read several lines from the child process.
		
		Parameters
		----------
		N_lines: int
			Number of lines to read.
		timeout: float, default Communicator._BASE_TIMEOUT
			Timeout of the reader before raising the exception.
			[30.11.2022] - No effect anymore. The parameter is kept for compatibility.

		Returns
		-------
		list
			The list of the lines received from the child process.
		"""
		res = []
		for i in range(N_lines):
			res.append(self.readline(timeout))
		return res

	def flush(self):
		"""Flush the child process buffer"""
		self.process.flush()

	def save_debug_info(self, filename = "debug_data.pkl"):
		"""
		Save the debug info to a files.
		
		Parameters
		----------
		filename: str, default debug_data.pkl
			Name of the file.
		"""
		if self.debug_mode:
			self.debug_data.to_pickle(filename)

	def __repr__(self):
		return f"Communicator('{self._process_name}', debug_mode = {self.debug_mode}, save_logs = {self._save_logs}, send_delay = {self._send_delay})"

	def __str__(self):
		return f"Communicator(process_name = '{self._process_name}', is_alive = {self.isalive()})"
