# -*- coding: utf-8 -*-
"""
Created on Thu Dec 20 12:00:00 2018

@author: Soma Olasz
"""

# Import necessary modules and Python scripts.
import readIn
import testReadIn
import rangeCheck
import dimensionCheck
import pGridMode
import matlabDouble
import EHat_calc
import CoulombLogarithm
import hdf5Write

import numpy as np
import matlab.engine
import itertools
import pickle
import ual
from time import asctime
import copy

# Load the external variables

# Save the location of the matlab variables needed for the NORSE tests
# Laptop loaction: 'D:\\ToDo\\Munka\\NORSE\\NORSE\\examples\\'
# Gateway location: '/pfs/work/g2solasz/git/NORSE/examples/'

# Load the matlab variables into Python in numpy array form
f = testReadIn.load('outputAdvanced.mat', '/pfs/work/g2solasz/git/NORSE/examples/', 'f')
extPBig = testReadIn.load('externalPBig.mat', '/pfs/work/g2solasz/git/NORSE/examples/', 'extPBig')
extXiBig = testReadIn.load('externalXiBig.mat', '/pfs/work/g2solasz/git/NORSE/examples/', 'extXiBig')

# Create a list from the external data variables
inputData = [f, extPBig, extXiBig]

# Put some sanity checks on the external variables

# Check on element range

# TODO Should check the external distribution somehow. Checking for negative values does not work.

# Check if the values of extPBig are all positive
rangeCheck.within(inputData[1], 'min', 0)

# Check if the values of extXiBig are between -1 and 1
rangeCheck.within(inputData[2], 'min', -1)
rangeCheck.within(inputData[2], 'max', 1)

# Check on dimensions

# Check if any of the external data has different dimensions
dimensionCheck.isIdentical(inputData[0], inputData[1], inputData[2])

# Extract numerical parameters necessary to recreate the grid
# pMax, nP, and nXi parameters are needed to recreate the NORSE grid

# pMax is the maximum of the extPBig vector
extPMax = max(inputData[1])

# create a temporary array from the locations of the maximum values of the external pBig
temp = np.where(inputData[1] == inputData[1].max())

# nXi is the number of maximums in extPBig
nXi = len(temp[0])

# create a temporary array from the locations of the maximum values of the external xiBig
temp = np.where(inputData[2] == inputData[2].max())

# nP is the number of maximums+1 in extXiBig
nP = len(temp[0])+1

# Check if the dimensions of the external distribution is correct

if len(inputData[0]) != ((nP-1)*nXi+1):
    raise Exception('The dimensions of the external distribution are incorrect')

# Extract pGridMode, pGridParameter and xiGridMode from grid vectors

# pGridMode
pGrid = pGridMode.extract(inputData[1], nP)
pGridMode = pGrid[0]
pGridParameter = float(pGrid[1])

# xiGridMode
# TODO find a way to implement a similar method as in pGridMode

# Resolution and parameters
# From here, the code will follow the AdvancedNORSERun example file found in the Github project named in the description
# of this code. The section name is taken from there.

# Set constant physical parameters and numerical parameters

# Numerical parameters. Some has been taken from SimpleNORSERun.m to get sensible results
# nP = 175       # these have been determined earlier
# nXi = 35       #             -- || --
# yMax = 14      # Thermal momenta (gamma v/v_th); Don't need this as time dependent parameters are excluded
pMax = float(extPMax)
nL = 7
dt = 9e-5
tMax = 0.018
nSaveSteps = 30  # 0, save the distribution at all timesteps

# Set up NORSE

# Start a Matlab engine to be able to call Matlab scripts
eng = matlab.engine.start_matlab()

# Save the location of the  matlab scripts necessary for the run
# Laptop: 'D:\\ToDo\\Munka\\NORSE\\NORSE\\src'
# Gateway: '/pfs/work/g2solasz/git/NORSE/src'
# Gateway: '/pfs/work/g2solasz/git/NORSE_actor'

# Add the location of NORSE files to the Matlab path
eng.addpath('/pfs/work/g2solasz/git/NORSE_hoppe/NORSE/src')
eng.addpath('/pfs/work/g2solasz/git/NORSE_actor/NORSE_actor')

# Initialize an empty NORSE object
o = eng.NORSE()

# Change some settings (see NORSE.m for a complete list)
eng.setfield(o, 'nSaveSteps', nSaveSteps)
eng.setfield(o, 'includeHeatSink', 1)			# TODO we will use something different in ETS
eng.setfield(o, 'enforceStrictHeatConservation', 1)
eng.setfield(o, 'show1DTimeEvolution', 0)
eng.setfield(o, 'conservativeParticleSource',1)

# Setting the parameters to NORSE object

# Set the grid parameters calculated earlier
eng.setfield(o, 'pGridMode', pGridMode)
# TODO The grid parameter is not exactly the same as the one which created the external grid. Has to set a limit on the error
# later.
eng.setfield(o, 'pGridParameter', pGridParameter)

