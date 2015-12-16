# -*- coding:utf-8 -*-
"""
Created on Jan 25, 2013

@author: Laser
"""
import PyTango as pt
import time

class EventCallback:
    def push_event(self, ev_data):
        print 'Event!!', str(ev_data)
        
if __name__ == '__main__':
    cb = EventCallback()
    dev = pt.DeviceProxy('testfel/gunlaser/finesse')
    event = dev.subscribe_event('LaserTemperature', pt.EventType.CHANGE_EVENT, cb)
    
