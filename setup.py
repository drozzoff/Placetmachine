from setuptools import setup, find_packages

DEPENDENCIES = [
	'pexpect==4.7.0',
	'pandas==1.1.3',
	''
]

setup(
	name = "placetmachine",
	version = "0.0.1",
	description = "Python API for the beam tracking code Placet",
	author = "Andrii Pastushenko",
	url = "to add",
	python_requires = ">=3.7",
	license = "MIT",
	

	classifiers=[
		"Intended Audience :: Science/Research",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: English",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.7",
		"Programming Language :: Python :: 3.8",
		"Programming Language :: Python :: 3.9",
		"Programming Language :: Python :: 3.10",
		"Topic :: Scientific/Engineering :: Physics",
	],
	packages = ["placetmachine"],
	include_package_data=True,
	install_requires = DEPENDENCIES,
)