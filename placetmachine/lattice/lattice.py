from pandas import DataFrame
import re
import shlex
from typing import List, Callable, Generator, Optional, Union
import warnings
from placetmachine.lattice import Quadrupole, Cavity, Drift, Bpm, Dipole, Multipole, Sbend, Element, Knob, Girder


_extract_subset = lambda _set, _dict: list(filter(lambda key: key in _dict, _set))
_extract_dict = lambda _set, _dict: {key: _dict[key] for key in _extract_subset(_set, _dict)}

class AdvancedParser:
	"""
	A class to do the advances parsing of the Placet lattice.

	Can perform the following measures:
	
	- Read and remember values that are set.

	    `% set tmp 5`

	- Put the value instead of the variable.
	    1. `% .. -strength expr [0.5*$e0] .. ` -> `% .. -strength expr [0.5*190.0] .. `
	    2. `% .. -e0 $e_initial .. ` -> ` .. -e0 190.0 .. `
	- Evaluate the values inside of the `expr` call.

	    `% .. -strength expr [0.5*190.0] .. ` -> `% .. -strength 95.0 .. `

	- Remove the comments part from the line.

	    `% .. -strength 95.0 # text.. ` -> `% .. -strength 95.0 `

	Attributes
	----------
	variables : dict
		Contains the values associated with the variables.

		Can be declared upon `AdvanceParser` instance initiation. It also gets
		automatically extended in the parsing process.

	"""
	def __init__(self, **variables_list):
		"""
		Accepts any keyword arguments in `variables_list`. These values are going to be kept in `variables` attribute.

		Can be used to globally modify certain parameters in the beamline, eg. energy (`e0`).
		"""
		self.variables = variables_list

		#making sure, everyhting is str:
		self.variables = {key: str(self.variables[key]) for key in self.variables}

	def replace_variables(self, var: str) -> str:
		"""
		Replace the input variable by the corresponding value stored in the 
		memory (`variables` attribute).
		
		If variable does not exist, sets it to `'0'`.

		Parameters
		----------
		var
			The variable to transform.
		
		Returns
		-------
		str
			The value corresponding to the variable.
		"""
		if var not in self.variables:
			warnings.warn(f"Variable '{var}' is missing. It is assigned to '0'.")
			self.variables[var] = "0"

		return self.variables[var]

	def evaluate_expression(self, match: str) -> str:
		"""
		Evaluate the expression from inside of a Tcl form `expr [..]`.

		Parameters
		----------
		match
			An expression to evaluate.
		
		Returns
		-------
		str
			Evaluated value.
		"""
		parameter = match.group(1)
		expression_with_vars = match.group(2)
		
		# Replace variables with their values
		expression = re.sub(r'\$(\w+)', lambda match: self.replace_variables(match.group(1)), expression_with_vars)

		result = eval(expression)
		return f"{parameter} {result}"

	def parse(self, line: str) -> str:
		"""
		Parse the line. Returns the line after applied transformations.

		Automatically performs the following:
	
		- Read and remember values that are set.

		    `% set tmp 5`

		- Put the value instead of the variable.
		    1. `% .. -strength expr [0.5*$e0] .. ` -> `% .. -strength expr [0.5*190.0] .. `
		    2. `% .. -e0 $e_initial .. ` -> ` .. -e0 190.0 .. `
		- Evaluate the values inside of the `expr` call.

		    `% .. -strength expr [0.5*190.0] .. ` -> `% .. -strength 95.0 .. `

		- Remove the comments part from the line.

		    `% .. -strength 95.0 # text.. ` -> `% .. -strength 95.0 `

		Parameters
		----------
		line
			The string line to parse.
		
		Returns
		-------
		str
			The parsed line.
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

class Beamline:
	"""
	A class used to store the beamline lattice.

	Fully compatible with **Placet** and can be imported from **Placet** lattice.

	The element types it supports:
	```
	["Bpm", "Cavity", "Quadrupole", "Drift", "Dipole", "Sbend", "Multipole"]
	```
	
	The class `Beamline` is iterative and elements in the lattice in the beamline
	can be accessed as in the normal `list`.
	
	**Parsers:**
	There are 2 parsers in the `Beamline` that allow to parse the Placet lattice:
	```
	["default", "advanced"]
	```

	- The `"default"` expects the lattice to be well structured with no variables or expressions.
	
	- The `"advanced"` can parse the variables, expressions and keep the variables in memory.
		See [AdvancedParser][placetmachine.lattice.lattice.AdvancedParser].

	Attributes
	----------
	name : str
		Name of the beamline.
	lattice : List[Element]
		The list of the elements forming the beamline.
	attached_knobs : List[Knob]
		The list of the knobs references that are associated with the `Beamline`
	girders : List[Girder]
		The list of the girders references that are the parts of the `Beamline`.
	"""

	_supported_elements = ["Girder", "Bpm", "Cavity", "Quadrupole", "Drift", "Dipole", "Sbend", "Multipole"]
	_parsers = ['advanced', 'default']
	_alignment_parameters = ['x', 'xp', 'y', 'yp', 'roll', 'tilt']

	def __init__(self, name: str):
		"""
		Parameters
		----------
		name
			Name of the beamline.
		"""
		self.name, self.lattice, self.attached_knobs, self.girders = name, [], [], []

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
			data_dict['girder'][i] = self.lattice[i].girder.name

		res_table = DataFrame(data_dict)
#		res_table.name = self.name
		
		return f"Beamline(name = '{self.name}', structure = \n{str(res_table)})"

	def __len__(self):
		return len(self.lattice)
	
	def append(self, element: Element, **extra_params):
		"""
		Append a given element at the end of the lattice.

		By default, places the element on the same girder as previous one. 
		If the previous element is not on the girder or this is the first element, 
		the element is not placed on girder.

		**`append()` works by duplicating a given element and then appending it. 
		Thus, the original and the appended element do not share the same reference**.

		Also, the **girders numbering starts from 1**.

		Parameters
		----------
		element : Element
			Element to append at the end of the sequence.
		
		Other parameters
		----------------
		new_girder : bool
			If `True` (default is `False`), places the element on a new girder. 
			Otherwise places it on the same girder last element is placed.

			If `False` and there are no elements in the lattice, does not set any girder number 
			(defaults to `None`).
		"""
		new_element = element.duplicate(element)
		if extra_params.get('new_girder', False):
			if self.lattice == [] or self.girders != []:
				# lattice is empty or the girders' list is non empty -> Creating a new Girder with an element
				self.girders.append(Girder(new_element, name = f"{len(self.girders) + 1}"))
			else:
				# lattice is non empty and there are no girders present -> Warning
				warnings.warn("Cannot create a new girder when previous elements are not on girders!", category = RuntimeWarning)
				
		elif self.girders != []:
			# girders list is non empty -> placing element in the last Girder
			self.girders[-1].append(new_element)
		else:
			# girders list is empty
			pass

		# Updating indexing and long. position
		
		if self.lattice == []:
			new_element.settings['s'] = new_element.settings['length']
			new_element.index = 0
		else:
			new_element.settings['s'] = self.lattice[-1].settings['s'] + new_element.settings['length']
			new_element.index = self.lattice[-1].index + 1
		
		self.lattice.append(new_element)
		

	def __setitem__(self, index: int, element: Element):
		#
		# Set the given element at the given position
		#
		# The element is copied and placed on the same girder the element before it was.
		#
		new_element = element.duplicate(element)
		
		girder = self.lattice[index].girder
		if girder is not None:
			# finding the correct element on the girder
			for i, element in enumerate(girder.elements):
				if element is self.lattice[index]:
					girder.elements[i] = new_element
					new_element.girder = girder
		self.lattice[index] = new_element

	def __getitem__(self, index: int):
		return self.lattice[index]
	
	def __iter__(self):
		#
		# Return an iteratable object and reset iteration index
		#
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

	def _verify_supported_elem_types(self, types: Optional[List[str]] = None):
		if types is None:
			return None
		for elem_type in types:
			if elem_type not in self._supported_elements:
				raise ValueError(f"Unsupported element type - {elem_type}")
		return True

	def attach_knob(self, knob: Knob):
		"""
		Attach an existing knob to the lattice.

		The elements included in the knob should exist in the lattice.

		Parameters
		----------
		knob
			The knob to attach to the lattice.
		"""
		if knob in self.attached_knobs:
			warnings.warn(f"The knob already attached!")
		else:
			# Verifying the elements in the given Knob exist in the Beamline
			for element in knob.elements:
				if element not in self.lattice:
					warnings.warn(f"One or few elements used in the Knob are not present in this Beamline! Knob is not attached")
					return
			self.attached_knobs.append(knob)

	def realign_elements(self, specific_parameters: Optional[Union[str, List[str]]] = None):
		"""
		Perfectly realign all the elements `Beamline.lattice` by settings
		one or all of the the following parameters to zero:
		```
		['x', 'xp', 'y', 'yp', 'roll', 'tilt']
		```

		Parameters
		----------
		specific_parameters
			One or several parameters from `['x', 'xp', 'y', 'yp', 'roll', 'tilt']` to reset.
			The unspecified parameters are not going to be change.

			If not specified - all the parameters  in `['x', 'xp', 'y', 'yp', 'roll', 'tilt']`
			are reset.
		"""
		parameters_to_reset = []
		
		if isinstance(specific_parameters, str):
			parameters_to_reset.append(specific_parameters)
		
		if specific_parameters is None:
			parameters_to_reset = self._alignment_parameters
		
		if isinstance(specific_parameters, list):
			for parameter in specific_parameters:
				if parameter not in self._alignment_parameters:
					raise ValueError(f"Parameter '{parameter}' either cannot be reset or does not exist!")
				parameters_to_reset.append(parameter)

		
		for element in self.lattice:
			for parameter in parameters_to_reset:
				element.settings[parameter] = 0.0

	def cache_lattice_data(self, elements: List[Element]):
		"""
		Cache up the data for certain elements.
		
		Parameters
		----------
		elements
			The list of the elements' references to cache.
			Each element in the list must be present in the Beamline.
		"""
		lattice_set = set(self.lattice)
		for element in elements:
			if element not in lattice_set:
				raise ValueError(f"Given element is not present in the Beamline!")
			element.cache_data()

	def upload_from_cache(self, elements: List[Element], clear_cache: bool = False):
		"""
		Restore the cached data for certain elements.

		Parameters
		----------
		elements
			The list of the elements' references to restore the cache values.
			Each element in the list must be present in the `Beamline`.
		clear_cache
			If `True`, clears the cached data.
		"""
		lattice_set = set(self.lattice)
		for element in elements:
			if element not in lattice_set:
				raise ValueError(f"Given element is not present in the Beamline!")
			element.use_cached_data(clear_cache)

	def read_placet_lattice(self, filename: str, **extra_params):
		"""
		Read the lattice from the Placet lattice file.

		Girders numbering starts from 1.
		Evaluates the longitudinal coordinates while parsing the lattice. The coordinate `s` corresponds 
		to the element exit.

		Parameters
		----------
		filename
			Name of the file with the lattice.

		Other parameters
		----------------
		debug_mode : bool
			If True (default is `False`), prints all the information it reads and processes.
		parser : str
			Type of parser to be used. The available optics are `"default"` (default one) and `"advanced"`.
		parser_variables : {}
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
		"""
		Get the total number of the girders in the beamline
		
		Returns
		-------
		int
			The total number of girders in the lattice.
		"""
		return self.lattice[-1].girder

	def extract(self, element_types: Union[str, List[str]]) -> Generator[Element, None, None]:
		"""
		Extract certain element type from the lattice.

		Parameters
		----------
		element_types
			The types of elements to extract.
		
		Yields
		------
		Element
			Element that satisfy the selection criteria.
		"""

		if isinstance(element_types, str):
			element_types = [element_types]
			
		for element_type in element_types:
			if element_type not in self._supported_elements:
				raise ValueError(f"The element type '{element_type}' is not supported. Accepting only {self._supported_elements}!")

		for element in self.lattice:
			if element.type in element_types:
				yield element
	
	def quad_numbers_list(self) -> List[int]:
		"""Get the list of the Quadrupoles indices"""
		return [quad.index for quad in self.extract(['Quadrupole'])]

	def cavs_numbers_list(self) -> List[int]:
		"""Get the list of the Cavities indices"""
		return [quad.index for quad in self.extract(['Cavity'])]
	
	def bpms_numbers_list(self) -> List[int]:
		"""Get the list of the BPMs indices"""
		return [quad.index for quad in self.extract(['Bpm'])]

	def get_girder(self, girder_index: int, **extra_params) -> Generator[Element, None, None]:
		"""
		Get the element(s) located on the given girder.
		
		Parameters
		----------
		girder_id
			The girder's index in the list of girders list associated with the Beamline
		
		Other parameters
		----------------
		filter_types : Optional[List[str]]
			The types of elements to extract from the given girder.
		
		Yields
		------
		Element
			Element extracted from the girder.
		"""
		for element in self.girders[girder_index]:
			if element.type in extra_params.get("filter_types", self._supported_elements):
				yield element

	def _get_quads_strengths(self) -> List[float]:
		"""Get the list of the quadrupoles strengths | Created for the use with Placet.QuadrupoleSetStrengthList() """
		return [quad['strength'] for quad in self.extract(['Quadrupole'])]

	def _get_cavs_gradients(self) -> List[float]:
		"""Get the list of the cavs gradients | Created for the use with Placet.CavitySetGradientList() """
		return [cav['gradient'] for cav in self.extract(['Cavity'])]

	def _get_cavs_phases(self) -> List[float]:
		"""Get the list of the cavs phases | Created for the use with Placet.CavitySetGradientList() """
		return [cav['phase'] for cav in self.extract(['Cavity'])]

	'''Misalignment routines'''
	def misalign_element(self, **extra_params):
		"""
		Apply the geometrical misalignments to the element given by the element_index.

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
		_options = []
		
		if not 'offset_data' in extra_params:
			raise Exception("'offset_data' is not given")
		
		elements = extra_params.get('offset_data')
		for element in elements:
			self.misalign_element(element_index = int(element), **elements[element], **_extract_dict(_options, extra_params))

	def misalign_girder_general(self, **extra_params):
		"""
		Misalign the girder by means of moving its end points.
		
		Other parameters
		----------------
		girder : int
			The id of the girder. **Required**
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
		_options = ['x', 'y']

		x, y = extra_params.get('x', 0.0), extra_params.get('y', 0.0)
		self.misalign_girder_general(girder = extra_params.get("girder"), x_left = x, x_right = x, y_left = y, y_right = y, filter_types = extra_params.get('filter_types', None))

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
		_options = ['x', 'y']
		filter_types = extra_params.get('filter_types', None)
		
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
			self.misalign_girder_general(**{
				'girder': girder_left,
				'x_right': extra_params.get('x', 0.0),
				'y_right': extra_params.get('y', 0.0),
				'filter_types': filter_types
			})

		if girder_right is not None:
			self.misalign_girder_general(**{
				'girder': girder_right,
				'x_left': extra_params.get('x', 0.0),
				'y_left': extra_params.get('y', 0.0),
				'filter_types': filter_types
			})

	def misalign_girders(self, **extra_params):
		"""
		Misalign the girders according to the dictionary.

		Essentially, it is [`Beamline.misalign_girder`][placetmachine.lattice.lattice.Beamline.misalign_girder] function extended on many girders.
		That means the input data should have the same structure as the one passed to [`Beamline.misalign_girder`][placetmachine.lattice.lattice.Beamline.misalign_girder].
		
		*Maybe, instead Beamline.misalign_girder() it will be replaced with Beamline.misalign_girder_general().*

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
		if not 'offset_data' in extra_params:
			raise Exception("'offset_data' is missing")

		_options = ['filter_types']

		girders = extra_params.get('offset_data')
		for girder in girders:
			self.misalign_girder(girder = int(girder), **girders[girder], **_extract_dict(_options, extra_params))

	def to_placet(self, filename: Optional[str] = None) -> str:
		"""
		Write the lattice in Placet readable format.
		
		Parameters
		----------
		filename
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
		Read the misalignments from the file.

		The structure of the file should correspond to the lattice in the memory. Otherwise
		Placet is going to produce errors.
		
		Parameters
		----------
		filename
			Name of the file with the misalignments.

		Other parameters
		----------------
		cav_bpm : bool
			Check Placet manual.
		cav_grad_phas : bool
			Check Placet manual.
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
		Write the misalignments to a file.

		The structure of the file is the same to what is produced with [`Placet.SaveAllPositions`][placetmachine.placet.placetwrap.Placet.SaveAllPositions].
		
		Parameters
		----------
		filename
			Name of the file with the misalignment.

		Other parameters
		----------------
		cav_bpm : bool
			Check Placet manual.
		cav_grad_phas : bool
			Check Placet manual.
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

def parse_line(data: str, girder_index: Optional[int] = None, index: Optional[int] = None):
	"""
	Parse the line of the file with Placet elements.

	Parameters
	----------
	data
		The line from the PLACET file.
	girder_index
		The girder number of the current element.
	index
		The current element's id.
	
	Returns
	-------
	tuple(Optional[str], Optional[Element])
		The first value is either a value from `Beamline._supported_elements`, `"Girder"` or `None`. 
		`None` is returned when the line does not contain any element (for example it is a comment, set command, etc.)
		[`Element`][placetmachine.lattice.element.Element] is the object of the corresponding type, if exists. In other case (girder, etc.) returns None.
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