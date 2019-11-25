import proto_path
import math
import os
import json
import csv
import sys
import statistics

csv.field_size_limit(sys.maxsize)

MOWING = False
GALLONS_PER_TANK = 12


def create_master_file():

    with open('dump_matching.json', 'r') as f:
        raw = json.load(f)

        for dict_ in raw:
            path_names, total_times, distances, total_distances, reports = [], [], [], [], []
            path_id = dict_["pathId"]

            for key, value in dict_.items():
                if key == 'rawReportEntries':
                    raw_report = value

                    for entry in raw_report:
                        try:
                            entry = eval(entry)[0]
                            for k, v in entry.items():
                                if k == 'timestamp':
                                    time = v
                                if k == 'state':
                                    state = v
                                if k == 'current_point':
                                    current_point = v
                                if k == 'progress':
                                    progress = v

                            reports.append([time, state, current_point, progress])

                        except Exception as e:
                            pass

            # Calculate time
            if reports and (reports[-1][3] - reports[0][3] != 0):  # If progression has been made

                # Capture only the time the bot was running
                total_time = 0
                for i, report in enumerate(reports):
                    if report[1] == 'RUNNING':
                        if i != 0 and reports[i - 1][1] != 'RUNNING':
                            total_time -= (report[0] - reports[i - 1][0])
                        else:
                            total_time += (report[0] - reports[0][0])
                    else:
                        if reports[i - 1][1] != 'RUNNING':
                            total_time -= (report[0] - reports[i - 1][0])

                if total_time > 0:
                    distance, total_distance = [], []
                    row = [path_id, total_time, reports[-1][2] - reports[0][2]]

                    # If path name, convert to ned_points to get distances
                    for path_name in os.listdir('paths/'):

                        if int(row[0]) == int(path_name):
                            f2 = open("paths/" + str(path_name), 'r')
                            path = proto_path.Path(f2.read())

                            first = path.points[0].point
                            ned_points, _ = path.to_ned(first.lat, first.lon, first.alt)

                            total_times.append(float(row[1]))
                            path_names.append(int(path_name))

                            # Row[2] is points traversed
                            if len(ned_points) >= int(row[2]):
                                for i in range(int(row[2]) - 1):
                                    distance.append(distance_between_two_points(ned_points[i], ned_points[i + 1]))
                                for k in range(len(ned_points) - 1):
                                    total_distance.append(distance_between_two_points(ned_points[k], ned_points[k + 1]))

                    distances.append(sum(distance))
                    total_distances.append(sum(total_distance))

            with open('master.csv', 'a') as file:
                writer = csv.writer(file)
                for i in range(len(path_names)):
                    writer.writerow([path_names[i], total_times[i], distances[i], total_distances[i]])
                    #path_name = path_names[i]


def add_average_time(path):

    with open('master.csv', 'r') as file:
        # next(file)
        reader = csv.reader(file)

        time_per_cm = []
        for row in reader:
            path_name = int(row[0])
            total_time = float(row[1])
            distance_traveled = float(row[2])
            total_distance = float(row[3])

            if path_name == int(path):
                if total_distance != 0 and distance_traveled != 0:
                    time_per_cm.append(total_time / distance_traveled)

        if len(time_per_cm) == 0:
            time_per_cm.append(0)

    # print(len(time_per_cm))
    median = statistics.median(sorted(time_per_cm))

    new_time_per_cm = []
    for i, instance in enumerate(time_per_cm):

        if time_per_cm[i] <= (median * 5) and time_per_cm[i] >= 0.0009:
            new_time_per_cm.append(time_per_cm[i])

    if len(new_time_per_cm) == 0:
        median_time_per_cm = 0
    else:
        median_time_per_cm = statistics.median(new_time_per_cm)

    with open('paths_info.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow([path, median_time_per_cm])


def distance_between_two_points(p1, p2):
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def get_average_time(path_name):

    with open("paths_info.csv", 'r') as file:
        average_time = 0
        times = []

        reader = csv.reader(file)
        for row in reader:
            times.append(float(row[1]))
            if row[0] == path_name:
                average_time = float(row[1])

    median = statistics.median(sorted(times))

    # if average_time <= 0.001 or average_time > (median * 5):  # CAN PLAY WITH THIS NUMBER LATER
    #     average_time = median  # Fill this number with average of all paths

    # For first instance
    if average_time == 0:
        average_time = median  # 0.002
    print(median)
    return average_time


def average_group_time():
    # Get the average time for the entire data set
    with open("paths_info.csv", 'r') as file:
        times = []

        reader = csv.reader(file)
        for row in reader:
            times.append(float(row[1]))

    return statistics.median(sorted(times))


def estimate_fuel(raw_path, path_name, index):
    distance, total_distance, average_time = 0, 0, 0

    # Convert the path to ned points, for distance traveled and total distance of path
    path = proto_path.Path(raw_path.read())
    first = path.points[0].point
    ned_points, _ = path.to_ned(first.lat, first.lon, first.alt)

    if len(ned_points) >= index:
        for i in range(int(index) - 1):
            distance += distance_between_two_points(ned_points[i], ned_points[i + 1])
        for j in range(len(ned_points) - 1):
            total_distance += distance_between_two_points(ned_points[j], ned_points[j + 1])

    average_time = get_average_time(path_name)

    # Get the time remaining to calculate the gallons needed and in turn the amount of fuel needed.
    time_remaining = (total_distance - distance) * average_time  # distance_remaining * average time per cm
    gallons_per_hour = 1.33 if MOWING else 1.5  # educated guess on average gallons per hour

    gallons_needed = gallons_per_hour * (time_remaining / 3600)
    fuel_needed = gallons_needed / GALLONS_PER_TANK

    print("PATH NAME: ", path_name, "FUEL NEEDED: ", fuel_needed, "MINUTES REMAINING: ", time_remaining / 60)
    return fuel_needed


if __name__ == "__main__":
    # create_master_file()

    for path in os.listdir('paths/'):
        add_average_time(path)

    median = average_group_time()

    for path in os.listdir('paths/'):
        raw_path = open("paths/" + str(path), 'r')
        fuel_needed = estimate_fuel(raw_path, path, index=20)

