#!/usr/bin/env python

import rospy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from numpy import concatenate
import numpy as np


class RobotController:

    LINEAR_SPEED=0.1
    TURN_SPEED=np.deg2rad(45)

    def __init__(self):
        self.pub = rospy.Publisher('cmd_vel',Twist,queue_size = 10)
        self.mc = Twist()

    def turn(self, degrees):

        # if negative direction sent, use reverse speed
        if degrees > 0:        
            self._command_motor(0, -self.TURN_SPEED)
        else:
            self._command_motor(0, self.TURN_SPEED)

        # wait for the right amount of time
        t = np.abs(degrees) / self.TURN_SPEED
        rospy.loginfo("turning for {}".format(t))
        rospy.sleep(t)

        self._stop()

    def move(self, meters):
        
        self._command_motor(self.LINEAR_SPEED, 0)

        # wait for the right amount of time
        t = meters / self.LINEAR_SPEED
        rospy.loginfo("moving for {}".format(t))
        rospy.sleep(t)

        self._stop()

    def _stop(self):
        self._command_motor(0,0)

    def _command_motor(self, lin, turn):
       
        # set speed
        self.mc.linear.x = lin
        self.mc.angular.z = turn

        # publish message
        self.pub.publish(self.mc)

def navigate(rc): 
    
    # delay to avoid message loss
    rospy.sleep(2)

    # send commands
    rc.move(1.0)
    rc.turn(np.deg2rad(90))
    rc.move(1.0)
    rc.turn(-np.deg2rad(90))
    rc.move(1.0)      

def main():

    # initialise
    rospy.init_node("Navigate", anonymous=True)

    rc = RobotController()
    navigate(rc)

if __name__ == '__main__':
    main()
