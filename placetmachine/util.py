
# So far, the only elements that can be used in the Knob based tuning are Quads and cavities

class Knob:
	"""
	A class used for the knobs handling

	Attributes
	----------
	name: str
		Name of the knob
	variables_girders: dict optional
		The dict of the girders offsets corresponding to the knob amplitude 1 in the format
		{
			'girder1':{
				'y': ..
				'py': ..
				..
			}	
			'girder2':{
				..
			}
			..
		}
	variables_elements: dict optional
		The dict of the elements offsets corresponding to the knob amplitude 1
		{
			'element1':{
				'y': ..
				'py': ..
				..
			}	
			'element2':{
				..
			}
			..
		}
	cavs_only: bool, default True
		If True, this indicates guirders movements correspond to the cavities movement
	types_of_elements: list, optional
		The full list if the types of the elements involved in the knob definition

	Methods
	-------
	apply(amplitude)
		Apply the knob with the given amplitude

	"""
	knob_elements = ['Cavity', 'Quadrupole'] #potential elements used in the knob	| to be expanded
	def __init__(self, variables_girders = {}, variables_elements = {}, name = "default", cavs_only = True):
		"""

		Parameters
		----------
		variables_girders: dict {}
			The dict of the girders offsets corresponding to the knob amplitude 1 in the format
		}
		variables_elements: dict {}
			The dict of the elements offsets corresponding to the knob amplitude 1
		cavs_only: bool default True
			If True, only offsets the cavities on the girder
		name: str default "default"
			The name of the knob
		"""
		self.name, self.variables_girders, self.variables_elements, self.cavs_only = name, variables_girders, variables_elements, cavs_only
		self.get_types_of_elements()

	def __str__(self):
		return str(self.__dict__)
		
	def apply(self, amplitude) -> (dict, dict):
		"""
		Apply the knob with the given amplitude
		...............

		Returns two dictionaries, first one with the girders offsets, second one with the elements offsets.

		Parameters
		----------
		amplitude: float
			Amplitude of the knob

		Returns
		-------
		res_girders: dict
			The girders offsets
		res_elements: dict
			The elements offsets

		"""
		res_girders, res_elements = {}, {}
		for girder in self.variables_girders:
			res_girders[girder] = {coord: value * amplitude * 1e6 for coord, value in self.variables_girders[girder].items()}

		for element in self.variables_elements:
			res_elements[element] = {coord: value * amplitude * 1e6 for coord, value in self.variables_elements[element].items()}

		return res_girders, res_elements

	def get_types_of_elements(self):
		"""
		Evaluate the elements types involved in the knob definition.

		Assigns the list to an attribute self.types_of_elements

		Returns
		-------
		list
			The types list
		"""
		res = []
		
		if self.variables_girders != {}:
			res += ['Cavity'] if self.cavs_only else ['Cavity', 'Quadrupole']	#more advanced girder analysis may be needed
		if self.variables_elements != {}:
#			for key in self.variables_elements:
#				if key in self.be
			if not 'Quadrupole' in res:
				res.append('Quadrupole')
		self.types_of_elements = res if res != [] else None
		return self.types_of_elements

	__repr__ = __str__

class CoordTransformation:
	"""
	Class used to store the coordinates tranformations
	"""
	def __init__(self, transformation_matrix):

		self.transformation_matrix = transformation_matrix

	def transform(self, coordinates):
		"""
		Transform the set of the coordinates
		---
		Performs the matrix X vector multiplication

		Parameters
		----------
		coordinates: np.array
			The set of the coordinates

		Returns
		-------
		np.array
			The resulting vector
		"""
		return self.transformation_matrix.dot(coordinates)

	def __str__(self):
		return str(self.transformation_matrix)

	__repr__ = __str__