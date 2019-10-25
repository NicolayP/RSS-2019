#!/usr/bin/env python

import numpy as np
import json
import matplotlib.pyplot as plt
from matplotlib import collections as mc
from copy import copy as copy

# class using a vectorial represnetation for the segments
# p1 the origin and p2 - p1 the orientation and length associated
# to it.
class Segment(object):
    """
    Class to represent a vector. This class alows operation such as checking
    intersection with two vectors.
    """
    def __init__(self, p1, p2):
        """
        Segment constructor.
            input:
            ------
                - first point p1 as array [x1, y1]
                - second point p2 as array [x2, y2]
            output:
            -------
                - None
        """
        self.p1 = p1
        self.p2 = p2
        self.vec = p2 - p1

        # Store the vectors perpendicular for collision calculation
        self.perp = np.copy(self.vec)
        tmp = self.perp[0]
        self.perp[0] = -self.perp[1]
        self.perp[1] = tmp

    def __str__(self):
        return self._toArray().__str__()

    def _toArray(self):
        return np.array([self.p1, self.p2])

    def plotSeg(self, fig, ax):
        lines = [self._toArray()]
        c = [(1,0,0,1)]
        lc = mc.LineCollection(lines, linestyles='dashed', colors=c, linewidth=2)
        ax.add_collection(lc)
        ax.autoscale()
        ax.margins(0.1)
        return fig, ax

