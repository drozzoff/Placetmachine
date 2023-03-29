import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pandas import DataFrame


from .quadrupole import Quadrupole
from .cavity import Cavity
from .drift import Drift
from .bpm import Bpm

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

def timing(func):

	def wrapper(*args, **kwargs):
		start = time.time()
		func(*args, **kwargs)
		print("Elapsed time = " + str(time.time() - start) + " s")

	return wrapper

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
				raise ValueError("Unsupported element type - " + str(elem_type))
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

	def read_from_file(self, filename):
		"""
		Read the lattice from the Placet lattice file

		Girders numbering starts from 1.
		Evaluates the longitudinal coordinates while parsing the lattice. The coordinate s corresponds to the element exit.

		Parameters
		----------
		filename: str
			Name of the file with the lattice

		"""
		girder_index, index = 0, 0
		with open(filename, 'r') as f:
			for line in f.readlines():
				elem_type, element = parse_line(line, girder_index, index)
				if elem_type == 'Girder':
					girder_index += 1
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
	def quad_numbers_list(self):
		"""Get the list of the Quadrupoles indices"""
		if not hasattr(self, '_quad_numbers_list_'):
			self._quad_numbers_list_ = list(map(lambda quad: quad.index, self.get_quads_list()))
			
		return self._quad_numbers_list_

	@property
	def cavs_numbers_list(self):
		"""Get the list of the Cavities indices"""
		if not hasattr(self, '_cav_numbers_list_'):
			self._cav_numbers_list_ = list(map(lambda cav: cav.index, self.get_cavs_list()))
			
		return self._cav_numbers_list_
	
	@property
	def bpms_numbers_list(self):
		"""Get the list of the BPMs indices"""
		if not hasattr(self, '_bpm_numbers_list_'):
			self._bpm_numbers_list_ = list(map(lambda cav: cav.index, self.get_cavs_list()))
			
		return self._bpm_numbers_list_

	def get_quads_numbers(self) -> list:
		"""Get the list of the BPMs indices"""
		return list(map(lambda quad: quad.index, self.get_quads_list()))

	def get_cavs_list(self) -> list:
		"""Get the list of the Cavities in the beamline"""
		return list(filter(lambda element: element.type == "Cavity", self.lattice))

	def get_quads_list(self) -> list:
		"""Get the list of the Quadrupoles in the beamline"""
		return list(filter(lambda element: element.type == "Quadrupole", self.lattice))

	def get_bpms_list(self) -> list:
		"""Get the list of the Bpms in the beamline"""
		return list(filter(lambda element: element.type == "Bpm", self.lattice))

	def get_drifts_list(self) -> list:
		"""Get the list of the elements on the girder"""
		return list(filter(lambda element: element.type == "Drift", self.lattice))

	def _get_girder(self, girder_index) -> list:
		"""Get the list of the elements on the girder"""
		return list(filter(lambda element: element.girder == girder_index, self.lattice))

	def get_girder(self, girder_index) -> list:
		"""
		Get the list of the elements on the girder
		
		Girders numbering starts from 1
		"""
		return self.girders[girder_index]

	def _get_quads_strengths(self) -> list:
		"""Get the list of the quadrupoles strengths | Created for the use with Placet.QuadrupoleSetStrengthList() """
		return list(map(lambda x: x.settings['strength'], self.get_quads_list()))

	def _get_cavs_gradients(self) -> list:
		"""Get the list of the cavs gradients | Created for the use with Placet.CavitySetGradientList() """
		return list(map(lambda x: x.settings['gradient'], self.get_cavs_list()))

	def _get_cavs_phases(self) -> list:
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
		assert self.lattice != [], "Empty lattice"

		_to_float = lambda data: list(map(lambda x: float(x), data))

		with open(filename, 'r') as f:
			for i in range(len(self.lattice)):
				data = f.readline()
