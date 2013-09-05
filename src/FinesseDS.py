#	"$Name:  $";
#	"$Header:  $";
#=============================================================================
#
# file :        FinesseDS.py
#
# description : Python source for the FinesseDS and its commands. 
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                FinesseDS are implemented in this file.
#
# project :     TANGO Device Server
#
# $Author:  $
#
# $Revision:  $
#
# $Log:  $
#
# copyleft :    European Synchrotron Radiation Facility
#               BP 220, Grenoble 38043
#               FRANCE
#
#=============================================================================
#  		This file is generated by POGO
#	(Program Obviously used to Generate tango Object)
#
#         (c) - Software Engineering Group - ESRF
#=============================================================================
#


import PyTango
import sys
import Finesse_control as fc
import threading
import Queue
import time

class LaserData():
	def __init__(self):
			self.current = None
			self.power = None
			self.status = None
			self.shutter = None
			self.interlock = None
			self.laserTemperature = None
			self.psuTemperature = None	
			self.psuTime = None
			self.laserEnabledTime = None
			self.laserThresholdTime = None

#==================================================================
#   FinesseDS Class Description:
#
#         Controls a Laser Quantum Finesse DPSS laser.
#
#==================================================================
# 	Device States Description:
#
#   DevState.ON :       Connected to laser. Laser power on, shutter open.
#   DevState.OFF :      Connected to laser, laser power off, shutter closed
#   DevState.STANDBY :  The laser is on, the shutter is closed.
#   DevState.FAULT :    An error was detected. Probably communication.
#   DevState.DISABLE :  The laser is disabled due to interlock condition.
#   DevState.ALARM :    The device is in an ALARM state due to an attribute being out of limits.
#   DevState.UNKNOWN :  Disconnected from laser power supply
#==================================================================


class FinesseDS(PyTango.Device_4Impl):

#--------- Add you global variables here --------------------------

#------------------------------------------------------------------
#	Device constructor
#------------------------------------------------------------------
	def __init__(self, cl, name):
		PyTango.Device_4Impl.__init__(self, cl, name)
		FinesseDS.init_device(self)

#------------------------------------------------------------------
#	Device destructor
#------------------------------------------------------------------
	def delete_device(self):
		print "[Device delete_device method] for device", self.get_name()
#		self.disconnectLaser()
		self.stopMonitorFlag = True
		self.monitorThread.join(10)


#------------------------------------------------------------------
#	Device initialization
#------------------------------------------------------------------
	def init_device(self):
		print "In ", self.get_name(), "::init_device()"
		self.set_state(PyTango.DevState.OFF)
		try:
			self.get_device_properties(self.get_device_class())
			self.info_stream('Checking if self.Port is available...')
			self.Port			
			self.info_stream('ok.')
		except AttributeError:
			self.error_stream('Property port not defined')
			self.set_state(PyTango.DevState.FAULT)
			self.set_status('init failed - Property "port" not defined')
			
		try:
			self.device = fc.Finesse_control(self.Port)
		except Exception, e:
			self.error_stream('Property port not defined')
			self.device = None
			self.set_state(PyTango.DevState.FAULT)
			self.set_status('init failed - Property "port" not defined')

		self.laserData = LaserData()
		self.stopMonitorFlag = False
		self.monitorThread = threading.Thread()
		threading.Thread.__init__(self.monitorThread, target=self.hardwareMonitor)
		
		self.monitorThread.start()

#------------------------------------------------------------------
#	Always excuted hook method
#------------------------------------------------------------------
	def always_executed_hook(self):
#		print "In ", self.get_name(), "::always_excuted_hook()"
		pass


