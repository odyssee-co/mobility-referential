#from IPython import embed; embed()
from IPython import embed
import os
os.environ['USE_PYGEOS'] = '0'
import sys
import yaml
import matplotlib
from matplotlib import pyplot as plt
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
    grid_size = cfg["grid_size"]

    #Create the processed data directory
    processed_path = f"{data_path}/processed/{municipalities_file.split('.')[0]}"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    area = area.Area(data_path, processed_path, municipalities_file)

    r1 = area.random_point()
    r2 = area.random_point()

    network_d = network.Network(area, "drive", processed_path)
    network_w = network.Network(area, "walk", processed_path, gtfs_path)
    network_t = network.Network(area, "transit", processed_path, gtfs_path)
    network_b = network.Network(area, "bike", processed_path, gtfs_path)

    print("drive: ", network_d.shortest_path(r1, r2))
    print("transit: ", network_t.shortest_path(r1, r2))
    print("bike: ", network_b.shortest_path(r1, r2))
    print("walk: ", network_w.shortest_path(r1, r2))

    #find distance matrix between all restaurants to all restaurant by car
    restaurants = area.find_POIs('"amenity"="restaurant"')
    matrices = network_d.get_matrices(restaurants, distance=True)
    print(matrices["time"], matrices["distance"])

    """
    #find the closest restaurants to each node
    network.set_pois(category = 'restaurants',
                     maxdist = 1000,
                     maxitems = 3,
                     x_col = restaurants.lon,
                     y_col = restaurants.lat)
    results = network.nearest_pois(distance = 1000,
                                   category = 'restaurants',
                                   num_pois = 3,
                                   include_poi_ids = True)
    print(results.head())

    #how many restaurants are within 20min meters of each node?
    network.set(restaurant_nodes, name = 'restaurants')
    accessibility = network.aggregate(distance = 20, type = 'count', name = 'restaurants')
    accessibility.describe()
    fig, ax = plt.subplots(figsize=(10,8))
    plt.title('Restaurants within 20min transportation')
    plt.scatter(network.nodes_df.x, network.nodes_df.y,
                c=accessibility, s=1, cmap='YlOrRd',
                norm=matplotlib.colors.LogNorm())
    cb = plt.colorbar()
    plt.show()
    """
