import os
os.environ['USE_PYGEOS'] = '0'
import sys
import yaml
from mobref import area, network

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python3 {sys.argv[0]} configuration_file")
        exit(1)
    yml_path = sys.argv[1]
    with open(yml_path, "r") as yml_file:
        cfg = yaml.safe_load(yml_file)
    data_path = cfg["data_path"]
    municipalities_file = cfg["municipalities_file"]

    #Create the processed data directory
    processed_path = f"{data_path}/processed/{municipalities_file.split('.')[0]}"
    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    area = area.Area(data_path, processed_path, municipalities_file)
    network_d = network.Network(area, "drive", processed_path)

    print("Find time and distance matrices between all restaurants to all restaurants by car.")
    restaurants = area.find_pois('"amenity"="restaurant"')
    matrices = network_d.get_matrices(restaurants)
    print(matrices["time"], matrices["distance"])
    print()

    print("Find the 3 closest restaurants at a maximum of 10 minutes to each node.")
    closest = network_d.find_closest(restaurants, maxtime=600, maxitems=3)
    print(closest)
    print()

    print("Plot accessibility...\n")
    network_d.plot_accessibility(restaurants, time=300)
