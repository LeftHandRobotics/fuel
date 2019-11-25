""" Protobuf path manipulation, especially serialization and deserialization. """

import zlib
import base64
from pymap3d import ned2geodetic, geodetic2ned
import path_pb2

import math
import csv


def serialize(proto):
    """ Serialize the data in this path object, compress it, and base64 encode it. """
    path_data = proto.SerializeToString()
    compressed = zlib.compress(path_data)
    # base64 encode as bytes, then interpret those bytes as an ascii string. Appears to work..
    return base64.b64encode(compressed).decode('ascii')


class Path:
    """ Path wrapper for interacting with structured Protobuf classes.

    Some of the getters are here purely for more readability, like obstacles and points. Careful with access
    to the underlying lists-- you won't be able to replace them as written, will need active setters.
    """

    def __init__(self, path_data=None):
        """ Pass fully serialized, compressed data to load an existing path, or nothing to create an empty one. """

        self._data = path_pb2.PathData()

        if path_data:
            decoded = base64.b64decode(path_data)
            uncompressed = zlib.decompress(decoded)
            self._data.ParseFromString(uncompressed)

    def serialize(self):
        return serialize(self._data)

    def add_point(self, lat, lng, alt, index=None):
        """ Utility method to add a point to the given (optional) index. Return the proto point. """
        point = path_pb2.Instruction()

        point.point.lat = lat
        point.point.lon = lng
        point.point.alt = alt

        if index is None:
            index = len(self.points)

        self.points.insert(index, point)
        return point

    def add_action(self, index, action):
        # TODO: check existing actions and replace those added with the same type on the given index
        self.points[index].actions.append(action)

    def remove_action(self, index, action_type):
        """ Not implemenented. No one is using it yet. """

    def add_circle_obstacle(self, lat, lng, alt, radius):
        """ Utility method to add a circular obstacle """
        obs = path_pb2.Obstacle()
        center = path_pb2.Point()
        center.lat = lat
        center.lon = lng
        center.alt = alt

        obs.points.append(center)
        obs.circle = radius
        self.obstacles.append(obs)

    def add_ring_obstacle(self):
        """ Create a new polygon obstacle, but don't add any points to it """
        obs = path_pb2.Obstacle()
        obs.ring = True
        self.obstacles.append(obs)

    def add_point_to_ring_obstacle(self, lat, lng, alt, index=None):
        """ Pass index of obstacle to add to. """
        if index is None:
            index = len(self.obstacles) - 1

        if index >= len(self.obstacles):
            raise Exception(f'Obstacle doesnt exist at index {index}')

        obs = self.obstacles[index]

        if not obs.ring:
            raise Exception("Cant add points to a non-ring obstacle")

        point = path_pb2.Point()
        point.lat = lat
        point.lon = lng
        point.alt = alt

        obs.points.append(point)
        return point

    def to_ned(self, lat, lon, height):
        """ Convert all the points to NED relative to passed llh """
        ned = []
        act = []

        for ins in self.points:

            if ins.point:
                n, e, d = geodetic2ned(lat=ins.point.lat, lon=ins.point.lon, h=ins.point.alt, lat0=lat, lon0=lon, h0=height)
                ned.append([n * 100, e * 100, d * 100])  # Multiplication is for meters -> CM

            if ins.actions:
                act.append(ins.actions)
            else:
                act.append("")

        return ned, act

    def __repr__(self):
        return f'Config: {self.config}, points: {len(self.points)}, obstacles: {len(self.obstacles)}'

    ####################################################################################
    # Beauty Properties
    ####################################################################################

    @property
    def points(self):
        """ Points are accessed as:

        point.point.lat, point.point.lon, point.point.alt
        """
        return self._data.instructions

    @property
    def obstacles(self):
        return self._data.obstacles


def to_llh(lat, lon, height, ned):
    """ Convert all the ned_points to an llh list of points. """
    n, e, d = ned[0] / 100, ned[1] / 100, ned[2] / 100  # Division is for CM -> meters
    return ned2geodetic(n=n, e=e, d=d, lat0=lat, lon0=lon, h0=height)


