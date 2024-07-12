####################################################################
# PACKAGES REQUIRED
####################################################################

# pymeasure
# matplotlib
# PyQt5
# scipy
# pylablib (use lightweight installation)
# nidaqmx

####################################################################
# IMPORTS
####################################################################

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
import sys
from time import sleep, time
from datetime import datetime
from pymeasure.log import console_log
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results, Metadata
from pymeasure.experiment import BooleanParameter, IntegerParameter, FloatParameter, Parameter, ListParameter
import matplotlib.pyplot as plt
import numpy as np
import nidaqmx
import nidaqmx.system
import os
import shutil
import random
import json

####################################################################
# GENERAL FUNCTIONS
####################################################################

def LoadSampleList():
	# opening the file in read mode 
	my_file = open("Samples.txt", "r") 
	
	# reading the file 
	data = my_file.read() 
	
	# Split text by newline
	return data.split("\n") 

def LoadSettings():
	# opening the file in read mode 
	my_file = open("settings.ini", "r") 
	
	# reading the file 
	data = my_file.read() 

	return json.loads(data)
	

####################################################################
# GLOBALS
####################################################################

# Variable used to store data read from text file on startup
samplesList = LoadSampleList()


####################################################################
# MAIN PROCEDURE
####################################################################

class MainProcedure(Procedure):
	# PARAMETERS
	################################################################
	system = nidaqmx.system.System.local()

	# User
	user = Parameter('User', default="")

	# Samples
	samples = ListParameter('Samples', choices=samplesList)

	# DAQ Name
	# daqName = Parameter('DAQ Name', default="Dev1")
	daqName = ListParameter('DAQ Name', choices=system.devices.device_names)

    # Input Port
	inputPort = Parameter('Input Port', default="ai0")

	# Output Port
	outputPort = Parameter('Output Port', default="ao0")

	# Data Points to Acquire
	dataPoints = IntegerParameter('Data Points to Acquire', default=10)

	# Sample Wait Time
	waitTime = FloatParameter('Sample Wait Time', units='s', default=0.1)

	# Data Bias Toggle
	dataBiasToggle = BooleanParameter('Data Bias Toggle', default=False) 

	# Manual Data Bias
	manualDataBias = FloatParameter('Manual Data Bias', group_by='dataBiasToggle', group_condition=lambda v: v == True, default=0.0)

	# Auto-Bias
	autoBiasToggle = BooleanParameter('Auto-Bias Data', group_by='dataBiasToggle', group_condition=lambda v: v == True, default=False) 

	# METADATA
	################################################################
	
	starttime = Metadata('Start Time', default="")
	dataBias = Metadata('Data Bias', default= 0)

	# VARIABLES
	################################################################	
	# Defines what data will be emitted for the main window
	DATA_COLUMNS = ['Sample', 'Y']

	# FUNCTIONS
	################################################################
	# Called at the start of the procedure. Can be used to initialise instruments if needed
	def startup(self):
		log.info("Startup")

		# Acquire what Data Bias to apply
		if (self.dataBiasToggle):
			# See if the program should attempt to auto obtain the bias 
			if (self.autoBiasToggle):
				log.info("Auto-acquiring bias")

				# Create NIDAQMX task
				with nidaqmx.Task() as task:
					task.ai_channels.add_ai_voltage_chan("{}/{}".format(self.daqName, self.inputPort))

					backgroundSum = 0

					# For 10 points
					for i in range(10):
						# Read the analogue input
						backgroundSum += task.read()

						# Wait
						sleep(self.waitTime)

					self.dataBias = -(backgroundSum / 10.0)
			else:
				self.dataBias = self.manualDataBias
		# No Bias
		else :
			self.dataBias = 0

		# Set the measurement start time
		self.starttime = datetime.now()

	# Main body of the procedure
	def execute(self):
		log.info("Reading Input")

		# Create NIDAQMX task
		with nidaqmx.Task() as task:
			task.ai_channels.add_ai_voltage_chan("{}/{}".format(self.daqName, self.inputPort))

			# For N points
			for i in range(self.dataPoints):
				# Read the analogue input
				data = task.read()

				# Add bias
				data += self.dataBias

				# Send the results to the main window
				self.emit('results', {'Sample': i + 1, 'Y': data})
				
				# Wait
				sleep(self.waitTime)

	# Called at the end of the procedure
	def shutdown(self):
		log.info("Ending Procedure")

####################################################################
# MAIN WINDOW
####################################################################

class MainWindow(ManagedWindow):
	def __init__(self):
		super().__init__(
			procedure_class=MainProcedure,
			inputs=['user', 'samples', 'daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime', 'dataBiasToggle', 'autoBiasToggle', 'manualDataBias'],
			displays=['user', 'samples', 'daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime', 'dataBiasToggle'],
			x_axis='Sample',
			y_axis='Y',
			# sequencer=True,
            # sequencer_inputs=['daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime'],
			# hide_groups = True,
			# directory_input=True,
			inputs_in_scrollarea = True
			)
		self.setWindowTitle('DAQ Test Program')

		self.settings = LoadSettings()

		# self.filename = os.getlogin() + '_'
		self.filename = self.settings["default_filename"]  # Sets default filename
		self.directory = self.settings["default_directory"] # Sets default directory
		self.store_measurement = True # Controls the 'Save data' toggle
		self.file_input.extensions = ["dat", "csv", "txt", "data"]  # Sets recognized extensions, first entry is the default extension
		self.file_input.filename_fixed = ~self.settings["editable_filename"] # Controls whether the filename-field is frozen (but still displayed)

####################################################################
# MAIN
####################################################################

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
