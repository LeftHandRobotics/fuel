# Fuel


The paths folder contains all the protopaths for each path.
Dump_matching.json contains the stats from the runs of each path.


## main.py 
	- Creates a master file which contains the path_name, total time, distance traveled, and the total distance of the path.
	- After master file is created, you only need the path name and the index to find the fuel estimate.
		- It calculates fuel by using the average distance covered in a given time frame.


## Assumptions
	A couple of assumptions include:
		- Mowing averages 1.5 MPG
		- Snow averages 1.33 MPG
			(according to Robotics)
		- Percentage of fuel is based off a 13 gallons tank.
		- Fuel consumption is based on time since engine is ALWAYS fully reved. 