def to_program(ned, act, file):
    arcs, xFunction, yFunction, actions, x_coords, y_coords = [], [], [], [], [], []
    arc = 0

    for i in range(len(ned) - 1):
        x_coords.append(ned[i][1])
        y_coords.append(ned[i][0])
        arc += math.sqrt((x_coords[i] - ned[i + 1][1]) ** 2 + (y_coords[i] - ned[i + 1][0]) ** 2)
        arcs.append(arc)
        actions.append(act[i])

    for j in range(len(x_coords) - 1):
        x_delta = x_coords[j + 1] - ned[j][1]
        y_delta = y_coords[j + 1] - ned[j][0]

        xFunction.append([0, 0, 0, 0, x_delta, x_coords[j]])
        yFunction.append([0, 0, 0, 0, y_delta, y_coords[j]])

        last_x = x_delta + x_coords[j]
        last_y = y_delta + y_coords[j]

    xFunction.append([0, 0, 0, 0, ned[-1][1] - last_x, last_x])
    yFunction.append([0, 0, 0, 0, ned[-1][0] - last_y, last_y])

    xHeading = "0,0,0,0,0"
    yHeading = "0,0,0,0,0"
    gradient = 0  # For now we don't know what gradient is

    to_file(arcs, xFunction, yFunction, xHeading, yHeading, actions, gradient, file)
    # angles = path_angles(xFunction, yFunction)
    # return arcs[-1], angles


def path_angles(xFunction, yFunction):
    angles = []

    for i in range(len(xFunction) - 2):
        a = [xFunction[i][5], yFunction[i][5]]
        b = [xFunction[i + 1][5], yFunction[i + 1][5]]
        c = [xFunction[i + 2][5], yFunction[i + 2][5]]
        angle = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])
        angles.append(angle)

    return sum(angles) / len(angles)


def to_file(p0, p1, p2, p3, p4, p5, p6, file):
    c_writer = csv.writer(open(file, 'w'), delimiter='|', quotechar=" ")

    header = [
        'Metadata',
        'base_station_serial_number=0',
        'init_heading=0',
        'job_site_id=514',
        'path_name=Translated Path',
        'vel_step=0.1',
        '',
        'Positions'
    ]

    for row in header:
        c_writer.writerow([row])

    p5_string = ""

    for i in range(len(p5)):
        if len(p5[i]) > 0:
            p5_string = ""

            for j in range(len(p5[i])):

                if p5[i][j].front_state or int(p5[i][j].front_state) == 0:
                    p5_string += "FRONT_STATE=" + str(p5[i][j].front_state) + ","
                if p5[i][j].front_pivot or int(p5[i][j].front_pivot) == 0:
                    p5_string += "BROOM_DIRECTION=" + str(p5[i][j].front_pivot) + ","
                if p5[i][j].front_vertical or int(p5[i][j].front_vertical) == 0:
                    p5_string += "FRONT_VERTICAL=" + str(p5[i][j].front_vertical) + ","
                if p5[i][j].narrow_view or int(p5[i][j].narrow_view) == 0:
                    p5_string += "NARROW_OBSTACLE_VIEW=" + str(p5[i][j].narrow_view) + ","
                if p5[i][j].wide_bounds:
                    p5_string += "WIDE_PATH_BOUNDS=0,"
                if p5[i][j].wide_bounds is False:
                    p5_string += "WIDE_PATH_BOUNDS=1,"
                # if p5[i][j].path_width or int(p5[i][j].path_width) == 0:
                #     p5_string += "DRIVE_STRAIGHT=" + str(p5[i][j].path_width) + ","
                if p5[i][j].rear_attachment or int(p5[i][j].rear_attachment) == 0:
                    p5_string += "REAR_ATTACHMENT=" + str(p5[i][j].rear_attachment)
                if p5[i][j].log or p5[i][j].log == 'FRONT':
                    p5_string += "LOG=" + str(p5[i][j].log) + ","
                if p5[i][j].pause:
                    p5_string += "PAUSE=0"
                if p5[i][j].pause is False:
                    p5_string += "PAUSE=1"
                break

        c_writer.writerow([p0[i], str(p1[i][0]) + "," + str(p1[i][1]) + "," + str(p1[i][2]) + "," + str(p1[i][3]) +
                           "," + str(p1[i][4]) + "," + str(p1[i][5]), str(p2[i][0]) + "," + str(p2[i][1]) + "," + str(p2[i][2]) +
                           "," + str(p2[i][3]) + "," + str(p2[i][4]) + "," + str(p2[i][5]), p3, p4, p5_string, p6])

    footer = ["Velocities", "0.0|0.0"]
    for item in footer:
        c_writer.writerow([item])


def angle(p1, p2):
    return math.atan2((p2[0] - p1[0]), (p2[1] - p1[1]))
