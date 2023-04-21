from pandas import DataFrame
import re
from typing import List, Callable
import warnings

from .quadrupole import Quadrupole
from .cavity import Cavity
from .drift import Drift
from .bpm import Bpm
from .dipole import Dipole


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

def _to_str(x):
	if x == 0: 
		return '0'
	elif x == 1.0: 
		return '1'
	elif x == -1.0:
		return '-1'
	else:
		return str(x)

class AdvancedParser:
	"""
	A class to do the parsing of the PLACET lattice.

	Can perform the following measures:
		- Read and remember values that are set. Eg.:
			% set tmp 5
		- Put the value instead of the variable. Eg.:
			% .. -strength expr [0.5*$e0] .. -> % .. -strength expr [0.5*190.0] ..
			% .. -e0 $e_initial .. -> .. -e0 190.0 ..
		- Evaluate the values inside of the expr call. Eg.:
			% .. -strength expr [0.5*190.0] .. -> .. -strength 95.0 ..

	Attributes
	----------

	"""
	def __init__(self, **variables_list):
		"""Taking the variables list a"""
		self.variables = variables_list

		#making sure, everyhting is str:
		self.variables = {key: str(self.variables[key]) for key in self.variables}

	def replace_variables(self, var):
		"""Get the variable from the memory. If does not exist, set to '0'"""
		if var not in self.variables:
			warnings.warn(f"Variable '{var}' is missing. It is assigned to '0'.")
			self.variables[var] = "0"

		return self.variables[var]

	def evaluate_expression(self, match):
		"""Evaluate the expression from inside of a Tcl expr []"""
		parameter = match.group(1)
		expression_with_vars = match.group(2)
		
		# Replace variables with their values
		expression = re.sub(r'\$(\w+)', lambda match: self.replace_variables(match.group(1)), expression_with_vars)

		result = eval(expression)
		return f"{parameter} {result}"

	def parse(self, line):
		"""
		Parse the line.

		Currently, can perform the following measures:
			- Read and remember values that are set. Eg.:
				% set tmp 5
			- Put the value instead of the variable. Eg.:
				% .. -strength expr [0.5*$e0] .. -> % .. -strength expr [0.5*190.0] ..
				% .. -e0 $e_initial .. -> .. -e0 190.0 ..
			- Evaluate the values inside of the expr call. Eg.:
				% .. -strength expr [0.5*190.0] .. -> .. -strength 95.0 ..
		..........
		Parameters
		----------
		line: str
			The string line to parse
		"""
		# Update the variables dictionary if a 'set' command is found
		set_match = re.search(r'set (\w+) ([\d.]+)', line)
		if set_match:
			self.variables[set_match.group(1)] = set_match.group(2)

		# Replace expressions with their evaluated results
		line = re.sub(r'(\S+)\s*\[expr\s(.*?)\]', self.evaluate_expression, line)

		# Replace other variables that appear in the format `-var $var`
		line = re.sub(r'(\S+)\s*\$(\w+)', lambda match: f"{match.group(1)} {self.replace_variables(match.group(2))}", line)

		return line

class Beamline():
	"""
	A class used to store the lattice

	Fully compatible with Placet and can be imported.
	
	Attributes
	----------
	name: str
		Name of the beamline.
	lattice: list, default []
		The list of the elements forming the beamline.

		The accepted elements are Bpm, Cavity, Quadrupole, Drift
	girders: dict
		The dict containing the following info:
		{
			'girder1': [elems on girder1]
			'girder2': [elems on girder2]
			..
		}
	quad_numbers_list: list
		The list with the quadrupoles indices
	cavity_numbers_list: list
		The list with the cavities indices
	bpm_numbers_list: list
		The list with the bpms indices

	Methods
	-------
	get_girders_number()
		Get the total number of the girders in the beamline
	get_quads_numbers()
		Get the list of the Quadrupoles indices
	get_cavs_list()
		Get the list of the Cavities in the beamline
	get_quads_list()
		Get the list of the Quadrupoles in the beamline
	get_bpms_list()
		Get the list of the Bpms in the beamline
	get_drifts_list()
		Get the list of the Drifts in the beamline
	get_girder(girder_index)
		Get the list of the elements on the girder
	to_placet(filename = None)
		Convert the lattice to a Placet readable format
	read_misalignments(filename, **extra_params)
		Read the lattice misalignments from a file (same format Placet uses)
	save_misalignments(filename, **extra_params)
		Save the lattice misalingments to a file (same format Placet uses)
	cache_beamline(**extra_params)
		Create the backup copy of the beamline
	upload_from_cache(clear_cache = False, **extra_params)
		Upload the
	"""

	_supported_elements = ["Bpm", "Cavity", "Quadrupole", "Drift"]
	_parsers = ['advanced', 'default']

	def __init__(self, name):
		"""
		Parameters
		----------
		name: str
			Name of the beamline.
		"""
		self.name, self.lattice, self.girders = name, [], {}

	def __repr__(self):
		return f"Beamline('{self.name}') && lattice = {list(map(lambda x: repr(x), self.lattice))}"

	def __str__(self):
		_data_to_show = ['name', 'type', 'girder', 's', 'x', 'xp', 'y', 'yp']
		_settings_data = ['name', 's', 'x', 'xp', 'y', 'yp']
		data_dict = {key: [None] * len(self.lattice) for key in _data_to_show}
		for i in range(len(self.lattice)):
			for key in _settings_data:
				data_dict[key][i] = self.lattice[i].settings[key]
			data_dict['type'][i] = self.lattice[i].type
			data_dict['girder'][i] = self.lattice[i].girder

		res_table = DataFrame(data_dict)
