#from IPython import embed; embed()
import geopandas as gpd
from r5py import TransportNetwork
import osmnx as ox
import os, sys
import yaml
import utils

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
        graph = ox.load_graphml(path_graphml)
    else:
        print("Downloading road network")
        area = gdf.dissolve().to_crs(4326)
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph = ox.graph_from_polygon(area.geometry[0], network_type="all",
                                      retain_all=True, truncate_by_edge=True,
                                      clean_periphery=True)
        graph = ox.projection.project_graph(graph, to_crs=2154)
        ox.save_graphml(graph, filepath=path_graphml)
    if not os.path.exists(path_xml):
        ox.save_graph_xml(graph, "graph.xml")
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

    #Create the processed data directory
    processed_path = f"{data_path}/processed/{municipalities_file.split('.')[0]}"

    path_graphml = f"{processed_path}/graph.graphml"
    path_xml = f"{processed_path}/graph.xml"
    path_pbf = f"{processed_path}/graph.osm.pbf"
    zone_path = f"{processed_path}/zone.feather"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    gdf = get_gdf()
    graph = get_network(gdf)

    nodes, roads = ox.graph_to_gdfs(graph)
    if not os.path.exists(path_pbf):
        utils.xml_to_pbf(path_xml, path_pbf)

    """
    transport_network = TransportNetwork(
            "data/Helsinki/Helsinki_region_OSM_2023_01.osm.pbf",
            ["data/Helsinki/helsinki_gtfs_2023-01_2023-02.zip"],
            )
    """