# Before performing the calculation set the initialDistribution property
# to 4, corresponding to external distribution input
eng.setfield(o, 'initialDistribution', 4)

# Run NORSE in silent mode so no information is printed
eng.setfield(o, 'silent', True)

# Convert the numpy arrays into matlab doubles so the PerformCalculation method can use them
f1 = matlabDouble.convert(inputData[0])
extPBig1 = matlabDouble.convert(inputData[1])
extXiBig1 = matlabDouble.convert(inputData[2])

# Create a matlab structure from the input data given in Matlab doubles
input_structure = eng.createStructure(f1, 'f', extPBig1, 'extPBig', extXiBig1, 'extXiBig')

# Numerical parameters
# Get the number of rho coordinates
rho_size = size(coreprof0[0].rho_tor_norm)

# Initialize arrays for physical parameters
temperature = np.zeros(rho_size)
density = np.zeros(rho_size)
EHat = np.zeros(rho_size)
Z_eff = np.zeros(rho_size)
B0 = np.zeros(rho_size)
rhoTor_arr = np.zeros(rho_size)
E_parallel = np.zeros(rho_size)
E_critical = np.zeros(rho_size)
time = readIn.convert(coreprof0[0].time)

# Define physical constants
c = 3e8
e = 1.6e-19

# Constant physical parameters
for i in range(rho_size):
	
	# Fill physics arrays with values from CPOs
	temperature[i] = readIn.convert(coreprof0[0].te.value, i)				# eV
	density[i] = readIn.convert(coreprof0[0].ne.value, i)					# m^{-3}
	EHat[i] = EHat_calc.calculate(density[i],CoulombLogarithm.calculate(density[i],temperature [i]),readIn.convert(coreprof0[0].profiles1d.eparallel.value, i))			# E/E_c
	Z_eff[i] = readIn.convert(coreprof0[0].profiles1d.zeff.value, i)			# Z_eff
	rhoTor_arr[i] = readIn.convert(coreprof0[0].rho_tor, i)					# m
	B0[i] = readIn.convert(coreprof0[0].toroid_field.b0)					# T
	E_parallel[i] = readIn.convert(coreprof0[0].profiles1d.eparallel.value, i)		# V/m
	E_critical[i] = E_parallel[i]/EHat[i]

# Initialize variables for storing calculation results
totalDistribution = []		# data storage for CPOs
finalPBig = []			# data storage for CPOs
finalXiBig = []			# data storage for CPOs
growth_rate = []
runaway_density = []
runaway_current = []

# Initialize numpy arrays to store distribution and coordinates for hdf5 writing
Distribution = np.zeros((1,rho_size,(nP-1)*nXi+1))
PBig = np.zeros((1,rho_size,(nP-1)*nXi+1))
XiBig = np.zeros((1,rho_size,(nP-1)*nXi+1))

for i in range (rho_size):

	# All the variables must be Python float, so Matlab gets them as double. The calculation doesn't work with integers.
	eng.SetParameters(o, float(nP), float(nXi), float(nL), float(pMax), float(dt), float(tMax), float(temperature[i]), float(density[i]), float(Z_eff[i]), float(EHat[i]), float(B0[i]), nargout=0)

	# Perform calculation
	eng.PerformCalculation(o, input_structure, nargout=0)

	# Take the data from the NORSE object, which will go into the CPO.
	distribution = np.array(eng.extractDistribution(o)).tolist()
	pBig = np.array(eng.extractPBig(o)).tolist()
	xiBig = np.array(eng.extractXiBig(o)).tolist()
	growthRate = density[i]*eng.extractGrowthRate(o)
	runawayDensity = density[i]*eng.extractFraction(o)
	runawayCurrent = runawayDensity * e * c * np.sign(E_parallel[i])
	
	# flatten the data to python list, so it can be given to the CPO
	distribution = list(itertools.chain.from_iterable(distribution))
	pBig = list(itertools.chain.from_iterable(pBig))
	xiBig = list(itertools.chain.from_iterable(xiBig))
	growth_rate.append(growthRate)
	runaway_density.append(runawayDensity)
	runaway_current.append(runawayCurrent)
	
	# Save coordinates from first calculation to write to CPO
	if i == 0:
		finalPBig = pBig
		finalXiBig = xiBig
	
	# Check if the grids are the same for the later calculations as the saved grid
	else:
		if not  finalPBig == pBig:
			raise Exception('The p grid is not the same for rho index {} as for the first index.'.format(i+1))
			
		elif not finalXiBig == xiBig:
			raise Exception('The xi grid is not the same for rho index {} as for the first index.'.format(i+1))
	
	totalDistribution += distribution
	
	# Convert data lists to numpy arrays
	distribution = np.array(distribution)
	pBig = np.array(pBig)
	xiBig = np.array(xiBig)
	
	# Save distribution and coordinates to global vairables
	Distribution[0,i,:] = distribution
	PBig[0,i,:] = pBig
	XiBig[0,i,:] = xiBig