#		res_table.name = self.name
		
		return f"Beamline(name = '{self.name}', structure = \n{str(res_table)})"

	def _verify_supported_elem_types(self, types):
		if types is None:
			return None
		for elem_type in types:
			if elem_type not in self._supported_elements:
				raise ValueError(f"Unsupported element type - {elem_type}")
		return True

	def cache_lattice_data(self, types):
		"""
		Cache up the data for certain types of the elements
		
		Parameters
		----------
		types: list, optional
			The list containing the types of the elements that the caching is applied to
			Eg. ['Bpm', 'Cavity']
			If type is None, not performing any actions
		"""
		if self._verify_supported_elem_types(types) is not None:
			for element in self.lattice:
				if element.type in types:
					element.cache_data()
		else:
			return

	def upload_from_cache(self, types, clear_cache = False, **extra_params):
		"""
		Restore the cached data for certain elements

		Parameters
		----------
		types: list
			The list containing the types of the elements that the caching is applied to
			Eg. ['Bpm', 'Cavity']
		clear_cache: bool, default False
			If True, cleares the cached beamline
		"""
		if self._verify_supported_elem_types(types) is not None:
			for element in self.lattice:
				if element.type in types:
					element.use_cached_data(clear_cache)
		else:
			return

	def read_from_file(self, filename: str, **extra_params):
		"""
		Read the lattice from the Placet lattice file

		Girders numbering starts from 1.
		Evaluates the longitudinal coordinates while parsing the lattice. The coordinate s corresponds to the element exit.

		Parameters
		----------
		filename: str
			Name of the file with the lattice

		Additional parameters
		---------------------
		debug_mode: bool default False
			If True, prints all the information it reads and processes
		parser: str default "default"
			Type of parser to be used. See Beamline._parsers
		parser_variables: {}
			The dict with the variables for the 'advanced parser'.
		"""
		parser = extra_params.get('parser', "default")
		if not parser in self._parsers:
			raise ValueError(f"Unsupported parser '{parser}'. Accepted values are: {str(self._parsers)}")

		preprocess_func = lambda x: x
		if parser == "advanced":
			advanced_parser = AdvancedParser(**extra_params.get('parser_variables', {}))
			preprocess_func = lambda x: advanced_parser.parse(x)

		girder_index, index, debug_mode, __line_counter = 0, 0, extra_params.get('debug_mode', False), 1
		if debug_mode:
			print(f"Processing the file '{filename}' with a parser '{parser}'")
		with open(filename, 'r') as f:
			for line in f.readlines():
				if debug_mode:
					line_tmp = line.strip('\n')
					print(f"#{__line_counter}. Read: '{line_tmp}'")
					__line_counter += 1
					if parser == "advanced":
						processed_line_tmp = preprocess_func(line).strip('\n')
						print(f"---Parsed: '{processed_line_tmp}'")
				elem_type, element = parse_line(preprocess_func(line), girder_index, index)

				if debug_mode:
					print(f"---Element created: {repr(element)}")
				if elem_type == 'Girder':
					girder_index += 1
					continue
				elif elem_type is None:
					continue
				index += 1
				if self.lattice == []:
					element.settings['s'] = element.settings['length']
				else:
					element.settings['s'] = self.lattice[-1].settings['s'] + element.settings['length']
				self.lattice.append(element)

		for girder_id in range(1, self.get_girders_number() + 1):
			self.girders[girder_id] = self._get_girder(girder_id)

	def get_girders_number(self) -> int:
		"""Get the total number of the girders in the beamline"""
		return self.lattice[-1].girder

	@property
	def quad_numbers_list(self) -> List[int]:
		"""Get the list of the Quadrupoles indices"""
		if not hasattr(self, '_quad_numbers_list_'):
			self._quad_numbers_list_ = list(map(lambda quad: quad.index, self.get_quads_list()))
			
		return self._quad_numbers_list_

	@property
	def cavs_numbers_list(self) -> List[int]:
		"""Get the list of the Cavities indices"""
		if not hasattr(self, '_cav_numbers_list_'):
			self._cav_numbers_list_ = list(map(lambda cav: cav.index, self.get_cavs_list()))
			
		return self._cav_numbers_list_
	
	@property
	def bpms_numbers_list(self) -> List[int]:
		"""Get the list of the BPMs indices"""
		if not hasattr(self, '_bpm_numbers_list_'):
			self._bpm_numbers_list_ = list(map(lambda cav: cav.index, self.get_cavs_list()))
			
		return self._bpm_numbers_list_

	def get_cavs_list(self) -> List[Cavity]:
		"""Get the list of the Cavities in the beamline"""
		return list(filter(lambda element: element.type == "Cavity", self.lattice))

	def get_quads_list(self) -> List[Quadrupole]:
		"""Get the list of the Quadrupoles in the beamline"""
		return list(filter(lambda element: element.type == "Quadrupole", self.lattice))

	def get_bpms_list(self) -> List[Bpm]:
		"""Get the list of the Bpms in the beamline"""
		return list(filter(lambda element: element.type == "Bpm", self.lattice))

	def get_drifts_list(self) -> List[Drift]:
		"""Get the list of the drifts in the beamline"""
		return list(filter(lambda element: element.type == "Drift", self.lattice))

	def get_dipoles_list(self) -> List[Dipole]:
		"""Get the list of the dipoles in the beamline"""
		return list(filter(lambda element: element.type == "Dipole", self.lattice))

	def _get_girder(self, girder_index) -> List:
		"""Get the list of the elements on the girder"""
		return list(filter(lambda element: element.girder == girder_index, self.lattice))

	def get_girder(self, girder_index) -> List:
		"""
		Get the list of the elements on the girder
		
		Girders numbering starts from 1
		"""
		return self.girders[girder_index]

	def _get_quads_strengths(self) -> List[float]:
		"""Get the list of the quadrupoles strengths | Created for the use with Placet.QuadrupoleSetStrengthList() """
		return list(map(lambda x: x.settings['strength'], self.get_quads_list()))

	def _get_cavs_gradients(self) -> List[float]:
		"""Get the list of the cavs gradients | Created for the use with Placet.CavitySetGradientList() """
		return list(map(lambda x: x.settings['gradient'], self.get_cavs_list()))

	def _get_cavs_phases(self) -> List[float]:
		"""Get the list of the cavs phases | Created for the use with Placet.CavitySetGradientList() """
		return list(map(lambda x: x.settings['phase'], self.get_cavs_list()))

	def to_placet(self, filename = None) -> str:
		"""
		Write the lattice in Placet readable format
		
		Paremeters
		----------
		filename: str, optional
			The name of the file to write the Placet lattice to.

		Returns
		-------
		str
			The string with the lattice in Placet readable format.
		"""
		res, current_girder_index = "Girder\n", 1
		
		for element in self.lattice:
			if element.girder == current_girder_index + 1:
				current_girder_index += 1
				res += "Girder\n"
			res += element.to_placet() + "\n"

		if filename is not None:
			with open(filename, 'w') as f:
				f.write(res)

		return res

	"""misallignments handling"""
	def read_misalignments(self, filename, **extra_params):
		"""
		Read the misalignments from the file

		The structure of the file should correspond to the lattice in the memory
		
		Paremeters
		----------
		filename: str
			Name of the file with the misalignment.

		Additional parameters
		---------------------
		cav_bpm: bool

		cav_grad_phas: bool
			

		"""
		if self.lattice == []:
			raise ValueError("Empty lattice")

		_to_float = lambda data: list(map(lambda x: float(x), data))

		with open(filename, 'r') as f:
			for i in range(len(self.lattice)):
				data = f.readline()
				if self.lattice[i].type == "Quadrupole":
					y, py, x, px, roll = _to_float(data.split())
					self.lattice[i].settings.update(dict(y = y, yp = py, x = x, xp = px, roll = roll))

				if self.lattice[i].type == "Cavity":
					res = {}
					if extra_params.get('cav_bpm', False) and extra_params.get('cav_grad_phas', False):
						y, py, x, px, bpm_offset_y, bpm_offset_x, grad, phase = _to_float(data.split())
						res = dict(y = y, yp = py, x = x, xp = px, gradient = grad, phase = phase, bpm_offset_y = bpm_offset_y, bpm_offset_x = bpm_offset_x)
					
					elif extra_params.get('cav_bpm', False):
						y, py, x, px, bpm_offset_y, bpm_offset_x = _to_float(data.split())
						res = dict(y = y, yp = py, x = x, xp = px, bpm_offset_y = bpm_offset_y, bpm_offset_x = bpm_offset_x)
					
					elif extra_params.get('cav_grad_phas', False):
						y, py, x, px, grad, phase = _to_float(data.split())
						res = dict(y = y, yp = py, x = x, xp = px, gradient = grad, phase = phase)
					else:
						y, py, x, px = _to_float(data.split())
						res = dict(y = y, yp = py, x = x, xp = px)

					self.lattice[i].settings.update(res)

				if self.lattice[i].type == "Bpm":
					y, py, x, px = _to_float(data.split())
					self.lattice[i].settings.update(dict(y = y, yp = py, x = x, xp = px))	

	def save_misalignments(self, filename, **extra_params):
		"""
		Write the misalignments to a file

		The structure of the file is the same to what is produced with Placet.SaveAllPositions
		
		Paremeters
		----------
		filename: str
			Name of the file with the misalignment.

		Additional parameters
		---------------------
		cav_bpm: bool

		cav_grad_phas: bool
			

		"""
		if self.lattice == []:
			raise ValueError("Empty lattice")
		res = ""
		with open(filename, 'w') as f:
			for element in self.lattice:
				res += f"{element.settings['y']} {element.settings['yp']} {element.settings['x']} {element.settings['xp']}"

				if element.type == "Quadrupole":
					res += f" {element.settings['roll']}"

				if element.type == "Cavity":
					if extra_params.get('cav_bpm', False) and extra_params.get('cav_grad_phas', False):
						res += f" {element.settings['bpm_offset_y']} {element.settings['bpm_offset_x']} {element.settings['gradient']} {element.settings['phase']}"
				res += "\n"
			f.write(res)

	def parse_beamline(self):
		"""
		Parse the Placet lattice file and read it to self.lattice

		Currently, can parse Quadrupole, Cavity, BPM, and Drift

		So far, not used, the need of this function is questionable
		"""
		parsed_beamline = []
		for element in self.lattice:
			if element['type'] == "Quadrupole":
				parsed_beamline.append(Quadrupole(element['settings'], element['girder'], element['index']))
			elif element['type'] == "Cavity":
				parsed_beamline.append(Cavity(element['settings'], element['girder'], element['index']))
			elif element['type'] == "Bpm":
				parsed_beamline.append(Bpm(element['settings'], element['girder'], element['index']))
			elif element['type'] == "Drift":
				parsed_beamline.append(Drift(element['settings'], element['girder'], element['index']))
			else:
				pass
		self.lattice = parsed_beamline

