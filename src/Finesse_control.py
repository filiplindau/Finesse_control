'''
Created on Sep 3, 2012

@author: Filip Lindau
'''

import serial
import logging
import time

logging.basicConfig(level=logging.DEBUG)

class Finesse_control():
    '''
    Serial control of a Laser Quantum Finesse laser. 
    
    The laser is connected to the serial port supplied in the constructor
    or in the connect command. The connection is closed after every command. 
    '''
    def __init__(self, port=0):
        self.port = port
        self.device = None
        
        self.closeFlag = False
        
    def connect(self, port):
        self.port = port
        ptmp = port
        if type(ptmp) == str:
            ptmp = ''.join(('//./', port))
        try:
            if self.device != None:
                self.close()
            self.device = serial.Serial(port, baudrate=19200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1)
        except IOError, e:
            self.device = None
            logging.exception(''.join(('Connect: ', str(e))))
            raise
        
    def close(self):
        if self.device != None:
            if self.device.isOpen() == True:
                self.device.close()
                
    def sendCommand(self, cmd, response=True, length=20):
        if self.device == None:
            self.connect(self.port)
        if self.device != None:
            try:
                if self.device.isOpen() == False:
                    self.device.open()
                self.device.write(cmd)
                p = self.device.readline(length)
                if response == True:
                    if p == None or p == '\r\n':
                        # Try one more time...
                        port = self.port
                        self.close()
                        self.connect(port)
                        if self.device != None:
                            if self.device.isOpen() == False:
                                self.device.open()
                            self.device.write(cmd)
                            p = self.device.readline(length)
                else:
                    if p == None:
                        # Try one more time...
                        port = self.port
                        self.close()
                        self.connect(port)
                        if self.device != None:
                            if self.device.isOpen() == False:
                                self.device.open()
                            self.device.write(cmd)
                            p = self.device.readline(length)
                if self.closeFlag == True:
                    self.device.close()
                return p
            except serial.SerialTimeoutException, e:
                logging.exception(''.join(('sendCommand: ', cmd, str(e))))
                raise
        else:
            logging.exception('Could not connect to device.')
            raise IOError('Could not connect to device.')

            
    def getPower(self):
        s = 'POWER?\n\r'
        p = self.sendCommand(s)
        if 'W' in p:
            try:
                data = float(p[0:p.index('W')])
            except:
                p = self.sendCommand(s)
                data = float(p[0:p.index('W')])
            unit = p[p.index('W')]
            return (data, unit)
        else:
            raise ValueError(''.join(('Power unit not found', p)))
            
    def setPower(self, power):
        if power > 0 or power < 8:
            s = 'POWER={0:1.3f}\n\r'.format(power)
            p = self.sendCommand(s, response=False)
            if p == '\r\n':
                return True
            else:
                return False
        else:
            logging.exception('Power out of range. Must be in the range 0-8 W.')
            raise ValueError('Power out of range. Must be in the range 0-8 W.')
        
                
    def getCurrent(self):
        s = 'CURRENT?\n\r'
        p = self.sendCommand(s, response=True)
        try:
            data = float(p[1:6])
        except:
            p = self.sendCommand(s, response=True)
            data = float(p[1:6])
        unit = p[6]
        return (data, unit)
            
                
    def getStatus(self):
        s = 'STATUS?\n\r'
        p = self.sendCommand(s)
        if p[:-2].lower() == 'enabled':
            data = True
        else:
            data = False
        return (data, p[:-2])
                
    def getShutter(self):
        s = 'SHUTTER?\n\r'
        p = self.sendCommand(s)
        if p[:-2].lower() == 'shutter open':
            data = True
        else:
            data = False
        return (data, p[:-2])
                
    def getInterlock(self):
        s = 'INTERLOCK?\n\r'
        p = self.sendCommand(s)
        if 'error' in p[:-2].lower():
            raise NotImplementedError('Interlock readout not available on this model.')
        if p[:-2].lower() == 'enabled':
            data = True
        else:
            data = False
        return (data, p[:-2])
        
    def getLaserTemperature(self):
        s = 'HTEMP?\n\r'
        p = self.sendCommand(s)
        try:
            data = float(p[1:7])
        except:
            p = self.sendCommand(s)
            data = float(p[1:7])
        unit = p[7]
        return (data, unit)
        
    def getPSUTemperature(self):
        s = 'PSUTEMP?\n\r'
        p = self.sendCommand(s)
        if 'error' in p[:-2].lower():
            raise NotImplementedError('PSU temperature readout not available on this model.')
        data = float(p[1:7])
        unit = p[7]
        return (data, unit)
            
    def getSerial(self):
        s = 'SERIAL?\n\r'
        p = self.sendCommand(s)
        data = int(p[1:6])
        unit = '#'
        return (data, unit)

    def getSoftwareVersion(self):
        s = 'SOFTVER?\n\r'
        p = self.sendCommand(s)
        data = p[:-2]
        unit = '#'
        return (data, unit)
            
    def openShutter(self):
        s = 'SHUTTER OPEN\n\r'
        p = self.sendCommand(s)
        if p == '\r\n':
            return True
        else:
            return False

    def closeShutter(self):
        s = 'SHUTTER CLOSE\n\r'
        p = self.sendCommand(s)
        if p == '\r\n':
            return True
        else:
            return False
            
    def turnLaserOn(self):
        s = 'LASER=ON\n\r'
        p = self.sendCommand(s)
        if p == '\r\n':
            return True
        else:
            return False

    def turnLaserOff(self):
        s = 'LASER=OFF\n\r'
        p = self.sendCommand(s)
        if p == '\r\n':
            return True
        else:
            return False
            
    def getLaserTimers(self):
        s = 'TIMERS?\n\r'
        tLength = 37
        p0 = self.sendCommand(s, length=tLength)
        p1 = self.device.readline(tLength)        
        p2 = self.device.readline(tLength)
        p3 = self.device.readline(tLength)      # Extra newline at the end
                            
        timers = [(int(p0[-12:-7].rsplit(':', 1)[-1]), 'PSU minutes'),
                  (int(p1[-14:-7].rsplit(':', 1)[-1]), 'Laser enabled minutes'),
                  (int(p2[-14:-7].rsplit(':', 1)[-1]), 'Laser threshold minutes')]
        return timers
            
    def resetLaser(self):
        s = 'RESET\n\r'
        p = self.sendCommand(s)
        if p == '\r\n':
            return True
        else:
            return False

        
if __name__ == '__main__':
    fc = Finesse_control('com1')
            