#------------------------------------------------------------------
#	Device constructor
#------------------------------------------------------------------



	def processFault(self, cmd, startingE=None):
		s = ''.join(('Fault condition. ', str(cmd), ', error ', str(startingE), ' Processing...\n'))
		t0 = time.time()
		faultProcessFlag = True
		print 'In processFault:: ', 'command ', str(cmd), ', error ', str(startingE)
		while faultProcessFlag == True:
			time.sleep(0.5)
			try:
				self.device.close()
				faultProcessFlag = False
			except Exception, e:
				print 'Close...', str(e)
				self.set_state(PyTango.DevState.FAULT)
				self.set_status(''.join((s, 'Error closing connection')))
				faultProcessFlag = True
			if faultProcessFlag == False:
				try:
					self.device.connect(self.Port)
					faultProcessFlag = False
				except Exception, e:
					print 'Connect...', str(e)
					self.set_state(PyTango.DevState.UNKNOWN)
					self.set_status(''.join((s, 'Error connecting')))
					faultProcessFlag = True
			if faultProcessFlag == False:
				try:
					stat = self.device.getPower()
					faultProcessFlag = False
				except Exception, e:
					print 'Communicate...', str(e)
					self.set_state(PyTango.DevState.FAULT)
					self.set_status(''.join((s, 'Error receiving response')))
					faultProcessFlag = True
			if time.time() - t0 > 10:
				faultProcessFlag = False


	def hardwareCommand(self, cmd):
		# If the command is a tuple it is a 'set' command.
		if type(cmd) == tuple:
			value = cmd[1]
			cmd = cmd[0]
		if cmd == 'start':
			self.device.turnLaserOn()
		elif cmd == 'open':
			self.device.openShutter()
		elif cmd == 'close':
			self.device.closeShutter()
		elif cmd == 'off':
			self.device.turnLaserOff()
		elif cmd == 'getCurrent':
			self.laserData.current = self.device.getCurrent()
		elif cmd == 'getPower':
			self.laserData.power = self.device.getPower()
		elif cmd == 'setPower':
			self.device.setPower(value)
		elif cmd == 'getLaserTemperature':
			self.laserData.laserTemperature = self.device.getLaserTemperature()
		elif cmd == 'getShutter':
			self.laserData.shutter = self.device.getShutter()
		elif cmd == 'getStatus':
			self.laserData.status = self.device.getStatus()
		elif cmd == 'getLaserTimers':
			lt = self.device.getLaserTimers()
			self.laserData.psuTime = lt[0][0]
			self.laserData.laserEnabledTime = lt[1][0]
			self.laserData.laserThresholdTime = lt[2][0]


	def hardwareMonitor(self):
		self.q = Queue.Queue()
		
		commandList = ['getCurrent', 'getPower', 'getLaserTemperature',
					'getShutter', 'getStatus', 'getLaserTimers']
		
		nextCommand = 0
		
		while self.stopMonitorFlag == False:
			t0 = time.time()
			try:
				# See if there is a command issued by tango
				cmd = self.q.get_nowait()
			except Queue.Empty:
				# The command queue was empty so we can add read command
				cmd = commandList[nextCommand]
				nextCommand = (nextCommand + 1) % commandList.__len__()
			try:
				# Send the command to hardware and time it
				# t0 = time.time()
				self.hardwareCommand(cmd)
				dt = time.time() - t0
				if dt > 0.5:
					# Slow execution time. Preventive measures should be taken
					pass
			except Exception, e:
				self.processFault(cmd, e)
				
			
			# Adjust the Tango state based on the lastest reading
			try:
				self.adjust_State()
			except Exception, e:
				print ('Error checking state. ', str(e))
				

		# Clear queue when we exit (no need to finish all the tasks
		with self.q.mutex:
			self.q.queue.clear()
		self.q.join()


	def adjust_State(self):
		'''
		Updates the state based on the information in the laserData variable.
		'''
		
		if self.get_state() != PyTango.DevState.ALARM:
			# Do not change state if we are in ALARM
			if self.laserData.interlock == None:
				if self.laserData.status != None and self.laserData.shutter != None:
					if self.laserData.status[0] == True and self.laserData.shutter[0] == False:
						self.set_state(PyTango.DevState.STANDBY)
						self.set_status('Laser on, shutter closed')
					elif self.laserData.status[0] == True and self.laserData.shutter[0] == True:
						self.set_state(PyTango.DevState.ON)
						self.set_status('Laser on, shutter open')
					elif self.laserData.status[0] == False:
						self.set_state(PyTango.DevState.OFF)
						self.set_status('Laser off')
					else:
						self.set_state(PyTango.DevState.FAULT)
						self.set_status('State data not initialized')
					
			else:
				if self.laserData.status != None and self.laserData.shutter != None:
					if self.laserData.interlock[0] == False:
						self.set_state(PyTango.DevState.DISABLE)
						self.set_status('Interlock tripped')
					elif self.laserData.status[0] == True and self.laserData.shutter[0] == False:
						self.set_state(PyTango.DevState.STANDBY)
						self.set_status('Laser on, shutter closed')
					elif self.laserData.status[0] == True and self.laserData.shutter[0] == True:
						self.set_state(PyTango.DevState.ON)
						self.set_status('Laser on, shutter open')
					elif self.laserData.status[0] == False:
						self.set_state(PyTango.DevState.OFF)
						self.set_status('Laser off')
					else:
						self.set_state(PyTango.DevState.FAULT)
						self.set_status('State data not initialized')


#------------------------------------------------------------------
#	Read Attribute Hardware
#------------------------------------------------------------------
	def read_attr_hardware(self, data):
#		print "In ", self.get_name(), "::read_attr_hardware()"
		pass

#==================================================================
#
#	FinesseDS read/write attribute methods
#
#==================================================================