# Convert rho coordinates to list so it can be given to CPOs
rhoTor = rhoTor_arr.tolist()

# Write calculation results to CPO
# Give run and shot numbers needed for CPO writing
shot = parameters["shotnumber"]
run = parameters["run_out"]

# Initialize CPO structure
itmp = ual.itm(shot, run)
itmp.create()

# Set numerical parameters for CPO writing
nCoord = 3	# number of different coordinates used (p, xi, rho_tor)
timeIn = 0	# TODO input time (will be taken from input CPO)
dt = 0.001	# TODO time step (will be taken from workflow parameter) (not sure if this will be added, the input time might already 		contain the time step for ETS)

# initialize the CPO
itmp.distributionArray.resize(1)
itmp.distributionArray.array[0].distri_vec.resize(1)
itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion.resize(1)
itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces.resize(nCoord)

# fill the coordinates
for i in range (nCoord):
	itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects.resize(1)
	itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].coordtype.resize(1,1)

	# p coordinate
	if i == 0: 
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo.resize((nP-1)*nXi+1,1,1,1)
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].coordtype[0,0] = 123
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo[:,0,0,0] = finalPBig
			
	# xi coordinate
	elif i == 1:
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo.resize((nP-1)*nXi+1,1,1,1)
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].coordtype[0,0] = 126
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo[:,0,0,0] = finalXiBig
			
	# rho coordinate
	else:
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo.resize(rho_size,1,1,1)
		# 107 is the coordinate convention for rho_tor (see https://portal.eufus.eu/documentation/ITM/html/itm_enum_types__coordinate_identifier.html#itm_enum_types__coordinate_identifier). Might have to change this later.
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].coordtype[0,0] = 107
		itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].grid.spaces[i].objects[0].geo[:,0,0,0] = rhoTor
			
# Write the distribution to the CPO
itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].values.scalar.resize(((nP-1)*nXi+1)*rho_size)
itmp.distributionArray.array[0].distri_vec[0].dist_func.f_expansion[0].values.scalar[:] = totalDistribution
		
# Write the time
itmp.distributionArray.array[0].time = timeIn + dt

# put CPO
itmp.distributionArray.put()
itmp.close()

# Reshape data for hdf5 writing
temperature = temperature.reshape(1,rho_size)
density = density.reshape(1,rho_size)
EHat = EHat.reshape(1,rho_size)
Z_eff = Z_eff.reshape(1,rho_size)
B0 = B0.reshape(1,rho_size)
rhoTor = rhoTor_arr.reshape(1,rho_size)
E_parallel = E_parallel.reshape(1,rho_size)
E_critical = E_critical.reshape(1,rho_size)
time = time.reshape(1,1)
growth_rate = np.array(growth_rate).reshape(1,rho_size)
runaway_density = np.array(runaway_density).reshape(1,rho_size)
runaway_current = np.array(runaway_current).reshape(1,rho_size)
Distribution = np.array([np.transpose(Distribution[0,:,:])])
PBig = np.array([np.transpose(PBig[0,:,:])])
XiBig = np.array([np.transpose(XiBig[0,:,:])])

# Create dictionaries of the hdf5 input parameters
temperature = {"Name": 'temperature', "Data": temperature}
density = {"Name": 'density', "Data":  density}
EHat = {"Name": 'EHat', "Data":  EHat}
Z_eff = {"Name": 'Z_eff', "Data":  Z_eff}
B0 = {"Name": 'B0', "Data":  B0}
rhoTor = {"Name": 'rhoTor', "Data":  rhoTor}
E_parallel = {"Name": 'E_parallel', "Data":  E_parallel}
E_critical = {"Name": 'E_critical', "Data":  E_critical}
time = {"Name": 'time', "Data":  time}
growth_rate = {"Name": 'growth_rate', "Data":  growth_rate}
runaway_density = {"Name": 'runaway_density', "Data":  runaway_density}
runaway_current = {"Name": 'runaway_current', "Data":  runaway_current}
Distribution = {"Name": 'Distribution', "Data":  Distribution}
PBig = {"Name": 'PBig', "Data":  PBig}
XiBig = {"Name": 'XiBig', "Data":  XiBig}

# Put dictionaries into a list
hdf5_param_data = [temperature, density, EHat, Z_eff, B0, rhoTor, E_parallel, E_critical, time, growth_rate, runaway_density, runaway_current]
hdf5_dist_data = [Distribution, PBig, XiBig]

# Write data to hdf5 file
hdf5Write.write_params(shot, run, hdf5_param_data)
hdf5Write.write_dist(shot, run, hdf5_dist_data)