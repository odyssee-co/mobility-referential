#from IPython import embed; embed()
import geopandas as gpd
import os, sys
import yaml
import utils
import datetime
from r5py import TransportNetwork, TravelTimeMatrixComputer, TransitMode, LegMode

import osmnx as ox
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

def get_gdf():
    #Process the zone from the given input departments
    if os.path.exists(zone_path):
        print("Loading zone...")
        gdf = gpd.read_feather(zone_path)
    else:
        print("Processing zone...")
        muni = open(f"{data_path}/{municipalities_file}").read().split("\n")
        gdf = gpd.read_file(f"{data_path}/communes.gpkg").to_crs(2154)
        gdf = gdf[gdf["commune_id"].isin(muni)]
        gdf.reset_index(drop=True).to_feather(zone_path)
    return gdf


def get_network(gdf):
    if os.path.exists(path_graphml):
        print("Loading road network")
        graph = ox.load_graphml(path_graphml, edge_dtypes={"oneway":str})
    else:
        print("Downloading road network")
        area = gdf.dissolve().to_crs(4326)
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph = ox.graph_from_polygon(area.geometry[0], network_type="all",
                                      retain_all=True, truncate_by_edge=True,
                                      clean_periphery=True)
        graph = ox.projection.project_graph(graph, to_crs=2154)
        ox.save_graphml(graph, filepath=path_graphml)
    if not os.path.exists(path_osm):
        ox.save_graph_xml(graph, filepath=path_osm)
    return graph


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python3 {sys.argv[0]} configuration_file")
        exit(1)
    yml_path = sys.argv[1]
    with open(yml_path, "r") as yml_file:
        cfg = yaml.safe_load(yml_file)
    data_path = cfg["data_path"]
    municipalities_file = cfg["municipalities_file"]
    gtfs_file = cfg["gtfs_file"]

    #Create the processed data directory
    processed_path = f"{data_path}/processed/{municipalities_file.split('.')[0]}"

    path_graphml = f"{processed_path}/graph.graphml"
    path_osm = f"{processed_path}/graph.osm"
    path_pbf = f"{processed_path}/graph.osm.pbf"
    zone_path = f"{processed_path}/zone.feather"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    gdf = get_gdf()
    graph = get_network(gdf)

    nodes, roads = ox.graph_to_gdfs(graph)
    if not os.path.exists(path_pbf):
        utils.osm_to_pbf(path_osm, path_pbf)

    from IPython import embed; embed()
    """
    transport_network = TransportNetwork(path_pbf, [gtfs_file])
    travel_time_matrix_computer = TravelTimeMatrixComputer(
        transport_network,
        origins=station,
        destinations=pop_points,
        departure=datetime.datetime(2023,1,19,7,30),
        transport_modes=[TransitMode.TRANSIT, LegMode.WALK])
    travel_time_matrix = travel_time_matrix_computer.compute_travel_times()
    """
