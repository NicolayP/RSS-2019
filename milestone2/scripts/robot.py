#!/usr/bin/env python

import rospy
import rospkg
import numpy as np
import tf

# Message types
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist

from gazebo_msgs.msg import ModelStates

from utile import Map
from controller import Controller

from milestone2.srv import RRTsrv, RRTsrvResponse

from milestone2.msg import Goal

# initial position in the map as per the brief
INITIAL_X = 0.561945
INITIAL_Y = 0.509381
INITIAL_YAW = 0.039069

# relative path from package directory
MAP_FILE = "/maps/rss_offset.json"

NUM_RAYS = 8
NUM_PARTICLES = 50

PUBLISH_RATE = 0.1

ODOM_RATE = 30

NOISE_MOVE = 0.05
NOISE_TURN = 0.05
NOISE_SENSE = 0.5

MAX_VAL = 150

class Robot(object):
    """
    Robot class used to represent particles and simulate the robot to
    test the particles.
    """
    def __init__(self, map, nb_p, x, y, yaw, nb_rays = 8):
        """
        Initializes a particle/robot.
        input:
        ------
            - map: a map object reference.
        """
        # initialise
        rospy.init_node("milestone2", anonymous=True)

        # subscribe
        #rospy.Subscriber("scan", LaserScan, self.scanCallback)
        #rospy.Subscriber("odom", Odometry, self.odomCallback)
        rospy.Subscriber("gazebo/model_states", ModelStates, self.gazeboCallback)
        # Allows to set a goal
        rospy.Subscriber("set_goal", Goal, self.setGoal)
        # Pose publisher, initialise message
        # TODO: UNCOMMENT THIS
        #self.pose_msg = Twist()
        #self.pose_msg.linear.x = x
        #self.pose_msg.linear.y = y
        #self.pose_msg.angular.z = yaw
        # timer for pose publisher
        # TODO: UNCOMMENT THIS
        #self.pose_pub = rospy.Publisher('pf_pose', Twist, queue_size = 10)
        #rospy.Timer(rospy.Duration(PUBLISH_RATE), self.pubPose)

        # Publisher for cmd vel
        self.vel_msg = Twist()
        self.vel_msg.linear.x = 0
        self.vel_msg.angular.z = 0
        self.vel_pub = rospy.Publisher('cmd_vel', Twist, queue_size = 10)
        rospy.Timer(rospy.Duration(PUBLISH_RATE), self.pubVel)

        # set initial position
        self.x = x
        self.y = y
        self.yaw = yaw

        # Initialise particle filter
        self.nb_rays = nb_rays
        self.map = map
        # self.particle_filter = ParticleFilter(map, nb_p, x, y, yaw, nb_rays)
        self.controller = Controller()

        rospy.loginfo("Started robot node")
        while not rospy.is_shutdown():
            rospy.sleep(10)
        return

    def setGoal(self, msg):
        rospy.loginfo("received new goal {}".format(msg.goal))
        rospy.loginfo("Waiting for rrt service...")
        rospy.wait_for_service('rrt')
        rospy.loginfo("Ask for a path")
        try:
            rrt = rospy.ServiceProxy('rrt', RRTsrv)
            resp = rrt([self.x, self.y], msg.goal)
            path = np.array(resp.path).reshape((-1,2))
            rospy.loginfo("Following new path...")
            self.controller.setPath(path)
            self.followPath()
        except rospy.ServiceException, e:
            print("Service call failed: %s"%e)
            return

    def followPath(self):
        rospy.loginfo("Enter path follow")
        rospy.loginfo(self.controller.isDone(self.x, self.y))
        while not self.controller.isDone(self.x, self.y):
            v, w = self.controller.getSpeed(self.x, self.y, self.yaw)
            self.vel_msg.linear.x = v
            self.vel_msg.angular.z = w
        self.vel_msg.linear.x = 0
        self.vel_msg.angular.z = 0

    def gazeboCallback(self, msg):
        j = 0
        for i, s in enumerate(msg.name):
            if s == "turtlebot3":
                j = i
        pose = msg.pose[j]
        self.x = pose.position.x
        self.y = pose.position.y
        orientation = (
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w
        )
        self.yaw = tf.transformations.euler_from_quaternion(orientation)[2]

    def scanCallback(self, msg):

        # get the measurements for the specified number of points out of the scan information
        indexes = np.rint(np.linspace(0, 360 - 360/self.nb_rays, self.nb_rays)).astype(int)
        m = np.array(msg.ranges)
        measure = m[indexes]

        # update position estimation
        # TODO UNCOMMENT THIS
        #self.poseEstimationUpdate(measure)
        return

    def odomCallback(self, msg):

        # add the received position increment to the particles
        vel = msg.twist.twist
        self.particle_filter.actionUpdate(vel.linear.x, vel.linear.y, vel.angular.z)

        values = [vel.linear.x, vel.linear.y, vel.angular.z]
        self.dict.update({str(self.counter) : values})
        self.counter+=1
        self.dumpData("values.json")

        return

    def poseEstimationUpdate(self, measurements):

        self.particle_filter.measurementUpdate(measurements)
        self.particle_filter.particleUpdate()
        x, y, yaw = self.particle_filter.estimate()

        rospy.logdebug("x = {}, y = {}, yaw = {}".format(x, y, yaw))

        self.pose_msg.linear.x = x
        self.pose_msg.linear.y = y
        self.pose_msg.angular.z = yaw
        return

    def pubPose(self, event):
        self.pose_pub.publish(self.pose_msg)
        return

    def pubVel(self, event):
        self.vel_pub.publish(self.vel_msg)
        return

    def __str__(self):
        return "x {}, y {}, yaw {} ".format(self.x, self.y, self.yaw)

    def setPose(self, x, y, yaw):
        """
        Sets a new pose for the robot.
        input:
        ------
            - x: the new x position.
            - y: the new y position.
            - yaw: the new yaw angle.
        output:
        -------
            None
        """
        self.x = x
        self.y = y
        self.yaw = yaw
        return

def main():

    rospack = rospkg.RosPack()
    path = rospack.get_path('milestone2')
    map = Map(path + MAP_FILE)
    r = Robot(map, NUM_PARTICLES, INITIAL_X, INITIAL_Y, INITIAL_YAW, NUM_RAYS)

if __name__ == "__main__":
    main()
