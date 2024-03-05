import placetmachine as pl
import os
import numpy as np


average = lambda data: sum(data) / len(data)
rms = lambda data: np.sqrt(sum(list(map(lambda x: x * x, data))) / len(data) - average(data)**2)

clic = pl.Machine(save_logs = True)

#+++++++++++Beamline creation+++++++++++
# cavities info is mandatory for the beamline creation
# this is what we use for the CLIC BDS. It does not affect
# anything, since we have no cavities in the lattice.
cavity_structure = {
	'a': 2.75e-3,
	'g': 7e-3,
	'l': 8.33333e-3,
	'delta': 0.145,
	'delta_g': 0.333e-3
}

clic.create_beamline("clic380_v2.tcl", name = "clic_bds", parser = "advanced", 
	parser_variables = dict(e0 = 190, mult_synrad = 1, quad_synrad = 1, sbend_synrad = 1), cavities_setup = cavity_structure)

beam_parameters =  {
	'emitt_x': 9.5,
	'emitt_y': 0.30,
	'e_spread': -1.0,
	'e_initial': 190,
	'sigma_z': 70.0, 
	'phase': 0.0,
	'charge': 5.2e9,
	'beta_x': 33.07266007,
	'beta_y': 8.962361942,
	'alpha_x': 0.0,
	'alpha_y': 0.0,
	'n_total': 40000
}

main_beam = clic.make_beam_many("main_beam", 200, 200, **beam_parameters)

res = clic.eval_obs(main_beam, ['x', 'y'], beam_type = 'particle')

x, y = res[0], res[1]

print(f"sigma_x = {rms(x) * 1e3} nm, sigma_y = {rms(y) * 1e3} nm")