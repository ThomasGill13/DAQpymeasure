####################################################################
# PACKAGES REQUIRED
####################################################################

# pymeasure
# matplotlib
# PyQt5
# scipy
# pylablib (use lightweight installation)
# nidaqmx
# pywin32

####################################################################
# IMPORTS
####################################################################

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
import sys
import tempfile
from time import sleep
from pymeasure.log import console_log
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results
from pymeasure.experiment import BooleanParameter, IntegerParameter, FloatParameter, Parameter, ListParameter
import matplotlib.pyplot as plt
import numpy as np
import nidaqmx
import os
import shutil
import win32ui

####################################################################
# GENERAL FUNCTIONS
####################################################################

def ChooseSaveFile():
	# Choose file to save
	dlg = win32ui.CreateFileDialog( 1, ".dat", "", 0, "Data Files (*.dat)|*.dat|All Files (*.*)|*.*|")
	dlg.DoModal()
	return dlg.GetPathName()

####################################################################
# MAIN PROCEDURE
####################################################################

class MainProcedure(Procedure):
	# DAQ Name
	daqName = Parameter('DAQ Name', default="Dev1")

    # Input Port
	inputPort = Parameter('Input Port', default="ai0")

	# Output Port
	outputPort = Parameter('Output Port', default="ao0")

	# Data Points to Acquire
	dataPoints = IntegerParameter('Data Points to Acquire', default=10)

	# Sample Wait Time
	waitTime = FloatParameter('Sample Wait Time', units='s', default=0.1)

	# Defines what data will be emitted for the main window
	DATA_COLUMNS = ['Sample', 'Y']

	# Called at the start of the procedure. Can be used to initialise instruments if needed
	def startup(self):
		log.info("Startup")

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

				# Send the results to the main window
				self.emit('results', {'Sample': i + 1, 'Y': data})
				
				# Wait
				sleep(self.waitTime)

	# Called at the end of the procedure
	def shutdown(self):
		self.trySaveFile()
		log.info("Ending Procedure")

	# Should be called by the main window program
	# Assigns the path to the current temporary file
	def setTempFile(self, tempFilePath):
		self.curTempFile = tempFilePath

	def trySaveFile(self):
		# Bring up a save dialog
		savepath = ChooseSaveFile()
			
		# Check that a file was selected
		if savepath != '':
			log.info("Saving data to " + savepath)
				
			# Copy the current temp file to the savepath
			shutil.copy(self.curTempFile, savepath)

		# No file selected
		else:
			log.info("Data not saved")

####################################################################
# MAIN WINDOW
####################################################################

class MainWindow(ManagedWindow):
	def __init__(self):
		super().__init__(
			procedure_class=MainProcedure,
			inputs=['daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime'],
			displays=['daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime'],
			x_axis='Sample',
			y_axis='Y',
			# sequencer=True,
            # sequencer_inputs=['daqName', 'inputPort', 'outputPort', 'dataPoints', 'waitTime'],
			# hide_groups = True,
			# directory_input=True,
			inputs_in_scrollarea = True
			)
		self.setWindowTitle('DAQ Test Program')

				# Get path to temp folder
		self.tempDir = os.path.join(tempfile.gettempdir(), "daqpytemp")

		# Check if temp folder exists
		if os.path.exists(self.tempDir):
			# Remove it (this is to get rid of any old temp files)
			shutil.rmtree(self.tempDir)

		# Create temp folder
		os.mkdir(self.tempDir)

	def queue(self, procedure=None):
		# Create temp file to save data to
		curTempFile = tempfile.mktemp(dir=self.tempDir)

		if procedure is None:
			procedure = self.make_procedure()

		# Pass the name of the current temporary file to the procedure
		procedure.setTempFile(curTempFile)

		results = Results(procedure, curTempFile)
		experiment = self.new_experiment(results)

		# Start the experiment
		self.manager.queue(experiment)

####################################################################
# MAIN
####################################################################

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
