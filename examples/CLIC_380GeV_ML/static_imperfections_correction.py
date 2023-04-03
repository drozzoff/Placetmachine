import placetmachine as pl
import pandas as pd
import random

clic = pl.Machine()

#+++++++++++Beamline creation+++++++++++
cavity_structure = {
    'a': 3.33e-3,
    'g': 6.4e-3,
    'l': 8.33333e-3,
    'delta': 0.18,
    'delta_g': 0.5e-3,
    'phase': 8.0, 
    'frac_lambda': 0.25, 
    'scale': 1.0
}
clic.create_beamline("ml_beamline.tcl", name = "ml", cavities_setup = cavity_structure)

#+++++++++++Beam creation+++++++++++
beam_parameters =  {
    'emitt_x': 8.0,
    'emitt_y': 0.1,
    'e_spread': 1.6,
    'e_initial': 9.0,
    'sigma_z': 70, 
    'phase': 0.0,
    'charge': 5.2e9,
    'beta_x': 8.054208256047598,
    'beta_y': 1.201443036029169,
    'alpha_x': 2.455451375064132e-02,
    'alpha_y': 6.250882009649877e-03,
    'n_total': 500
}
main_beam = clic.make_beam_slice_energy_gradient("main_beam", 11, 5, 1.0, 1.0, int(random.random() * 1e5), **beam_parameters)

#+++++++++++Applying alignment errors+++++++++++
static_errors = {
    "quadrupole_x": 14.0,
    "quadrupole_y": 14.0,
    "quadrupole_roll": 100.0,
    "bpm_x": 14.0,
    "bpm_y": 14.0,
    "bpm_roll": 100.0,
    "cavity_x": 14.0,
    "cavity_y": 10.0,
    "cavity_realign_x": 3.5,
    "cavity_realign_y": 3.5,
    "cavity_xp": 141,
    "cavity_yp": 141
}

clic.assign_errors("default_clic", static_errors = static_errors, scatter_y = 12.0, flo_y = 5.0)

#+++++++++++Particle tracking+++++++++++
correction_summary = clic.track(main_beam)

#+++++++++++121 correction+++++++++++
one_2_one = clic.one_2_one(main_beam, bpm_resolution = 0.1)
correction_summary = pd.concat([correction_summary, one_2_one])

#+++++++++++DFS+++++++++++

#extra beams for DFS
beam1 = clic.make_beam_slice_energy_gradient("dfs_beam1", 11, 5, 0.95, 0.9, int(random.random() * 1e5), **beam_parameters)
cbeam0 = clic.make_beam_slice_energy_gradient("dfs_cbeam0", 1, 1, 1.0, 1.0, int(random.random() * 1e5), **beam_parameters)
cbeam1 = clic.make_beam_slice_energy_gradient("dfs_cbeam1", 1, 1, 0.95, 0.9, int(random.random() * 1e5), **beam_parameters)

dfs_options = {
    'wgt1': 1000, 
    'bin_iteration': 3, 
    'correct_full_bin': 1, 
    'binlength': 36, 
    'binoverlap': 18,
    'bpm_resolution': 0.1,
    'beam1': beam1,
    'cbeam0': cbeam0,
    'cbeam1': cbeam1
}

dfs = clic.DFS(main_beam, **dict(dfs_options))
correction_summary = pd.concat([correction_summary, dfs])

#+++++++++++RF alignment+++++++++++
rf = clic.RF_align(main_beam, girder = 1, bpm_resolution = 0.1)
correction_summary = pd.concat([correction_summary, rf])

print(correction_summary)