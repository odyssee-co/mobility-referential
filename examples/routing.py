import os
os.environ['USE_PYGEOS'] = '0'
import sys
import yaml
from mobref import area, network, vrp

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python3 {sys.argv[0]} configuration_file")
        exit(1)
    yml_path = sys.argv[1]
    with open(yml_path, "r") as yml_file:
        cfg = yaml.safe_load(yml_file)
    municipalities_path = cfg["municipalities_path"]
    administrative_cutting_path = cfg["administrative_cutting_path"]

    #Create the processed data directory if needed
    processed_path = cfg["processed_path"]
    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    area = area.Area(processed_path, municipalities_path, administrative_cutting_path)
    network_d = network.Network(area, "drive", processed_path)

    print("Showcasing vrp problem with random jobs and vehicles.\n")
    jobs = area.random_points(15)
    print("Jobs: ", jobs)
    vehicles = area.random_points(4)
    print("Vehicles: ", vehicles)
    solution = vrp.solve_vrp(network_d, vehicles, jobs)
    print(f"Total time: {solution.summary.cost}")
    print(solution.routes[["vehicle_id", "type", "arrival", "location_index", "id"]])
