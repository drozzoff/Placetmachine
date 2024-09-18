from typing import List, Optional, Tuple
from pandas import DataFrame
import warnings
import copy
from placetmachine.lattice import Element


class Knob:
	"""
	A class used to create a Knob.

	A knob is a certain change in the beamline (elements offsets, strengths change, etc.)
	that is applied to modify change conditions like beam waist, dispersion or something
	more complex.

	So far the elements' types accepted for the knobs creation are [`Quadrupole`][placetmachine.lattice.quadrupole.Quadrupole]
	and [`Cavity`][placetmachine.lattice.cavity.Cavity].

	The `Knob` is going to store the references of the [`Element`][placetmachine.lattice.element.Element]s provided and use them to 
	apply the changes. Thus changes to the elements here are going to change the originals.
	
	If parameter ``step_size'' is provided, the coordinates modifications when using [`apply_knob'][placetmachine.lattice.knob.Knob.apply_knob]
	are adjusted towards the closest  number full of steps.

	Attributes
	----------
	elements : List[Element]
		List of the elements that used in this Knob.
	variables : List[dict]
		A list containing dictionaries that describe the changes that are performed to the elements when `Knob ` is
		applied. Number of elements in the list should be the same as the number of the elements. It contains the info
		on the amplitude for each coordinate to change for the given `Element` as well as the total accumulated changes,
		mismatches and step sizes.
		An example of the 
		dict that describes that `Element` must be moved vertically by 5.0 micron and horizontaly by -2.0 micron:
		```
		{
			'y': {
				'amplitude': 5.0,
				'change': 0.0,
				'step_size': 0.5,
				'mismatch': 0.0
			}
			'x': {
				'amplitude': -2.0,
				'change': 0.0
				'step_size': 0.5,
				'mismatch': 0.0
			}
		}
		```
		Both vertical and horizontal movers are anticipated to have a step size of 0.5 micron in this example. Also, 
		for each coordinate a mismatch and total accumnulated coordinate changes are kept.
	supported_amplitudes : Optional[List[float]]
		A list of the supported amplitudes. When provided, only the amplitudes from the list are applied. This list
		contains the amplitudes that an attribute `amplitude` can take. That means that amplitude given
		in  `Knob.apply()` is adjusted so that the sum `Knob.amplitude + amplitude` eqists in `supported_amplitudes`.
		Since, strategies, like `min_scale` and `min_scale_memory` have their own amplitude selection, attribute
		`supported_amplitudes` has no effect on them.
	amplitude_mismatch : float
		A mismatch between the amplitude requested and the amplitude applied. By default is `0.0`.
		It is modified when the `apply()` strategy foresees the automatic adjustment of the amplitude. So
		`amplitude_mismatch` accomodates this mismatch between multiple `apply()` calls.
	name : str
		Name of the Knob.
	types_of_elements : List[str]
		Types of the elements involved in the Knob.
	amplitude : float
		The current Knob amplitude.
	"""

	_cached_parameters = ['x', 'y', 'xp', 'yp']
	_accepted_types = ['Quadrupole', 'Cavity']
	_strategies_available = [None, "simple", "simple_memory", "min_scale", "min_scale_memory"]

	def __init__(self, elements: List[Element], knob_structure: List[dict], **extra_params):
		"""
		Parameters
		----------
		elements
			List of elements to be used for this `Knob`.
			Elements provided here must be the elements that are the part of the Beamline.
		knobs_structure
			A list containing info about the elements' amplitudes and step sizes. An example of such a list for
			a knob containing 2 elements:
			```
			[{'y':{'amplitude': 2.0, 'step_size': 0.5}}, {'x': {'amplitude': 2.5}, 'y': {'amplitude': -0.5}}]
			```
			Here, the first element has an amplitude `2.0` for the coordinate `y`, while the second element
			requires a combination of `x` and `y` changes of `2.5` and `-0.5` respectively.
		
		Other parameters
		----------------
		name : str
			The name of the knob. If not provided, defaults to "".
		supported_amplitudes : Optional[List[float]]
			A list of the supported amplitudes.
		"""
		if len(elements) != len(knob_structure):
			raise ValueError(f"The number of elements and values provided are different.")
	
		self.elements, self.types_of_elements, self.amplitude, self.amplitude_mismatch = elements, [], 0.0, 0.0
		self.name = extra_params.get('name', "")
		self.supported_amplitudes = extra_params.get("supported_amplitudes", None)
		self.variables = []

		# building variables

		for tmp in knob_structure:
			dict_tmp = {}
			for coord in tmp:
				if coord not in self._cached_parameters:
					raise ValueError(f"Incorrect coordinate. Acceptable are {self._cached_parameters}, received '{coord}'")
				dict_tmp[coord] = {
					'amplitude': tmp[coord]['amplitude'],
					'step_size': tmp[coord]['step_size'] if 'step_size' in tmp[coord] else None,
					'change': 0.0,
					'mismatch': 0.0
				}
				if dict_tmp[coord]['step_size'] == 0.0:
					dict_tmp[coord]['step_size'] = None

			self.variables.append(dict_tmp)
			

		# checking the supported types and building the types involved
		for i, element in enumerate(self.elements):
			if element.type not in self._accepted_types:
				raise TypeError(f"Inappropriate element type. Acceptable are {self._accepted_types}, received '{element.type}'")

			if element.type not in self.types_of_elements:
				self.types_of_elements.append(element.type)
		
			# storing the info about mismatches globally
			if not hasattr(element, '_mismatch'):
				element._mismatch = {}
				for coord in self.variables[i]:
					element._mismatch[coord] = 0.0
			else:
				for coord in self.variables[i]:
					if coord not in element._mismatch:
						element._mismatch[coord] = 0.0
	def reset(self):
		"""
		Reset the knob's data.
		
		It resets the knob to 0.0 amplitude. That means the elements' offsets changes done 
		by the knob are removed.
		Consequently resets the following attributes: `amplitude`, `mismatch`, and `changes`. 
		"""
		self.amplitude, self.amplitude_mismatch = 0.0, 0.0
		for i, element in enumerate(self.elements):
			for coord in self.variables[i]:
				element[coord] -= self.variables[i][coord]['change']
				element._mismatch[coord] -= self.variables[i][coord]['mismatch']

				self.variables[i][coord]['change'] = 0.0			
				self.variables[i][coord]['mismatch'] = 0.0


	def apply(self, amplitude: float, **kwargs):
		"""
		Apply the knob.

		Amplitude defines the fraction of the amplitudes of each individual coordinates to add to the 
		`elements`s involved in the `Knob`. If `step_size` is not defined (default), coordinate change 
		is applied directly. If `step_size` is defined, the actual coordinate change may be different
		from anticipated. This difference may also depend on the `strategy` used.

		Parameters
		----------
		amplitude
			Amplitude of the knob to apply.

		Other parameters
		----------------
		strategy : str
			Strategy to use for calculations of the offsets when the `step_size` is defined. Default is
			`None`. Possible options are:
			```
			[None, 'simple', 'simple_memory', 'min_scale', 'min_scale_memory']
			```
			If strategy is `None` all of the step sizes are ignored.
		use_global_mismatch : bool
			If `True` (default) coordinates' changes are evaluated to also compensate the possible mismatches
			caused by other knobs. Only applicable to the strategies that memorize the mismatches, such as:
			```
			['simple_memory', 'min_scale_memory']
			```
		"""
		strategy = kwargs.get("strategy", None)

		if strategy not in self._strategies_available:
			raise ValueError(f"Unacceptable apply strategy - '{strategy}'")
		
		if strategy is None:
			for i, element in enumerate(self.elements):
				for coord in self.variables[i]:
					element[coord] += self.variables[i][coord]['amplitude'] * amplitude
					self.variables[i][coord]['change'] += self.variables[i][coord]['amplitude'] * amplitude
			self.amplitude += amplitude

		if strategy == "simple":
			self.__appply_simple(amplitude)
		if strategy == "simple_memory":
			self.__apply_simple_memory(amplitude, use_global_mismatch = kwargs.get('use_global_mismatch', True))
		if strategy == "min_scale":
			self.__apply_min_scale(amplitude)
		if strategy == "min_scale_memory":
			self.__apply_min_scale_memory(amplitude, use_global_mismatch = kwargs.get('use_global_mismatch', True))

	def cache_state(self):
		"""
		Save the current knobs' state into the cache.

		It saves the changes applied by the knob so it could be restored later.
		Attributes to be cached:
		```
		[`amplitude`, `amplitude_mismatch`, `changes`, `mismatch`]
		```
		"""
		self._cached_data = {
			'amplitude': self.amplitude,
			'amplitude_mismatch': self.amplitude_mismatch,
			'variables': copy.deepcopy(self.variables)
		}
	
	def upload_state_from_cache(self, clear_cache: bool = False):
		"""
		Upload the knob's data from the cache.

		Attributes to be upload:
		```
		[`amplitude`, `amplitude_mismatch`, `changes`, `mismatch`]
		```
		As these values are uploaded - elements' offsets are adjusted correspondingly.

		Parameters
		----------
		clear_cache
			If `True` clears the cached data.
		"""
		if not hasattr(self, '_cached_data'):
			warnings.warn(f"Cannot upload, cache is empty!")
			return 
		elif self._cached_data is None:
			warnings.warn(f"Cannot upload, cache is empty!")
			return 

		for i, element in enumerate(self.elements):
			for coord in self.variables[i]:
				element[coord] += self._cached_data['variables'][i][coord]['change'] - self.variables[i][coord]['change']
				element._mismatch[coord] += self._cached_data['variables'][i][coord]['mismatch'] - self.variables[i][coord]['mismatch']

		self.amplitude = self._cached_data['amplitude']
		self.amplitude_mismatch = self._cached_data['amplitude_mismatch']
		
		self.variables = copy.deepcopy(self._cached_data['variables'])

		if clear_cache:
			self._cached_data = None

	def __appply_simple(self, amplitude, **extra_params):
		"""
		Apply the the knob.

		The offsets to apply are evaluated by rounding the offsets' amplitude.
		Is prone to accumulating the missmatches of the knobs offsets.

		If `supported_amplitudes` is provided, it takes the closest value such that
		`amplitude + Knob.amplitude` exist in the `Knob.supported_amplitudes` and 
		applies it. The difference between the applied and requested amplitudes is 
		added to `amplitude_mismatch` attribute.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.

		Other parameters
		----------------
		ignore_supported_amplitudes : bool
			If `True` (default is `False`) ignores the `supported_amplitudes` attribute even if present.
		
		"""
		amplitude_tmp = amplitude + self.amplitude # absolute amplitude currently
		# evaluating the amplitude to apply from the list
		if self.supported_amplitudes is not None and not extra_params.get('ignore_amplitudes_list', False):
			for i, amp in enumerate(self.supported_amplitudes):
				if amp > amplitude_tmp:
					if amp - amplitude_tmp <= amplitude_tmp - self.supported_amplitudes[i - 1]:
						amplitude_tmp = amp
					else:
						amplitude_tmp = self.supported_amplitudes[i - 1]
					
					break
			
			self.amplitude_mismatch += amplitude + self.amplitude - amplitude_tmp

		amplitude = amplitude_tmp - self.amplitude # new amplitude to apply

		for i, element in enumerate(self.elements):
			for coord in self.variables[i]:
				coord_amplitude = self.variables[i][coord]['amplitude']
				coord_step_size = self.variables[i][coord]['step_size']

				coord_change = coord_amplitude * amplitude

				if coord_step_size is not None:
					n_step_sizes = int(coord_change / coord_step_size)

					new_coord_change = None
					if abs(coord_change - n_step_sizes * coord_step_size) < 0.5 * coord_step_size:
						new_coord_change = n_step_sizes * coord_step_size
					else:
						if coord_change > 0:
							new_coord_change = (n_step_sizes + 1) * coord_step_size
						else:
							new_coord_change = (n_step_sizes - 1) * coord_step_size

					# updating the values
					self.variables[i][coord]['change'] += new_coord_change

					old_mismatch = self.variables[i][coord]['mismatch']

					self.variables[i][coord]['mismatch'] = coord_amplitude * (self.amplitude + amplitude) - self.variables[i][coord]['change']

					# mismatch is accumulated with respect to the individual elements
					element._mismatch[coord] += self.variables[i][coord]['mismatch'] - old_mismatch

					element[coord] += new_coord_change
				else:
					element[coord] += coord_change
					self.variables[i][coord]['change'] += coord_change

		self.amplitude += amplitude

	def __apply_simple_memory(self, amplitude: float, **extra_params):
		"""
		Apply the the knob.

		The offsets to apply are evaluated by rounding the offsets' amplitude taking 
		into account also the the accumulated mismatch. It also takes into account the 
		present amplitude mismatch `Knob.amplitude_mismatch`.

		If `supported_amplitudes` is provided, it takes the closest value such that
		`amplitude + Knob.amplitude` exist in the `knob.supported_amplitudes` and 
		applies it. The difference between the applied and requested amplitudes is 
		added to `amplitude_mismatch` attribute.

		Parameters
		----------
		amplitude
			Amplitude of the knob to apply.

		Other parameters
		----------------
		ignore_supported_amplitudes : bool
			If `True` (default is `False`) ignores the `supported_amplitudes` attribute even if present.
		use_global_mismatch : bool
			If `True` (default) coordinates' changes are evaluated to also compensate the possible mismatches
			caused by other knobs.
		"""
		# absolute amplitude expected
		amplitude_tmp = amplitude + self.amplitude + self.amplitude_mismatch
		
		# evaluating the amplitude to apply from the list
		if self.supported_amplitudes is not None and not extra_params.get('ignore_supported_amplitudes', False):
			for i, amp in enumerate(self.supported_amplitudes):
				if amp > amplitude_tmp:
					if amp - amplitude_tmp < amplitude_tmp - self.supported_amplitudes[i - 1]:
						amplitude_tmp = amp
					else:
						amplitude_tmp = self.supported_amplitudes[i - 1]
					
					break
			
			self.amplitude_mismatch += amplitude + self.amplitude - amplitude_tmp

		amplitude = amplitude_tmp - self.amplitude # new amplitude to apply
		
		for i, element in enumerate(self.elements):
			for coord in self.variables[i]:
				coord_amplitude = self.variables[i][coord]['amplitude']
				coord_step_size = self.variables[i][coord]['step_size']

				coord_change = coord_amplitude * amplitude
				coord_change += element._mismatch[coord] if extra_params.get('use_global_mismatch', True) else self.variables[i][coord]['mismatch']

				if coord_step_size is not None:
					n_step_sizes = int(coord_change / coord_step_size)
					
					new_coord_change = None
					if abs(coord_change - n_step_sizes * coord_step_size) < 0.5 * coord_step_size:
						new_coord_change = n_step_sizes * coord_step_size
					else:
						if coord_change > 0:
							new_coord_change = (n_step_sizes + 1) * coord_step_size
						else:
							new_coord_change = (n_step_sizes - 1) * coord_step_size

					# updating the values
					self.variables[i][coord]['change'] += new_coord_change

					old_mismatch = self.variables[i][coord]['mismatch']
					self.variables[i][coord]['mismatch'] = coord_amplitude * (self.amplitude + amplitude) - self.variables[i][coord]['change']

					# mismatch is accumulated with respect to the individual elements
					element._mismatch[coord] += self.variables[i][coord]['mismatch'] - old_mismatch

					element[coord] += new_coord_change
				else:
					element[coord] += coord_change
					self.variables[i][coord]['change'] += coord_change
		
		self.amplitude += amplitude

	def __evaluate_sensitive_coordinate(self) -> Tuple[Optional[int], Optional[str]]:
		"""
		Evaluate the most sensitive coordinate and element by checking the relation between
		their absolute amplitudes and step sizes. The smaller value is - the more sensitive
		the element/coordinate is.

		Returns
		-------
		The id of the element and the coordinate of the most sensitive point. If no such found
		(eg. no step sizes defined) returns `None, None`.
		"""
		# evaluating the smallest coord change wrt to the corresponding step size
		coords_list = []
		for variable in self.variables:
			for coord in variable:
				if coord not in coords_list:
					coords_list.append(coord)

		coord_to_scale, i_min, tmp = None, -1, None
		for coord in coords_list:
			abs_coord_values = list(map(lambda x: abs(x[coord]['amplitude'] / x[coord]['step_size']) if 'step_size' in x[coord] else None, self.variables))
			abs_coord_values_filtered = filter(lambda x: x is not None, abs_coord_values)
			if abs_coord_values_filtered == []:
				# the following coordinate has no step size
				continue
			
			min_value = min(abs_coord_values_filtered)
			if (tmp is not None and min_value < tmp) or tmp is None:
				coord_to_scale = coord
				tmp = min_value
				i_min = abs_coord_values.index(min_value)
		
		return i_min, coord_to_scale

	def __apply_min_scale(self, amplitude):
		"""
		Apply the the knob.

		The offsets are evaluated the following way:
		1. The minimum offset is evalued among all the elements. For instance, lets take
			the smallest offset amplitude is 1.0 $\mu$m, step size of 0.5 $\mu$m, and the knob
			amplitude of 0.6. The rounded smallest offsets is goint to be 0.5.
		2. We take the smallest rounded offset and evaluate the offsets of the other elements by
			scalling the offset amplitudes correspondingly. These offsets are also rounded to 
			the closest value proportional to the step size.

		As a result of such adjustemnt - amplitude applied may differ from the amplitude
		passed.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.
		"""

		i_min, coord_to_scale = self.__evaluate_sensitive_coordinate()

		if coord_to_scale is None:
			# none of the coordinates have a step size
			warnings.warn(f"There are no step sizes associated with current knob. Running apply() with `strategy = None`.")
			self.apply(amplitude, strategy = None)
			return

		coord_amplitude = self.variables[i_min][coord_to_scale]['amplitude']
		coord_stepsize = self.variables[i_min][coord_to_scale]['step_size']
		
		coord_change_ref = coord_amplitude * amplitude
		
		n_step_sizes_ref = int(coord_change_ref / coord_stepsize)
		
		ref_offset = None
		if abs(coord_change_ref - n_step_sizes_ref * coord_stepsize) < 0.5 * coord_stepsize:
			ref_offset = n_step_sizes_ref * coord_stepsize
		else:
			if coord_change_ref > 0:
				ref_offset = (n_step_sizes_ref + 1) * coord_stepsize
			else:
				ref_offset = (n_step_sizes_ref - 1) * coord_stepsize

		amplitude_adjusted = ref_offset / coord_amplitude

		self.__appply_simple(amplitude_adjusted, ignore_supported_amplitudes = True)

		self.amplitude_mismatch += amplitude - amplitude_adjusted
		
	def __apply_min_scale_memory(self, amplitude, **extra_params):
		"""
		Apply the the knob.

		The offsets are evaluated the following way:
		1. The minimum offset is evalued among all the elements. For instance, lets take
			the smallest offset amplitude is 1.0 $\mu$m, step size of 0.5 $\mu$m, and the knob
			amplitude of 0.6. The rounded smallest offsets is goint to be 0.5.
		2. We take the smallest rounded offset and evaluate the offsets of the other elements by
			scalling the offset amplitudes correspondingly. These offsets are also rounded to 
			the closest value proportional to the step size.

		As a result of such adjustment - amplitude applied may differ from the amplitude
		passed.

		When evaluating the offsets, the mismatch between the current values and values
		expected by the amplitude are added. Also, the amplitude mismatch (difference between
		the `amplitude` provided to the function `Knob.amplitude`) is taken into accound.

		Parameters
		----------
		amplitude : float
			Amplitude of the knob to apply.

		Other parameters
		----------------
		use_global_mismatch : bool
			If `True` (default) coordinates' changes are evaluated to also compensate the possible mismatches
			caused by other knobs.
		"""

		i_min, coord_to_scale = self.__evaluate_sensitive_coordinate()
		
		if coord_to_scale is None:
			# none of the coordinates have a step size
			warnings.warn(f"There are no step sizes associated with current knob. Running apply() with `strategy = None`.")
			self.apply(amplitude, strategy = None)
			return

		coord_amplitude = self.variables[i_min][coord_to_scale]['amplitude']
		coord_stepsize = self.variables[i_min][coord_to_scale]['step_size']

		coord_change_ref = coord_amplitude * (amplitude + self.amplitude_mismatch)
		n_step_sizes_ref = int(coord_change_ref / coord_stepsize)
		
		ref_offset = None
		if abs(coord_change_ref - n_step_sizes_ref * coord_stepsize) < 0.5 * coord_stepsize:
			ref_offset = n_step_sizes_ref * coord_stepsize
		else:
			if coord_change_ref > 0:
				ref_offset = (n_step_sizes_ref + 1) * coord_stepsize
			else:
				ref_offset = (n_step_sizes_ref - 1) * coord_stepsize

		amplitude_adjusted = ref_offset / coord_amplitude
		# this could be different from the correct amplitude required:
		# which is amplitude + self.amplitude_mismatch
		self.amplitude_mismatch += amplitude - amplitude_adjusted

		for i, element in enumerate(self.elements):
			for coord in self.variables[i]:
				coord_amplitude = self.variables[i][coord]['amplitude']
				coord_step_size = self.variables[i][coord]['step_size']
				
				coord_change = coord_amplitude * amplitude_adjusted
				coord_change += element._mismatch[coord] if extra_params.get('use_global_mismatch', True) else self.variables[i][coord]['mismatch']

				n_step_sizes = int(coord_change / coord_step_size)
				
				new_coord_change = None
				if abs(coord_change - n_step_sizes * coord_step_size) < 0.5 * coord_step_size:
					new_coord_change = n_step_sizes * coord_step_size
				else:
					if coord_change > 0:
						new_coord_change = (n_step_sizes + 1) * coord_step_size
					else:
						new_coord_change = (n_step_sizes - 1) * coord_step_size

				self.variables[i][coord]['change'] += new_coord_change
				
				old_mismatch = self.variables[i][coord]['mismatch']
				
				self.variables[i][coord]['mismatch'] = coord_amplitude * (self.amplitude + amplitude_adjusted) - self.variables[i][coord]['change']
				
				element._mismatch[coord] += self.variables[i][coord]['mismatch'] - old_mismatch
				element[coord] += new_coord_change

		self.amplitude += amplitude_adjusted

	def to_dataframe(self) -> DataFrame:
		"""
		Return the DataFrame with the Knob data.

		The data included in the DataFrame is:
		```
		['name', 'type', 'girder', 's']
		```
		which is a name, type, girder id, and location of the element belonging to the girder.
		Plus the coordinate amplitude, current value in the beamline, coordinate change performed
		by the knob, and the mismatch when there is a finit step size:
		```
		['y_amplitude', 'y_current']
		```
		Typically, the properties, like `girder` or `s` are acquired during the [`Beamline`][placetmachine.lattice.lattice.Beamline]
		creation. When the knob is created on the isolated element, these properties are set to `None`.

		Returns
		-------
		DataFrame
			Knob data summary
		"""
		columns = ['name', 'type', 'girder', 's']
		
		# setting up the full list of the corodinates used in the 
		coords_list = []
		for tmp in self.variables:
			for coord in tmp:
				if coord not in coords_list:
					coords_list.append(coord)
		
		for coord in coords_list:
			columns += [f'{coord}_amplitude', f'{coord}_step_size', f'{coord}_current', f'{coord}_change', f'{coord}_mismatch', f'{coord}_total_mismatch']
		data_dict = {key: [] for key in columns}

		for i, element in enumerate(self.elements):
			data_dict['name'].append(element['name'])
			
			data_dict['s'].append(element['s'] if 's' in element.settings else None)

			data_dict['type'].append(element.type)
			data_dict['girder'].append(element.girder.name if element.girder is not None else None)

			for coord in self.variables[i]:
				step_size = self.variables[i][coord]['step_size']
				data_dict[f"{coord}_amplitude"].append(self.variables[i][coord]['amplitude'])
				data_dict[f"{coord}_step_size"].append(step_size if step_size is not None else '-')
				data_dict[f"{coord}_current"].append(element[coord])
				data_dict[f"{coord}_change"].append(self.variables[i][coord]['change'])
				data_dict[f"{coord}_mismatch"].append(self.variables[i][coord]['mismatch'])
				data_dict[f"{coord}_total_mismatch"].append(element._mismatch[coord])

		return DataFrame(data_dict)

	def __str__(self):
		
		return str(self.to_dataframe())

	__repr__ = __str__