#------------------------------------------------------------------
#	Read Current attribute
#------------------------------------------------------------------
	def read_Current(self, attr):
		print "In ", self.get_name(), "::read_Current()"
		
		#	Add your own code here
		
		attr_Current_read = self.laserData.current
		attr.set_value(attr_Current_read[0])


#------------------------------------------------------------------
#	Write Current attribute
#------------------------------------------------------------------
	def write_Current(self, attr):
		print "In ", self.get_name(), "::write_Current()"
		data = []
		attr.get_write_value(data)
		print "Attribute value = ", data

		#	Add your own code here


#---- Current attribute State Machine -----------------
	def is_Current_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read Power attribute
#------------------------------------------------------------------
	def read_Power(self, attr):
		print "In ", self.get_name(), "::read_Power()"
		
		#	Add your own code here
		
		attr_Power_read = self.laserData.power
		attr.set_value(attr_Power_read[0])


#------------------------------------------------------------------
#	Write Power attribute
#------------------------------------------------------------------
	def write_Power(self, attr):
		print "In ", self.get_name(), "::write_Power()"
		data = attr.get_write_value()
		print "Attribute value = ", data

		#	Add your own code here
		self.q.put(('setPower', data))


#---- Power attribute State Machine -----------------
	def is_Power_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read LaserTemperature attribute
#------------------------------------------------------------------
	def read_LaserTemperature(self, attr):
		print "In ", self.get_name(), "::read_LaserTemperature()"
		
		#	Add your own code here
		
		attr_LaserTemperature_read = self.laserData.laserTemperature

		attr.set_value(attr_LaserTemperature_read[0])
		if attr.check_alarm() == True:
			if attr.is_max_alarm() == True or attr.is_min_alarm() == True:
				self.q.put('off')
				self.q.put('close')


#---- LaserTemperature attribute State Machine -----------------
	def is_LaserTemperature_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read PowerSupplyTemperature attribute
#------------------------------------------------------------------
	def read_PowerSupplyTemperature(self, attr):
		print "In ", self.get_name(), "::read_PowerSupplyTemperature()"
		
		#	Add your own code here
		
		attr_PowerSupplyTemperature_read = self.laserData.psuTemperature
		if attr_PowerSupplyTemperature_read == None:
			attr.set_value(0)
		else:
			attr.set_value(attr_PowerSupplyTemperature_read[0])


#---- PowerSupplyTemperature attribute State Machine -----------------
	def is_PowerSupplyTemperature_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read PSUTime attribute
#------------------------------------------------------------------
	def read_PSUTime(self, attr):
		print "In ", self.get_name(), "::read_PSUTime()"
		
		#	Add your own code here
		
		if self.laserData.psuTime != None:
			attr_PSUTime_read = self.laserData.psuTime
		else:
			attr_PSUTime_read = 0.0
		attr.set_value(attr_PSUTime_read)


#---- PSUTime attribute State Machine -----------------
	def is_PSUTime_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read LaserEnabledTime attribute
#------------------------------------------------------------------
	def read_LaserEnabledTime(self, attr):
		print "In ", self.get_name(), "::read_LaserEnabledTime()"
		
		#	Add your own code here
		
		if self.laserData.laserEnabledTime != None:
			attr_LaserEnabledTime_read = self.laserData.laserEnabledTime
		else:
			attr_LaserEnabledTime_read = 0.0

		attr.set_value(attr_LaserEnabledTime_read)


#---- LaserEnabledTime attribute State Machine -----------------
	def is_LaserEnabledTime_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Read LaserThresholdTime attribute
#------------------------------------------------------------------
	def read_LaserThresholdTime(self, attr):
		print "In ", self.get_name(), "::read_LaserThresholdTime()"
		
		#	Add your own code here
		
		if self.laserData.laserThresholdTime != None:
			attr_LaserThresholdTime_read = self.laserData.laserThresholdTime
		else:
			attr_LaserThresholdTime_read = 0.0

		attr.set_value(attr_LaserThresholdTime_read)


#---- LaserThresholdTime attribute State Machine -----------------
	def is_LaserThresholdTime_allowed(self, req_type):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True



#==================================================================
#
#	FinesseDS command methods
#
#==================================================================

#------------------------------------------------------------------
#	On command:
#
#	Description: 
#------------------------------------------------------------------
	def On(self):
		print "In ", self.get_name(), "::On()"
		#	Add your own code here
		self.q.put('start')
		self.q.put('open')


#---- On command State Machine -----------------
	def is_On_allowed(self):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Off command:
#
#	Description: 
#------------------------------------------------------------------
	def Off(self):
		print "In ", self.get_name(), "::Off()"
		#	Add your own code here
		self.q.put('off')
		self.q.put('close')


