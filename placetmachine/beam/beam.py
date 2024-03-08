import os
import random
from typing import Optional
import pandas as pd
import numpy as np
import tempfile
from placetmachine import Placet

def make_beam_particles(e_design: float, e_spread: float, n_particles: int, **extra_params) -> pd.DataFrame:
	"""
	Generate the particles distribution for the particle beam creation. 
	**Does not generate the beam!**

	Equivalent to the procedure of the same name in Placet file 'make_beam.tcl'.
	
	Parameters
	----------
	e_design
		The beam design energy in [GeV].
	e_spread
		The beam energy spread in [%].
	n_particles
		Number of particles in the beam.

	Other parameters
	----------------
	sigma_z : float
		Bunch length in micrometers.
	beta_x : float
		Horizontal beta-function.
	beta_y : float
		Vertical beta-function.
	alpha_x : float
		Horizontal alpha-function.
	alpha_y : float
		Vertical alpha-function.
	emitt_x : float
		Horizontal normalized emittance.
	emitt_y : float
		Vertical normalized emittance.

	Returns
	-------
	DataFrame
		The particles' coordinates.
	"""
	_options_list = ['sigma_z', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y']
	for value in _options_list:
		if not value in extra_params:
			raise Exception(f"The parameter '{value}' is missing!")

	emittance_x = extra_params.get('emitt_x') * 1e-7 * 0.511e-3 / e_design
	emittance_y = extra_params.get('emitt_y') * 1e-7 * 0.511e-3 / e_design

	sigma_x = np.sqrt(emittance_x * extra_params.get('beta_x')) * 1e6
	sigma_y = np.sqrt(emittance_y * extra_params.get('beta_y')) * 1e6
	sigma_px = np.sqrt(emittance_x / extra_params.get('beta_x')) * 1e6
	sigma_py = np.sqrt(emittance_y / extra_params.get('beta_y')) * 1e6
	sigma_z = extra_params.get('sigma_z')
	sigma_E = 0.01 * np.abs(e_spread)

	e, x, y, z, px, py = [], [], [], [], [], []
	if e_spread < 0:
		for i in range(n_particles):
			e.append(e_design * (1.0 + sigma_E * (random.uniform(0, 1) - 0.5)))
			z_tmp = random.gauss(0, sigma_z)
			while np.abs(z_tmp) >= 3 * sigma_z:
				z_tmp = random.gauss(0, sigma_z)
			z.append(z_tmp)

			x.append(random.gauss(0, sigma_x))
			y.append(random.gauss(0, sigma_y))

			px.append(random.gauss(0, sigma_px) - extra_params.get('alpha_x') * x[-1] * sigma_px / sigma_x)
			py.append(random.gauss(0, sigma_py) - extra_params.get('alpha_y') * x[-1] * sigma_py / sigma_y)
	else:
		for i in range(n_particles):
			e_offset = random.gauss(0, sigma_E)
			while np.abs(e_offset) >= 3 * sigma_E:
				e_offset = random.gauss(0, sigma_E)
			e.append(e_design * (1.0 + e_offset))

			z_tmp = random.gauss(0, sigma_z)
			while np.abs(z_tmp) >= 3 * sigma_z:
				z_tmp = random.gauss(0, sigma_z)
			z.append(z_tmp)

			x.append(random.gauss(0, sigma_x))
			y.append(random.gauss(0, sigma_y))

			px.append(random.gauss(0, sigma_px) - extra_params.get('alpha_x') * x[-1] * sigma_px / sigma_x)
			py.append(random.gauss(0, sigma_py) - extra_params.get('alpha_y') * x[-1] * sigma_py / sigma_y)

	particle_coordinates = pd.DataFrame({'E': e, 'x': x, 'y': y, 'z': z, 'px': px, 'py': py})
	particle_coordinates = particle_coordinates.sort_values('z')

	return particle_coordinates

class Beam:
	"""
	A class to handle the beams in **Placet**.

	Attributes
	----------
	name : str
		The name of the beam.
	placet : Placet
		The `Placet` object to control the beam creation in **Placet**.
	beam_type : str
		The type of beam. The possible options are:
		```
		["sliced", "partice", None]
		```
	
	_data_folder_ : str
		The name of the folder where the temporary files produced by **Placet** are stored.
	"""
	def __init__(self, beam_name: str, placet: Placet, beam_type: Optional[str] = None):
		"""
		name
			The name of the beam to create.
		placet 
			Placet process to create the beam in.
		beam_type
			The type of beam to create. The possible options it accepts:
			```
			["sliced", "partice", None]
			```
			First 2 are valid options for Placet, `None` is for testing only.
		"""
		self.name, self.placet = beam_name, placet
		if beam_type in ["sliced", "particle", None]:
			self.beam_type = beam_type
		else:
			raise ValueError(f"Incorrect beam type - '{beam_type}'")
		
		self.dict = tempfile.TemporaryDirectory()
		self._data_folder_ = self.dict.name

	def make_beam_slice_energy_gradient(self, n_slice: int, n_macroparticles: int, eng: float, grad: float, beam_seed: Optional[int] = None, **extra_params):
		"""
		Generate the macroparticle (sliced) beam.
		
		Similar to `make_beam_slice_energy_gradient`from "make_beam.tcl" in Placet but rewritten in Python.

		Parameters
		----------
		beam_name
			Name of the beam.
		n_slice
			Number of the slices.
		n_macroparticles
			Number of the macroparticles per slice.
		eng
			Initial energy offset.
		grad
			Accelerating gradient offset.
		beam_seed
			The seed number of the random number distribution. If not given a random
			number in the range [1, 1000000] is taken.
		
		Other parameters
		----------------
		sigma_z : float
			**[Required]** Bunch length in micrometers. 
		charge : float
			**[Required]** Bunch charge.
		beta_x : float
			**[Required]** Horizontal beta-function.
		beta_y : float
			**[Required]** Vertical beta-function.
		alpha_x : float
			**[Required]** Horizontal alpha-function.
		alpha_y : float
			**[Required]** Vertical alpha-function.
		emitt_x : float
			**[Required]** Horizontal normalized emittance.
		emitt_y : float
			**[Required]** Vertical normalized emittance.
		e_spread : float
			**[Required]** Energy spread.
		e_initial : float
			**[Required]** Initial energy.
		n_total : int
			**[Required]** Total number of the particles.

		Returns
		-------
		str
			The beam name.
		"""

		_options_list = ['charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'sigma_z', 'n_total']
		for value in _options_list:
			if not value in extra_params:
				raise Exception(f"The parameter '{value}' is missing!")

		if beam_seed is None:
			beam_seed = random.randint(1, 1000000)
		
		self.placet.RandomReset(seed = beam_seed)

		beam_setup = {
			'bunches': 1,
			'macroparticles': n_macroparticles,
			'particles': extra_params.get('n_total'),
			'energyspread': 0.01 * extra_params.get('e_spread') * extra_params.get('e_initial'),
			'ecut': 3.0,
			'e0': eng * extra_params.get('e_initial'),
			'file': self.placet.wake_calc(os.path.join(self._data_folder_, "wake.dat"), extra_params.get('charge'), -3,  3, extra_params.get('sigma_z'), n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x')
		}
		self.placet.InjectorBeam(self.name, **beam_setup)
		
		self.placet.SetRfGradientSingle(self.name, 0, "{" + str(grad) +  " 0.0 0.0}")
	
	def make_beam_many(self, n_slice: int, n: int, **extra_params):
		"""
		Generate the particle beam.
		
		Similar to `make_beam_many` from "make_beam.tcl" in Placet but rewritten in Python.
		
		Practically could pass the whole beam_setup to the function. Keep the same structure as in Placet.
		Optional parameters (if not given, checks self.beam_parameters. If self.beam_parameters does not have them throws an Exception)
		
		Parameters
		----------
		beam_name
			Name of the beam.
		n_slice
			Number of the slices.
		n
			Number of the particles per slice.
	
		Other parameters
		----------------
		sigma_z : float
			**[Required]** Bunch length in micrometers. 
		charge : float
			**[Required]** Bunch charge.
		beta_x : float
			**[Required]** Horizontal beta-function.
		beta_y : float
			**[Required]** Vertical beta-function.
		alpha_x : float
			**[Required]** Horizontal alpha-function.
		alpha_y : float
			**[Required]** Vertical alpha-function.
		emitt_x : float
			**[Required]** Horizontal normalized emittance.
		emitt_y : float
			**[Required]** Vertical normalized emittance.
		e_spread : float
			**[Required]** Energy spread.
		e_initial : float
			**[Required]** Initial energy.
		n_total : int
			**[Required]** Total number of the particles.

		Returns
		-------
		str
			The beam name.
		"""
		_options_list = ['sigma_z', 'charge', 'beta_x', 'beta_y', 'alpha_x', 'alpha_y', 'emitt_x', 'emitt_y', 'e_spread', 'e_initial', 'n_total']
		for value in _options_list:
			if not value in extra_params:
				raise Exception(f"The parameter '{value}' is missing!")

		beam_setup = {
			'bunches': 1,
			'macroparticles': n,
			'particles': extra_params.get('n_total'),
			'energyspread': 0.01 * extra_params.get('e_spread') * extra_params.get('e_initial'),
			'ecut': 3.0,
			'e0': extra_params.get('e_initial'),
			'file': self.placet.wake_calc(os.path.join(self._data_folder_, "wake.dat"), extra_params.get('charge'), -3,  3, extra_params.get('sigma_z'), n_slice),
			'chargelist': "{1.0}",
			'charge': 1.0,
			'phase': 0.0,
			'overlapp': -390 * 0.3 / 1.3,	#no idea
			'distance': 0.3 / 1.3,			#bunch distance, no idea what it is
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x')
		}
		self.placet.InjectorBeam(self.name, **beam_setup)

		self.placet.SetRfGradientSingle(self.name, 0, "{1.0 0.0 0.0}")
		
		particle_beam_setup = {
			'alpha_y': extra_params.get('alpha_y'),
			'beta_y': extra_params.get('beta_y'),
			'emitt_y': extra_params.get('emitt_y'),
			'alpha_x': extra_params.get('alpha_x'),
			'beta_x': extra_params.get('beta_x'),
			'emitt_x': extra_params.get('emitt_x'),
			'sigma_z': extra_params.get('sigma_z')
		}
		particles_distribution = make_beam_particles(extra_params.get('e_initial'), extra_params.get('e_spread'), n_slice * n, **particle_beam_setup)
		particles_distribution.to_csv(os.path.join(self._data_folder_, "particles.in"), sep = ' ', index = False, header = False)

		self.placet.BeamRead(beam = self.name, file = os.path.join(self._data_folder_, "particles.in"))

	def offset_beam(self, **extra_params):
		"""
		Add the transverse offset, transverse angle or roll angle to the 
		currentbeam.

		Other parameters
		----------------
		x : float
			Horizontal offset in micrometers.
		y : float
			Vertical offset in micrometers.
		angle_x : float
			Horizontal angle in microradians.
		angle_y : float
			Vertical angle in microradians.
		rotate : float
			Roll angle in radians. It is added after the offsets.
		start : int
			First particle to offset.
		end : int
			Last particle to offset.
		"""
		self.placet.BeamAddOffset(**dict(extra_params, beam = self.name))