#				print(self.lattice[i].type, data)
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
#	@timing
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
		assert self.lattice != [], "Empty lattice"
		res = ""
		with open(filename, 'w') as f:
			for element in self.lattice:
				res += str(element.settings['y']) + " " + str(element.settings['yp']) + " " + str(element.settings['x']) + " " + str(element.settings['xp'])

				if element.type == "Quadrupole":
					res += " " + str(element.settings['roll'])

				if element.type == "Cavity":
					if extra_params.get('cav_bpm', False) and extra_params.get('cav_grad_phas', False):
						res += " " + str(element.settings['bpm_offset_y']) + " " + str(element.settings['bpm_offset_x']) + " " + str(element.settings['gradient']) + " " + str(element.settings['phase'])
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

	def draw_beamline(self, plane = 'y', **extra_params):
		"""
		Draw the beamline

		Parameters
		----------
		plane: str, default 'y'
			Plane for the plot.

		Additional parameters
		---------------------
		offsets_only: bool, default False
			If True, only draws the elements that are mislaigned
		length_scale: float, default 1.0
			Scale the lengths of the elements accordingly
			Sometimes needed to better see the elements
		filename: str, optional
			If given, saves the plot to the given path
		"""
		_DEFAULT_HEIGHT = 5
		offsets_only, length_scale = extra_params.get("offsets_only", False), extra_params.get("length_scale", 1.0)
		def _get_absolute_orbit(plane = 'y'):
			bpms = list(filter(lambda element: element.type == "Bpm", self.lattice))
			s = list(map(lambda x: x.settings['s'], bpms))
			if plane == 'x':
				return s, list(map(lambda x: x.settings['x'] + x.settings['reading_x'], bpms))
			if plane == 'y':
				return s, list(map(lambda x: x.settings['y'] + x.settings['reading_y'], bpms))
		counter = 0
		with plt.style.context(['science', 'ieee']):
			fig = plt.figure()
			ax = fig.add_subplot(111)
			
			s, orbit = _get_absolute_orbit(plane)

			#reference line
			plt.plot(s, [0.0] * len(s), linewidth = 0.2, linestyle = "solid", color = "black")
			plt.plot(s, orbit, '-', linewidth = 0.5, linestyle = "solid", color = "red")

			for element in self.lattice:
				if plane == 'x':
					center = element.settings['x']
				elif plane == 'y':
					center = element.settings['y']
				else:
					raise ValueError('"plane" accepts only "x" or "y", received - ' + str(plane))
				if center == 0.0 and offsets_only:
					continue

				s, length = element.settings['s'], element.settings['length'] * length_scale
				_classification = {
					'Quadrupole': {"length_scale": 2.0, "color": "blue"},
					'Bpm': {"length_scale": .75, "color": "green"},
					'Cavity': {"length_scale": .5, "color": "grey"}
				}
				if element.type in ['Quadrupole', 'Bpm', 'Cavity']:
					_height = _DEFAULT_HEIGHT * _classification[element.type]["length_scale"]
					ax.add_patch(patches.Rectangle((s - length, -_height + center), length, 2 * _height, linewidth = 1e-6, edgecolor = _classification[element.type]["color"], facecolor = _classification[element.type]["color"]))
					


			plt.ylim(-300, 300)
			plt.xlim(0, 200)
			plt.xlabel("s [m]")
			plt.ylabel(plane + r" [$\mu$m]")
			if 'filename' in extra_params:
				plt.savefig(extra_params.get('filename'))
			plt.show()

#	def __repr__(self):

#		return f"Cavity({self.settings}, {self.girder}, {self.index}, '{self.type}')"

#	def __str__(self):
#		return f"Cavity({json.dumps(self.settings, indent = 4)})"


def parse_line(data, girder_index = None, index = None):
	"""
	Parse the line of the file containing the Placet lattice
	"""
	data_list, i, res = data.split(), 1, {}
	elem_type = data_list[0]

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

	if elem_type == "Girder":
		return "Girder", None

def test_init():
	
	with open("Lattices/1000_db_ml.tcl", 'r') as f:
		for line in f.readlines():
			res = parse_line(line)
			print(res)

def test_write():
	ml = Beamline("ml")
	ml.read_from_file("tmp.dat")
	print(ml)
	ml.save(filename = "temp/beamline_tmp.json")

def test_read():
	ml = Beamline("ml")
	ml.read("temp/beamline_tmp.json")
	ml.to_placet("temp/lattice_tmp.tcl")

def convert_to_json(filename_in, filename_out):
	ml = Beamline()
	ml.read_from_file(filename_in)
	ml.save(filename = filename_out)

def read_from_json():
	ml = Beamline()
	ml.read("Lattices/drive_beam_ml.json")
	ml.to_placet("lattice_tmp.tcl")

def errors_reading():
	ml = Beamline("ml")
	ml.read_from_file("Lattices/1000_db_ml.tcl")
	ml.read_misalignments("temp/positions.dat", cav_bpm = True, cav_grad_phas = True)
	ml.save_misalignments("temp/positions_2.dat", cav_bpm = True, cav_grad_phas = True)

if __name__ == "__main__":
#	test_write()
#	test_read()

#	convert_to_json()
#	read_from_json()
	errors_reading()