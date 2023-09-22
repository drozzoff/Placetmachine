from pandas import DataFrame
import re
import shlex
from typing import List, Callable, Generator
import warnings

from .quadrupole import Quadrupole
from .cavity import Cavity
from .drift import Drift
from .bpm import Bpm
from .dipole import Dipole
from .multipole import Multipole
from .sbend import Sbend
from .element import Element


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

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
		- Remove the comments part from the line
			% .. -strength 95.0 # text.. -> .. -strength 95.0

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

	def parse(self, line: str):
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
			- Remove the comments part from the line
				% .. -strength 95.0 # text.. -> .. -strength 95.0
		..........
		Parameters
		----------
		line: str
			The string line to parse
		"""
		# Remove the comments
		line = re.sub(r'#.*', '', line)

		# Replace expressions with their evaluated results
		line = re.sub(r'(\S+)\s*\[expr\s(.*?)\]', self.evaluate_expression, line)

		# Replace other variables that appear in the format `-var $var`
		line = re.sub(r'(\S+)\s*\$(\w+)', lambda match: f"{match.group(1)} {self.replace_variables(match.group(2))}", line)

		# Update the variables dictionary if a 'set' command is found
		set_match = re.search(r'set (\w+) ([\d.]+)', line)
		if set_match:
			self.variables[set_match.group(1)] = set_match.group(2)
			line = ''
		
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
	cache_lattice_data(types)
		Cache up the data for certain types of the elements
	upload_from_cache(types, clear_cache = False, **extra_params)
		Restore the cached data for certain elements
	read_from_file(filename: str, **extra_params)
		Read the lattice from the Placet lattice file
	get_girders_number()
		Get the total number of the girders in the beamline
	quad_numbers_list()
		Get the list of the Quadrupoles indices
	cavs_numbers_list()
		Get the list of the Cavities indices
	bpms_numbers_list()
		Get the list of the BPMs indices
	get_cavs_list()
		Get the list of the Cavities in the beamline
	get_quads_list()
		Get the list of the Quadrupoles in the beamline
	get_bpms_list()
		Get the list of the Bpms in the beamline
	get_drifts_list()
		Get the list of the Drifts in the beamline
	get_dipoles_list()
		Get the list of the dipoles in the beamline
	get_sbends_list()
		Get the list of the dipoles in the beamline
	get_multipoles_list()
		Get the list of the dipoles in the beamline
	get_girder(girder_index)
		Get the list of the elements on the girder
	to_placet(filename = None)
		Convert the lattice to a Placet readable format
	read_misalignments(filename, **extra_params)
		Read the lattice misalignments from a file (same format Placet uses)
	save_misalignments(filename, **extra_params)
		Save the lattice misalingments to a file (same format Placet uses)
	parse_beamline()
		Parse the Placet lattice file and read it to Beamline.lattice
	"""

	_supported_elements = ["Girder", "Bpm", "Cavity", "Quadrupole", "Drift", "Dipole", "Sbend", "Multipole"]
	_parsers = ['advanced', 'default']

	def __init__(self, name: str):
		"""
		Parameters
		----------
		name: str
			Name of the beamline.
		"""
		self.name, self.lattice = name, []

	def __repr__(self):
		return f"Beamline('{self.name}') && lattice = {list(map(lambda x: repr(x), self.lattice))}"

	def __str__(self):
		_data_to_show = ['name', 'type', 'girder', 's', 'x', 'xp', 'y', 'yp']
		_settings_data = ['name', 's', 'x', 'xp', 'y', 'yp']
		data_dict = {key: [None] * len(self.lattice) for key in _data_to_show}
		for i in range(len(self.lattice)):
			for key in _settings_data:
				data_dict[key][i] = self.lattice[i].settings[key] if key in self.lattice[i].settings else None
			data_dict['type'][i] = self.lattice[i].type
			data_dict['girder'][i] = self.lattice[i].girder

		res_table = DataFrame(data_dict)
