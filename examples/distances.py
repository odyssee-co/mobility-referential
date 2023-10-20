import os
os.environ['USE_PYGEOS'] = '0'
import sys
import yaml
from mobref import network, area

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

    gtfs_path = cfg["gtfs_path"]
    network_d = network.Network(area, "drive", processed_path)
    network_w = network.Network(area, "walk", processed_path, gtfs_path)
    network_t = network.Network(area, "transit", processed_path, gtfs_path)
    network_b = network.Network(area, "bike", processed_path, gtfs_path)

    print("Print shortest path between two random points for available modes.")
    r1 = area.random_point()
    r2 = area.random_point()

    d_sp = network_d.shortest_path(r1, r2)
    t_sp = network_t.shortest_path(r1, r2)
    b_sp = network_b.shortest_path(r1, r2)
    w_sp = network_w.shortest_path(r1, r2)

    print(f"drive distance: {d_sp['distance']}")
    print(f"drive time: {d_sp['travel_time']}")
    print(f"drive path: {d_sp['shortest_path']}")
    print()
    print(f"transit distance: {t_sp['distance']}")
    print(f"transit time: {t_sp['travel_time']}")
    print(f"transit path: {t_sp['shortest_path']}")
    print()
    print(f"bike distance: {b_sp['distance']}")
    print(f"bike time: {b_sp['travel_time']}")
    print(f"bike path: {b_sp['shortest_path']}")
    print()
    print(f"walk distance: {w_sp['distance']}")
    print(f"walk time: {w_sp['travel_time']}")
    print(f"walk path: {w_sp['shortest_path']}")
    print()

    print("Plot transit network...\n")
    network_t.plot_net_by_travel_time()
