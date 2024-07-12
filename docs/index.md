# placetmachine Documentation

This website features the details of the module `placetmachine` that is used for the particle tracking.

`placetmachine` acts as a wrapper for the tracking code [PLACET](https://gitlab.cern.ch/clic-software/placet).
It allows for the basic beamline and beam handling as well as beam tracking and corrections (121, DFS, RF alignment).
All the tools are written in Python, so using PLACET becomes easier and more streamligned.
The module features a class `Placet` that facilitates the interaction with Placet using [`Pexpect`](https://github.com/pexpect/pexpect).
It can be used directly to comunicate with PLACET. Other classes included are `Beamline` for the beamlines handling and `Beam` for the beams handling.
All of them are connected inside of the `Machine` class to simulate the actual beamline and use PLACET as the driving code for the tracking/corrections.