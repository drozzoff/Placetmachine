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