#---- Off command State Machine -----------------
	def is_Off_allowed(self):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Open command:
#
#	Description: 
#------------------------------------------------------------------
	def Open(self):
		print "In ", self.get_name(), "::Open()"
		#	Add your own code here
		self.q.put('open')


#---- Open command State Machine -----------------
	def is_Open_allowed(self):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Close command:
#
#	Description: 
#------------------------------------------------------------------
	def Close(self):
		print "In ", self.get_name(), "::Close()"
		#	Add your own code here
		self.q.put('close')


#---- Close command State Machine -----------------
	def is_Close_allowed(self):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#------------------------------------------------------------------
#	Start command:
#
#	Description: 
#------------------------------------------------------------------
	def Start(self):
		print "In ", self.get_name(), "::Start()"
		#	Add your own code here
		self.q.put('start')


#---- Start command State Machine -----------------
	def is_Start_allowed(self):
		if self.get_state() in [PyTango.DevState.FAULT,
		                        PyTango.DevState.UNKNOWN]:
			#	End of Generated Code
			#	Re-Start of Generated Code
			return False
		return True


#==================================================================
#
#	FinesseDSClass class definition
#
#==================================================================
class FinesseDSClass(PyTango.DeviceClass):

	#	Class Properties
	class_property_list = {
		}


	#	Device Properties
	device_property_list = {
		'Port':
			[PyTango.DevString,
			"Serial port that the laser is connected to.",
			[ "COM0" ] ],
		}


	#	Command definitions
	cmd_list = {
		'On':
			[[PyTango.DevVoid, ""],
			[PyTango.DevVoid, ""]],
		'Off':
			[[PyTango.DevVoid, ""],
			[PyTango.DevVoid, ""]],
		'Open':
			[[PyTango.DevVoid, ""],
			[PyTango.DevVoid, ""]],
		'Close':
			[[PyTango.DevVoid, ""],
			[PyTango.DevVoid, ""]],
		'Start':
			[[PyTango.DevVoid, ""],
			[PyTango.DevVoid, ""]],
		}


	#	Attribute definitions
	attr_list = {
		'Current':
			[[PyTango.DevDouble,
			PyTango.SCALAR,
			PyTango.READ_WRITE],
			{
				'label':"current",
				'unit':"%",
				'display unit':"%",
				'max value':100,
				'min value':0,
				'description':"Current through the pump diodes as percentage of maximum.",
				'Polling period':500,
			} ],
		'Power':
			[[PyTango.DevDouble,
			PyTango.SCALAR,
			PyTango.READ_WRITE],
			{
				'label':"power",
				'unit':"W",
				'display unit':"W",
				'max value':10,
				'min value':0,
				'description':"Laser power level in W.",
				'Memorized':"true_without_hard_applied",
				'Polling period':500,
			} ],
		'LaserTemperature':
			[[PyTango.DevDouble,
			PyTango.SCALAR,
			PyTango.READ],
			{
				'unit':"degC",
				'display unit':"degC",
				'max alarm':27,
				'min alarm':15,
				'max warning':24,
				'min warning':23,
				'description':"Temperature of the laser head.",
				'Polling period':500,
			} ],
		'PowerSupplyTemperature':
			[[PyTango.DevDouble,
			PyTango.SCALAR,
			PyTango.READ],
			{
				'Polling period':2000,
			} ],
		'PSUTime':
			[[PyTango.DevLong,
			PyTango.SCALAR,
			PyTango.READ],
			{
				'unit':"min",
				'Polling period':60000,
			} ],
		'LaserEnabledTime':
			[[PyTango.DevLong,
			PyTango.SCALAR,
			PyTango.READ],
			{
				'unit':"min",
				'Polling period':60000,
			} ],
		'LaserThresholdTime':
			[[PyTango.DevLong,
			PyTango.SCALAR,
			PyTango.READ],
			{
				'Polling period':60000,
			} ],
		}


#------------------------------------------------------------------
#	FinesseDSClass Constructor
#------------------------------------------------------------------
	def __init__(self, name):
		PyTango.DeviceClass.__init__(self, name)
		self.set_type(name);
		print "In FinesseDSClass  constructor"

#==================================================================
#
#	FinesseDS class main method
#
#==================================================================
if __name__ == '__main__':
	try:
		py = PyTango.Util(sys.argv)
		py.add_TgClass(FinesseDSClass, FinesseDS, 'FinesseDS')

		U = PyTango.Util.instance()
		U.server_init()
		U.server_run()

	except PyTango.DevFailed, e:
		print '-------> Received a DevFailed exception:', e
	except Exception, e:
		print '-------> An unforeseen exception occured....', e