#		res_table.name = self.name
		
		return f"Beamline(name = '{self.name}', structure = \n{str(res_table)})"

	def __len__(self):
		return len(self.lattice)
	
	def append(self, element: Element, **extra_params):
		"""
		Append a given element at the end of the lattice.

		By default, places the element on the same girder as previous one. 
		If the previous one is not on the girder or this is the first element, the element is not placet on girder

		Parameters
		----------
		element: Element
			Element to append at the end of the sequence
		
		Additional parameters
		---------------------
		new_girder: bool, default False
			If True, places the element on a new girder. Otherwise places it on the same girder last element is placed.

			If False and there are no elements in the lattice, does not set any girder number (defaults to None)
		"""
		new_element = element.duplicate(element)
		if extra_params.get('new_girder', False):
			if self.lattice == []:
				new_element.girder = 1
			elif self.lattice[-1].girder is not None:
				girder_id = self.lattice[-1].girder
				new_element.girder = girder_id + 1
			else:
				warnings.warn("Cannot create a new girder when previous elements are not on girders!")
				new_element.girder = None
		else:
			if self.lattice == []:
				new_element.girder = None
			else:
				new_element.girder = self.lattice[-1].girder
		
		if self.lattice == []:
			new_element.settings['s'] = new_element.settings['length']
			new_element.index = 0
		else:
			new_element.settings['s'] = self.lattice[-1].settings['s'] + new_element.settings['length']
			new_element.index = self.lattice[-1].index + 1
		
		self.lattice.append(new_element)

	def at(self, element_id: int):
		"""
		Return the element at a given location
		
		Parameters
		----------
		element_id: int
			The id of the element
		
		Returns
		-------
		Element
			Element at the given location
		"""
		if element_id > len(self.lattice):
			raise IndexError(f"The number of elements in the lattice {len(self.lattice)}, the id received {element_id}")
		if element_id < 0:
			raise IndexError("Element index cannot be negative")

		return self.lattice[element_id]

	def __setitem__(self, index: int, value: Element):
		self.lattice[index] = value

	def __getitem__(self, index: int):
		return self.lattice[index]
	
	def __iter__(self):
		self._iter_index = 0
		return self

	def __next__(self):
		if not hasattr(self, '_iter_index'):
			self._iter_index = 0
		
		if self._iter_index < len(self.lattice):
			res = self.lattice[self._iter_index]
			self._iter_index += 1
			return res
		else:
			raise StopIteration

	def _verify_supported_elem_types(self, types: List[str]):
		if types is None:
			return None
		for elem_type in types:
			if elem_type not in self._supported_elements:
				raise ValueError(f"Unsupported element type - {elem_type}")
		return True

	def cache_lattice_data(self, types: List[str]):
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

	def upload_from_cache(self, types: List[str], clear_cache = False, **extra_params):
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
				line, processed_line = line.strip('\n'), None
				if debug_mode:
					print(f"#{__line_counter}. Read: '{line}'")
					__line_counter += 1
					if parser == "advanced":
						processed_line = preprocess_func(line)
						print(f"---Parsed: '{processed_line}'")
				else:
					processed_line = preprocess_func(line)
				elem_type, element = parse_line(processed_line, girder_index, index)

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

	def get_cavs_list(self) -> Generator[Cavity, None, None]:
		"""Get the Cavities from the lattice"""
		for element in self.lattice:
			if element.type == "Cavity":
				yield element

	def get_quads_list(self) -> Generator[Quadrupole, None, None]:
		"""Get the Quadrupoles from the lattice"""
		for element in self.lattice:
			if element.type == "Quadrupole":
				yield element

	def get_bpms_list(self) -> Generator[Bpm, None, None]:
		"""Get the Bpms from the lattice"""
		for element in self.lattice:
			if element.type == "Bpm":
				yield element

	def get_drifts_list(self) -> Generator[Drift, None, None]:
		"""Get the Drifts from the lattice"""
		for element in self.lattice:
			if element.type == "Drift":
				yield element

	def get_dipoles_list(self) -> Generator[Dipole, None, None]:
		"""Get the Dipoles from the lattice"""
		for element in self.lattice:
			if element.type == "Dipole":
				yield element

	def get_sbends_list(self) -> Generator[Sbend, None, None]:
		"""Get the Sbend from the lattice"""
		for element in self.lattice:
			if element.type == "Sbend":
				yield element

	def get_multipoles_list(self) -> Generator[Multipole, None, None]:
		"""Get the Multipoles from the lattice"""
		for element in self.lattice:
			if element.type == "Multipole":
				yield element

	def get_girder(self, girder_index) -> Generator[Element, None, None]:
		"""Get the elements on the girder"""
		for element in self.lattice:
			if element.girder == girder_index:
				yield element

	def _get_quads_strengths(self) -> List[float]:
		"""Get the list of the quadrupoles strengths | Created for the use with Placet.QuadrupoleSetStrengthList() """
		return list(map(lambda x: x.settings['strength'], self.get_quads_list()))

	def _get_cavs_gradients(self) -> List[float]:
		"""Get the list of the cavs gradients | Created for the use with Placet.CavitySetGradientList() """
		return list(map(lambda x: x.settings['gradient'], self.get_cavs_list()))

	def _get_cavs_phases(self) -> List[float]:
		"""Get the list of the cavs phases | Created for the use with Placet.CavitySetGradientList() """
		return list(map(lambda x: x.settings['phase'], self.get_cavs_list()))

	'''Misalignment routines'''
	def misalign_element(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element given by the element_index.

		An alternative is to individually apply the misalignment
			>>> for element in beamline:
			>>> 	element.settings['x'] += delta_x
		
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

		"""
		_options = ['x', 'xp', 'y', 'yp', 'roll']
		
		try:
			elem_id = extra_params.get('element_index')
		except KeyError:
			print("Element number is not given")
			return

		offsets_dict = _extract_dict(_options, extra_params)
		for key in offsets_dict:
			self.lattice[elem_id].settings[key] += offsets_dict[key]

	def misalign_elements(self, **extra_params):
		"""
		Apply the geometrical misalignments to several elements

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
		"""
		_options = []
		
		if not 'offset_data' in extra_params:
			raise Exception("'offset_data' is not given")
		
		elements = extra_params.get('offset_data')
		for element in elements:
			self.misalign_element(element_index = int(element), **elements[element], **_extract_dict(_options, extra_params))

	def misalign_girder_2(self, **extra_params):
		"""
		Misalign the girder by means of moving its end points
		
		Additional parameters
		---------------------
		girder: int
			The id of the girder
		x_right: float default 0.0
			The horizontal offset in micrometers of right end-point
		y_right: float default 0.0
			The vertical offset in micrometers of the right end-point
		x_left: float default 0.0
			The horizontal offset in micrometers of left end-point
		y_left: float default 0.0
			The vertical offset in micrometers of the left end-point
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		"""
		# Check the correctness of the types
		filter_types = extra_params.get('filter_types', None)
		if filter_types is not None:
			for element in filter_types:
				if element == 'Girder':
					raise ValueError(f"Incorrect element type '{element}'! Accepted types are {self._supported_elements} except 'Girder'!")
				elif not element in self._supported_elements:
					raise ValueError(f"Incorrect element type '{element}'! Accepted types are {self._supported_elements} except 'Girder'!")
		girder_start, girder_end = None, None

		#evaluating the dimenstions of the girder
		for element in self.get_girder(extra_params.get('girder')):
			if girder_start is None:
				girder_start = element.settings['s'] - element.settings['length']
			
			girder_end = element.settings['s']

		girder_length = girder_end - girder_start

		for element in self.get_girder(extra_params.get('girder')):
			element_center = element.settings['s'] - element.settings['length'] / 2
			
			# misaligning the left end-point
			x = extra_params.get('x_left', 0.0) * (girder_end - element_center) / girder_length
			y = extra_params.get('y_left', 0.0) * (girder_end - element_center) / girder_length
			
			# misaligning the right end-point
			x += extra_params.get('x_right', 0.0) * (element_center - girder_start) / girder_length
			y += extra_params.get('y_right', 0.0) * (element_center - girder_start) / girder_length
			if filter_types is not None:
				if not element.type in filter_types:
					continue
			self.misalign_element(element_index = element.index, x = x, y = y)

	def misalign_girder(self, **extra_params):
		"""
		Offset the girder along with the elements on it.

		All the elements on the girder are equally misaligned.

		Additional parameters
		---------------------
		girder: int
			The id of the girder
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		x: float default 0.0
			The horizontal offset in micrometers
		y: float default 0.0
			The vertical offset in micrometers
		"""
		_options = ['x', 'y']

		x, y = extra_params.get('x'), extra_params.get('y')
		self.misalign_girder_2(x_left = x, x_right = x, y_left = y, y_right = y, filter_types = extra_params.get('filter_types', None))

	def misalign_articulation_point(self, **extra_params):
		"""
		Offset the articulation point either between 2 girders or at the beamline start/end.

		The girders and elements on them are misalligned accordingly.

		Additional parameters
		---------------------
		girder_left: int, optional
			The id of the girder to the left of the articulation point
		girder_right: int, optional
			The id of the girder to the roght of the articulation point
		x: float, default 0.0
			The horizontal offset in micrometers
		y: float, default 0.0
			The vertical offset in micrometers
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
			
		There is an option to provide the ids of the girders to the right and to the left of the articulation point.
		That require girder_right - girder_left = 1, otherwise an exception will be raised.

		It is possible to provide only 1 id either of the right or the left one. This also works for the start/end of the beamline

		"""
		_options = ['x', 'y']

		# Check the correctness of the types
		filter_types = extra_params.get('filter_types', None)
		if filter_types is not None:
			for element in filter_types:
				if element == 'Girder':
					raise ValueError(f"Incorrect element type '{element}'! Accepted types are {self._supported_elements} except 'Girder'!")
				elif not element in self._supported_elements:
					raise ValueError(f"Incorrect element type '{element}'! Accepted types are {self._supported_elements} except 'Girder'!")

		N_girders = self.get_girders_number()

		girder_left, girder_right = extra_params.get('girder_left', None), extra_params.get('girder_right', None)
		
		if girder_left is not None and girder_right is not None and girder_right - girder_left != 1:
			raise ValueError("The girders provided do not have a common articulation point.")

		if girder_left is not None:
			if girder_left < 1 or girder_left > N_girders:
				raise ValueError(f"A girder with {girder_left} id does not exist!")
		
		if girder_right is not None:
			if girder_right < 1 or girder_right > N_girders:
				raise ValueError(f"A girder with {girder_right} id does not exist!")

		if girder_right is not None:
			girder_left = girder_right - 1 if girder_right != 1 else None
		
		elif girder_left is not None:
			girder_right = girder_left + 1 if girder_left != N_girders else None

		if girder_left is not None:
			# misalign the girder_left from the right
			self.misalign_girder_2(**{
				'girder': girder_left,
				'x_right': extra_params.get('x', 0.0),
				'y_right': extra_params.get('y', 0.0),
				'filter_types': filter_types
			})

		if girder_right is not None:
			self.misalign_girder_2(**{
				'girder': girder_right,
				'x_left': extra_params.get('x', 0.0),
				'y_left': extra_params.get('y', 0.0),
				'filter_types': filter_types
			})

	def misalign_girders(self, **extra_params):
		"""
		Misalign the girders according to the dictionary

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
		filter_types: list(Element), optional
			The types of elements to apply the misalignments to
			By default, the misalignments are applied to all the elements on the girder
		"""
		if not 'offset_data' in extra_params:
			raise Exception("'offset_data' is missing")

		_options = ['filter_types']

		girders = extra_params.get('offset_data')
		for girder in girders:
			self.misalign_girder(girder = int(girder), **girders[girder], **_extract_dict(_options, extra_params))

	def to_placet(self, filename: str = None) -> str:
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
	def read_misalignments(self, filename: str, **extra_params):
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

				if self.lattice[i].type == "Dipole":
					strength_y, strength_x = _to_float(data.split())
					self.lattice[i].settings.update(dict(strength_x = strength_x, strength_y = strength_y))

				if self.lattice[i].type == "Multipole" or self.lattice[i].type == "Sbend" or self.lattice[i].type == "Drift":
					y, py, x, px = _to_float(data.split())
					self.lattice[i].settings.update(dict(y = y, yp = py, x = x, xp = px))

	def save_misalignments(self, filename: str, **extra_params):
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
				if element.type in ["Quadrupole", "Cavity", "Bpm", "Drift", "Multipole", "Sbend"]:
					res += f"{element.settings['y']} {element.settings['yp']} {element.settings['x']} {element.settings['xp']}"

					if element.type == "Quadrupole":
						res += f" {element.settings['roll']}"

					if element.type == "Cavity":
						if extra_params.get('cav_bpm', True) and extra_params.get('cav_grad_phas', True):
							res += f" {element.settings['bpm_offset_y']} {element.settings['bpm_offset_x']} {element.settings['gradient']} {element.settings['phase']}"
				
				if element.type == "Dipole":
					res += f"{element.settings['strength_y']} {element.settings['strength_x']}"
				res += "\n"
			f.write(res)

def parse_line(data: str, girder_index: int = None, index: int = None):
	"""
	Parse the line of the file with PLACET elements.

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
	if data == '':
		return None, None

	pattern = r'(\w+)((?:\s+-\w+\s*(?:\S+|"[^"]*")?)*)'
	match = re.match(pattern, data)

	if not match:
		raise ValueError("Invalid line format")

	elem_type = match.group(1)
	remaining = match.group(2)
#	print(elem_type, remaining)
	if not elem_type in Beamline._supported_elements:
		warnings.warn(f"Element '{elem_type}' is not supported and is ignored. The list of supported elements is {Beamline._supported_elements}.")
		return None, None

	res = {}
	if remaining is not None:
		# Splits the remaining string into parts
		parts = shlex.split(remaining)
		for i in range(len(parts)):
			if parts[i].startswith('-'):
				if i == len(parts) - 1 or (parts[i+1].startswith('-') and parts[i+1][1].isalpha()):
					continue
				else:
					param = parts[i].strip('-')
					value = parts[i+1].strip('"')
					res[param] = value

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
	
	if elem_type == "Sbend":
		return "Sbend", Sbend(res, girder_index, index)

	if elem_type == "Multipole":
		return "Multipole", Multipole(res, girder_index, index)

	if elem_type == "Girder":
		return "Girder", None

	return None, None