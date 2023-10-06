#from IPython import embed; embed()
from IPython import embed
import os
os.environ['USE_PYGEOS'] = '0'
import sys
import yaml
import area
import network

"""
#parameters to set all_oneway to true but it's buggy
utn = ox.settings.useful_tags_node
oxna = ox.settings.osm_xml_node_attrs
oxnt = ox.settings.osm_xml_node_tags
utw = ox.settings.useful_tags_way
oxwa = ox.settings.osm_xml_way_attrs
oxwt = ox.settings.osm_xml_way_tags
utn = list(set(utn + oxna + oxnt))
utw = list(set(utw + oxwa + oxwt))
ox.settings.all_oneway = True
ox.settings.useful_tags_node = utn
ox.settings.useful_tags_way = utw
"""


def get_matrices(network, POIs):
    #
    return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python3 {sys.argv[0]} configuration_file")
        exit(1)
    yml_path = sys.argv[1]
    with open(yml_path, "r") as yml_file:
        cfg = yaml.safe_load(yml_file)
    data_path = cfg["data_path"]
    municipalities_file = cfg["municipalities_file"]
    gtfs_path = cfg["gtfs_path"]

    #Create the processed data directory
    processed_path = f"{data_path}/processed/{municipalities_file.split('.')[0]}"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    area = area.Area(data_path, processed_path, municipalities_file)

    network_d = network.Network(area, "drive", processed_path)

    """
    network_w = network.Network(area, "walk", processed_path, gtfs_path)
    network_t = network.Network(area, "transit", processed_path, gtfs_path)
    network_b = network.Network(area, "bike", processed_path, gtfs_path)

    r1 = area.random_point()
    r2 = area.random_point()
    print("drive: ", network_d.shortest_path(r1, r2))
    print("transit: ", network_t.shortest_path(r1, r2))
    print("bike: ", network_b.shortest_path(r1, r2))
    print("walk: ", network_w.shortest_path(r1, r2))
    """

    #find time and distance matrices between all restaurants to all restaurant by car
    restaurants = area.find_pois('"amenity"="restaurant"')
    matrices = network_d.get_matrices(restaurants, distance=True)
    print(matrices["time"], matrices["distance"])

    #find the 3 closest restaurants at a maximum of 10 minutes to each node
    closest = network_d.find_closest(restaurants, maxtime=600, maxitems=3)
    print(closest.head())

    #plot a map showing how many restaurants are within 5min of each node
    network_d.plot_accessibility(restaurants, time=300)