def parse_line(data, girder_index = None, index = None):
	"""
	Parse the line of the file with PLACET elements

	Parameters
	----------
	data: str
		The line from the PLACET file
	girder_index: optional
		The girder number of the current element
	index: optional
		The current element's id
	
	Returns
	-------
	Element_type, Element
		Element_type is either a value from Beamline._supported_elements, 'Girder' or None. None is returned when the line 
		does not contain any element (comment, set command, etc.)
		Element is the object of the corresponding type, if exists. In other case (girder, etc.) returns None.
	"""
	data_list, i, res = data.split(), 1, {}
	elem_type = data_list[0]
	if not elem_type in Beamline._supported_elements:
		return None, None
	while i < len(data_list):
		res[data_list[i][1:]] = data_list[i + 1]
		i += 2

	if elem_type == "Quadrupole":
		return "Quadrupole", Quadrupole(res, girder_index, index)

	if elem_type == "Cavity":
		return "Cavity", Cavity(res, girder_index, index)

	if elem_type == "Bpm":
		return "Bpm", Bpm(res, girder_index, index)

	if elem_type == "Drift":
		return "Drift", Drift(res, girder_index, index)
	
	if elem_type == "Dipole":
		return "Dipole", Dipole(res, girder_index, index)
	
	if elem_type == "Girder":
		return "Girder", None

	return None, None