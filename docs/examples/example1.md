# Example - Beamline creation and beam tracking

First, we need to import the module in order to use it
```
import placetmachine as pl
```

Now, we want to create a basic `Machine` object. It will start a PLACET process running in the background.

In this example, we are going to use CLIC 380 GeV Main Linac.
```
clic = pl.Machine()
```
The output:
```
********************************************************************************
**                                                                            **
**                       PLACET Version No 1.0.5 (SWIG)                       **
**                           written by D. Schulte                            **
**                             contributions from                             **
**                            A. Latina, N. Leros,                            **
**                           P. Eliasson, E. Adli,                            **
**                          B. Dalena, J. Snuverink,                          **
**                           Y. Levinsen, J. Esberg                           **
**                                                                            **
**                             THIS VERSION INFO:                             **
**                         Octave interface enabled                           **
**                         Python interface enabled                           **
**                            MPI module disabled                             **
**                                                                            **
**                 Submit bugs reports / feature requests to                  **
**                  https://its.cern.ch/jira/browse/TCPLACET                  **
**                                                                            **
********************************************************************************
```
By defult it is going to print the PLACET welcome message.

So, now we want to create a beamline and beam before we can do any tracking.
Lets start with the beamline.
```
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
```
The output:
```
[17:01:24] Beamline created                                                                           machine.py:70
```

In this example, we read the PLACET lattice from the file "ml_beamline.tcl". One can take the file from [here](https://github.com/drozzoff/Placetmachine/tree/master/examples/CLIC_380GeV_ML).
We give the beamline a name "ml" and we provide the cavities setup dictionary `cavity_structure` that is needed for PLACET to evaluate the wakefield effects in the beamline.
*Description of each term to follow.*

Lets create a sliced beam with a `make_beam_slice_energy_gradient()`:
```
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
main_beam = clic.make_beam_slice_energy_gradient("main_beam", 11, 5, 1.0, 1.0, 1111, **beam_parameters)
```
The output:
```
[17:02:17] Beam created                                                                               machine.py:70
```

We pass to the function
- Name for the beam.
- Number of slices.
- Number of macroparticles per slice.
- Initial energy offset.
- Accelerating gradient offset.
- The seed number of the random number distribution.
- A dictionary with the whole list of the beam parameters.

Now, as we have all the important parts of the beamline, lets perform the tracking
```
perfect_line = clic.track(main_beam)
print(perfect_line)
```
The output
```
[17:03:31] Tracking done                                                                              machine.py:70
  correction       beam     survey positions_file  emittx    emitty beamline
0         No  main_beam  from_file           None  8.0093  0.100151       ml
```
The tracking result is retured as `pandas.DataFrame`. It contains, the data about corrections applied, file used for the survey, name of the beam and beamline used for the tracking 
and the beam emittances at the ML exit.