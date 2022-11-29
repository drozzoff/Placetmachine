import pexpect
import time
from threading import Thread
import pandas as pd
from functools import wraps

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # python 2.x

class Communicator(object):
	"""
	A class used to interact with the process spawned with Pexpect
	
	It also creates a deamon process for reading the child's output
	...

	Attributes
	----------
	process: pexpect.spawn
		The child process spawned with pexpect
	debug_mode: bool, default False
		If True, running in debug mode
	out_buffer: Queue
		The queue with the data read from process terminal

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
	writelines(commands)
		Write the lines to a child process
	close()
		Finish the runnning processes and terminate the child process
	save_debug_info(filename = "debug_data.pkl")
		Save the debug data to a file

	"""
	_BASE_TIMEOUT = 5
	_BUFFER_MAXSIZE = 1000
	_DELAY_BEFORE_SEND = 0.1
	_TERMINAL_SPECIAL_SYMBOL = "% "


	def __init__(self, process_name, **kwargs):
		"""
		21.06.2022	- spawning the reader thread on init

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
		self.process = pexpect.spawn(process_name, timeout = None, encoding = 'utf-8')
		
		self.debug_mode = kwargs.get('debug_mode', False)
	
		if self.debug_mode:
			print("Debug mode is on. Running the process " + process_name + " with parameters " + str(kwargs))
			self.debug_data = pd.DataFrame(columns = ['function', 'arguments', 'run_time', "res"])

		if kwargs.get("save_logs", True):
			self.save_logs()

		self.add_send_delay(kwargs.get('send_delay', self._DELAY_BEFORE_SEND))

		self.out_buffer = Queue(maxsize = self._BUFFER_MAXSIZE)
		self.__spawn_out_stream()
	
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
				print("\t" + str(exec_summ))
			return res
		return wrapper

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
	def writeline(self, command, skipline = True, timeout = _BASE_TIMEOUT) -> str:
		"""
		Send the line to a child process
		
		Parameters
		----------
		command

		skipline

		timeout

		Returns
		-------
		str
		"""
		self.process.write(command)
#		if self.debug_mode:
#			print("Running: " + command, end = "")
		if skipline: self.skipline(timeout)
		return command

	def writelines(self, commands):
		"""
		Send the lines to a child process
		
		Paramaters
		----------
		commands
		"""
		for command in commands:
			self.writeline(command)

	def __terminate(self):
		""" """
		if self.process.isalive():
			self.process.terminate()

	def close(self):
		"""Close all the associated thread running"""
		self.__kill_out_thread()
		self.__terminate()

	def _readline(self):
		"""Get the line if available in out_buffer, otherwise None"""
		try:
			res = self.out_buffer.get() 
		except Empty:
			res = None
		return res

	@logging
	def skipline(self, timeout = _BASE_TIMEOUT):
		"""
		Skip the line of the child's process output.
		
		Paramaters
		----------
		timeout: float, default Communicator._BASE_TIMEOUT
			Timeout of the reader before raising the exception.
		"""
		self.readline(timeout)
	
	def __remove_special_symbol(func):
		"""
		Wrapper for readline()

		Check if the string has special interactive shell symbols at the start. If so, removes them.
		"""
		@wraps(func)
		def wrapper(self, timeout = None):
			res = func(self, timeout) if timeout is not None else func(self)
			base = ""
			while len(base) < len(res):
				if res.startswith(base + self._TERMINAL_SPECIAL_SYMBOL):
					base += self._TERMINAL_SPECIAL_SYMBOL
				else:
					break
			return res[len(base):]
		return wrapper

	def __placet_error_seeker(func):
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
				raise Exception("Placet exited with an error message:\n" + res)
			if "warning".casefold() in list(map(lambda x: x.casefold(), res.split())):
				raise Exception("Placet encountered a warning:\n" + res)
			return res
		return wrapper

	@logging
	@__remove_special_symbol
	@__placet_error_seeker
	def readline(self, timeout = _BASE_TIMEOUT) -> str:
		"""
		Read the line from the child process.

		Parameters
		----------
		timeout: float, default Communicator._BASE_TIMEOUT
			Timeout of the reader before raising the exception.

		Raises
		------
		Exception
			if no data is read after the timeout has passed.

		Returns
		-------
		str
			The line of the data received from the child process.
		"""
		start, res = time.time(), self._readline()

		exec_time = 0.0 
		while res is None:
			exec_time = time.time() - start
			if exec_time > timeout:			
				raise Exception("No data found!")
			res = self._readline()

		#21.06.2022	- the thread is running constantly
		# self._kill_out_thread()
		# if self.debug_mode:
		# 	print("\t" + res, end = "")
		return res

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

		Returns
		-------
		list
			The list of the lines received from the child process.
		"""
		start, res = time.time(), []
		for i in range(N_lines):	
			tmp = self._readline()
			while tmp is None:
				if time.time() - start > timeout: 
					raise Exception("readlines() - No data found!")

				tmp = self._readline()
			res.append(tmp)
		return res

	@logging
	def __spawn_out_stream(self):
		"""
		Start a thread for an online reading of the output from the child process.

		An old if/else routine handling the init/kill of the created thread
		In practice there is no benefit from killing the reader each time
		the command is executed. The computational time is higher. Also
		occasionally, the thread could stuck, ignoring timeout which
		produces readline() Exception.
		"""
		# if hasattr(self, '_t'):
		# 	#Thread exist in the memory
		# 	if self._t.isAlive():
		# 		#Thread is running
		# 		if self._thread_exit_flag:
		# 			#If it is running
		# 			#->	 not doing anything
		# 			return
		# 		else:
		# 			#If the flag to end the process is False and the thread is running
		# 			#->	waiting for the thread to finish
		# 			self._t.join(self._BASE_TIMEOUT)
		# 			self._thread_exit_flag = True
		# 	else:
		# 		#Thread finished running
		# 		#->	reseting the flag
		# 		self._thread_exit_flag = True
		# else:
		# 	#Thread does not exist in the memory
		# 	#->	creating the flag
		# 	self._thread_exit_flag = True
		self.__thread_exit_flag = True
		
		def reader():
			while self.__thread_exit_flag:
				line = self.process.readline()
				if line is not None:
					self.out_buffer.put(line)
				else:
					pass
		self._t = Thread(target = reader)
		self._t.daemon = True
		self._t.start()

	def __kill_out_thread(self):
		"""Kill the ouput reading process."""
		self.__thread_exit_flag = False

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

def test():
	test = Communicator("./madx")

	test.save_logs()

	for x in test.readlines(8):
		print(x, end = "")
#		print(x), #python 2.x
	
	test.writeline("tmp1 = 5;\n")
	test.writeline("value, tmp1;\n")
#	test.write("tmp2 = 6;\n")
#	test.write("tmp3 = 7;\n")



#	test.write("value, tmp3;\n")
#	print(test.readlines(4))
	print(test.readline())
#	print(test.readline())
#	print(test.readline())
#	test.close()

def test2():
	test = Communicator("python2")
	test.save_logs()

	test.writeline("a = 5\n")

	print(test.readline())
	print(test.readline())
	print(test.readline())
	print(test.readline())

def test3():
	test = Communicator("placet", debug_mode = True, save_logs = True, send_delay = None)

#	for i in range(19):
#		test.readline(10)
	test.readlines(19)

	while True:
		test.writeline("set tmp 5\n")
		

if __name__ == '__main__':
	test3()