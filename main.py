#from IPython import embed; embed()
import geopandas as gpd
from r5py import TransportNetwork
import osmnx as ox
import os, sys
import yaml

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

    #Process the zone from the given input departments
    zone_path = f"{processed_path}/zone.feather"
    if os.path.exists(zone_path):
        print("Loading zone...")
        gdf = gpd.read_feather(zone_path)
    else:
        print("Processing zone...")
        muni = open(f"{data_path}/{municipalities_file}").read().split("\n")
        gdf = gpd.read_file(f"{data_path}/communes.gpkg").to_crs(2154)
        gdf = gdf[gdf["commune_id"].isin(muni)]
        gdf.reset_index(drop=True).to_feather(zone_path)

    path = f"{processed_path}/graph.graphml"
    if os.path.exists(path):
        print("Loading road network")
        graph = ox.load_graphml(path)
    else:
        print("Downloading road network")
        area = gdf.dissolve().to_crs(4326)
        cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph = ox.graph_from_polygon(area.geometry[0], network_type="drive", retain_all=True, truncate_by_edge=True, clean_periphery=True, custom_filter=cf)
        graph = ox.projection.project_graph(graph, to_crs=2154)
        ox.save_graphml(graph, filepath=path)
    nodes, roads = ox.graph_to_gdfs(graph)


    """
    transport_network = TransportNetwork(
            "data/Helsinki/Helsinki_region_OSM_2023_01.osm.pbf",
            ["data/Helsinki/helsinki_gtfs_2023-01_2023-02.zip"],
            )
    """
