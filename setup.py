from setuptools import setup, find_packages

DEPENDENCIES = [
	'pexpect',
	'pandas',
	'rich',
	'numpy'
]

setup(
	name = "placetmachine",
	version = "0.0.1-alpha",
	description = "Python API for the beam tracking code Placet",
	author = "Andrii Pastushenko",
	url = "to add",
	python_requires = ">=3.7",
	license = "MIT",
	
	packages = ["placetmachine", "placetmachine.placet", "placetmachine.lattice", "placetmachine.beam"],
	package_data = {
		'placetmachine': ["placet_files/*"]
	},
	install_requires = DEPENDENCIES,
	classifiers = [
		"Intended Audience :: Science/Research",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: English",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.7",
		"Topic :: Scientific/Engineering :: Physics",
	],
)