class Map(object):

    LENGTH = 5.32 # sqrt(4.25**2 + 3.20**2)
    X_LEN = 4.1
    Y_LEN = 3.05
    """
    Class representing the map. It has a set of segments.
    """
    def __init__(self, map_file):
        """
        Loads a map from a map file. The file is assumed to be  a json file
        and the structure should be as follows:
        - first entry has the key word 'segments'. This entry is an array of
        segments. A segment is an array of points and a point is an array of
        x and y coordinates.
            input:
            ------
             - map_file: path to the json map file.
        """
        self.segments = []
        with open(map_file) as json_file:
            data = json.load(json_file)
            for seg in data['segments']:
                p1 = np.array(seg[0])
                p2 = np.array(seg[1])
                s = Segment(p1, p2)
                self.segments.append(s)

    def __str__(self):
        ret = ""
        for seg in self.segments:
            ret += seg.__str__()
            ret += "\n"
        return ret

    def _createLaser(self, particle, angle):
        '''
            input:
            ------
                - particle : The Robot which is the object of the ray trace, used for position
                - angle : what angle relative to the current yaw to cast the ray through the robot
            output:
            -------
                - a segment which passes through the world map with the robot at the halfway point
                This allows us to calculate 2 data points with a single ray trace
        '''
        end_x = np.cos(angle)*self.LENGTH + particle.x
        end_y = np.sin(angle)*self.LENGTH + particle.y

        start_x = -np.cos(angle)*self.LENGTH + particle.x
        start_y = -np.sin(angle)*self.LENGTH + particle.y

        return Segment(np.array([start_x, start_y]), np.array([end_x, end_y]))

    def _createSegment(self, particle, angle):
        '''
            input:
            ------
                - particle : The Robot which is the object of the ray trace, used for position
                - angle : what angle relative to the current yaw to cast the ray through the robot
            output:
            -------
                - a segment from the particle to the outside of the map
        '''
        end_x = np.cos(angle)*self.LENGTH + particle[0]
        end_y = np.sin(angle)*self.LENGTH + particle[1]

        return Segment(np.array([particle[0], particle[1]]), np.array([end_x, end_y]))

    def _intersection(self, wall, ray):
        prod = cross(wall.vec, ray.vec)
        if prod == 0: # filter rare case of parallel
            return -1, -1

        # find scalar offsets which indicate crossover point
        t = cross((ray.p1 - wall.p1), ray.vec)/prod
        s = cross((wall.p1 - ray.p1), wall.vec)/-prod # because cross(wall.vec, ray.vec) = -cross(ray.vec, wall.vec)
        return t, s

    def minIntersections(self, particle, angle):
        '''
            input:
            ------
                - particle : The Robot which is the focus of the ray trace, used for position
                - angle : what angle relative to the current yaw to cast the ray through the robot
            output:
            -------
                - a 2rry of the pairs (point, distance), which represents the two minimum points of intersection in front of the robot and behind.
                If no valid intersection is found these points will be "None".

        Computes the intersection point between two segments according to
        [https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect]
        '''
        # TODO REVIEW used variables to store the distance when point is sufficient
        # this was to reduce the number of distance calculations, but makes the code not as clean.
        # Possibly change the WORLD_MAP.LENGTH to a World.LENGTH and make the robot use this also.
        # not sure on the type used for return
        # Create a line segment to represent the laser beam
        ray = self._createLaser(particle, angle)

        # initialise minimum intersection vars
        min_forward_point = min_backward_point = None
        min_forward_dist = min_backward_dist = self.LENGTH

        # check collisions of ray with each of the worlds walls
        for wall in self.segments:

            t, s = self._intersection(wall, ray)
            # is the crossover point not within the segment? (segment limits at t or s value 0 and 1)
            if 0.0 > t or t > 1.0 or 0.0 > s or s > 1.0:
                continue

            # There is an intersection, get the point by applying the offset
            point = wall.p1 + t*wall.vec

            # measure distance to the point of intersection from the robot
            dist = np.linalg.norm(point - np.array([particle.x, particle.y]))

            # if scalar is more than halfway (0.5) the obstacale is in front of robot, otherwise behind.
            # check if the newly found intersection is closer than previously measured points (for a given direction)
            if s >= 0.5 and dist < min_forward_dist:
                min_forward_point = point
                min_forward_dist = dist

            elif s < 0.5 and dist < min_backward_dist:
                min_backward_point = point
                min_backward_dist = dist


        # return the min intersections in both directions (default is at length of the ray)
        return (min_forward_point, min_backward_point), (min_forward_dist, min_backward_dist)

    def plotMap(self, fig, ax):
        lines = []
        for seg in self.segments:
            lines.append(seg._toArray())
            #fig, ax = seg.plotPerp(fig, ax)
        lc = mc.LineCollection(lines, linewidth=2)
        ax.add_collection(lc)
        ax.autoscale()
        ax.margins(0.1)
        return fig, ax

    def inObstacle(self, p):
        """Returns true if point p is inside an obstacle
        input:
        ------
            p: point in space
        output:
        -------
            True if the point is inside an obstacle, False otherwise
        """
        angle = np.random.rand()*2*np.pi
        ray = self._createSegment(p, angle)
        nb = 0
        for wall in self.segments:
            t, s = self._intersection(wall, ray)
            # is the crossover point not within the segment? (segment limits at t or s value 0 and 1)
            if 0.0 < t and t < 1.0 and 0.0 < s and s < 1.0:
                nb += 1
        if nb % 2 == 0:
            return True
        return False

    def intersect(self, segment):
        """Returns true if a segment instersects a wall
        input:
        ------
            segment: a list with two points inside
        output:
        -------
            True if the segments intersects a wall, False otherwise
        """
        seg = Segment(np.array(segment[0]), np.array(segment[1]))
        for wall in self.segments:
            t, s = self._intersection(wall, seg)
            if 0.0 < t and t < 1.0 and 0.0 < s and s < 1.0:
                return True
        return False

    def samplePoint(self):
        """ Samples a point on the map that is not inside an obstacle
        input:
        ------
            None
        output:
        -------
            None
        """
        valid = False
        sample = []
        while not valid:
            sample = []
            sample.append(np.random.rand()*self.X_LEN)
            sample.append(np.random.rand()*self.Y_LEN)
            if not self.inObstacle(sample):
                valid = True
        return sample
def cross(v, w):
    """
    Cross product for 2D vector. This function asssumes that the given vector is in 2D.
    input:
    ------
    - v: first vector.
    - w: second vector.
    output:
    -------
    - cross product (@f$(v_x * w_y - v_y * w_x)@f$)
    """
    return v[0]*w[1] - v[1]*w[0]