#from IPython import embed; embed()
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sys
import yaml
import utils
import datetime
import numpy as np
from itertools import product
from shapely.geometry import Point
from r5py import TransportNetwork, TravelTimeMatrixComputer, TransportMode
import matplotlib.pyplot as plt
from shapely.ops import nearest_points
import osmnx as ox
import pandas as pd
from network import get_matrices

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

def get_gdf():
    #Process the zone from the given input departments
    if os.path.exists(zone_path):
        print("Loading zone...")
        gdf = gpd.read_feather(zone_path)
    else:
        print("Processing zone...")
        muni = open(f"{data_path}/{municipalities_file}").read().split("\n")
        #gdf = gpd.read_file(f"{data_path}/communes.gpkg").to_crs(2154)
        gdf = gpd.read_file(f"{data_path}/communes.gpkg").to_crs(4326)
        gdf = gdf[gdf["commune_id"].isin(muni)]
        gdf.reset_index(drop=True).to_feather(zone_path)
    return gdf

def make_grid(gdf):
    """
    Compute a grid that cover uniformly the gdf shape
    """
    grid_path = f"{processed_path}/grid.feather"
    if os.path.exists(grid_path):
        print("Loading grid...")
        grid = gpd.read_feather(grid_path)
    else:
        print("Processing grid...")
        min_lon, min_lat, max_lon, max_lat = gdf.total_bounds
        size = max(max_lon-min_lon, max_lat-min_lat)/grid_size
        # compute the longitudes and latitudes top left corner coordinates
        longitudes = np.arange(min_lon+size/2, max_lon, size)
        latitudes = np.arange(min_lat+size/2, max_lat, size)
        # create the grid centroids
        points = []
        for coords in product(longitudes, latitudes):
            points.append(Point(coords[0], coords[1]))
        points = gpd.GeoDataFrame({'geometry':points})
        points.crs=4326
        # clip to geometries
        #grid = gpd.clip(gpd.GeoDataFrame({'geometry':points}, crs=2154), gdf)
        grid = gpd.clip(points, gdf)
        #grid = pd.DataFrame({"geometry":grid.geometry, "x":grid.geometry.x, "y":grid.geometry.y})
        grid = grid.reset_index(drop=True)
        grid["id"]=ox.distance.nearest_nodes(graph, grid.geometry.x,
                                               grid.geometry.y, return_dist=False)
        nodes, roads = ox.graph_to_gdfs(graph)
        grid = grid[["id"]].merge(nodes[["geometry"]],
                                                    left_on="id",
                                                    right_on="osmid",
                                                    how="left")
        grid = gpd.GeoDataFrame(grid)
        grid.reset_index(drop=True).to_feather(grid_path)
    return grid


def plot_grid(gdf, grid, graph):
    nodes, roads = ox.graph_to_gdfs(graph)
    ax = gdf.plot()
    roads.plot(ax=ax, color="white", linewidth=1, alpha=0.2, zorder=3)
    grid.plot(ax=ax, color="red", markersize=5, zorder=10)
    ax.set_axis_off()
    plt.show()

def get_grid_id(grid, x, y):
    """
    Return the nearest grid centroid from the x, y coordinates of a point
    """
    geometry = gpd.GeoSeries(gpd.points_from_xy(grid.x, grid.y))
    g = grid.copy()
    g["geometry"] = geometry
    queried, nearest = nearest_points(Point(x, y), geometry.unary_union)
    return int(grid[g.geometry == nearest].index[0])

def get_network(gdf):
    if os.path.exists(path_graphml):
        print("Loading road network")
        graph = ox.load_graphml(path_graphml, edge_dtypes={"oneway":str})
    else:
        print("Downloading road network")
        area = gdf.dissolve().to_crs(4326)
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph = ox.graph_from_polygon(area.geometry[0], network_type="all")
        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)
        #graph = ox.projection.project_graph(graph, to_crs=2154)
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
    grid_size = cfg["grid_size"]

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
    grid = make_grid(gdf)

    #plot_grid(gdf, grid, graph)

    nodes, roads = ox.graph_to_gdfs(graph)
    if not os.path.exists(path_pbf):
        utils.osm_to_pbf(path_osm, path_pbf)

    transport_network = TransportNetwork(path_pbf, [gtfs_file])

    car_tt_path = f"{processed_path}/car_tt.feather"
    if not os.path.exists(car_tt_path):
        print("Computing car travel times matrix")
        travel_time_matrix_computer = TravelTimeMatrixComputer(
            transport_network,
            origins=grid,
            transport_modes=[TransportMode.CAR])
        car_tt = travel_time_matrix_computer.compute_travel_times()
        car_tt.reset_index(drop=True).to_feather(car_tt_path)
    else:
        print("Loading car travel times matrix")
        car_tt = pd.read_feather(car_tt_path)

    pt_tt_path = f"{processed_path}/pt_tt.feather"
    if not os.path.exists(pt_tt_path):
        print("Computing public transports travel times matrix")
        travel_time_matrix_computer = TravelTimeMatrixComputer(
            transport_network,
            departure=datetime.datetime(2023,7,1,8,30),
            origins=grid,
            transport_modes=[TransportMode.TRANSIT])
        pt_tt = travel_time_matrix_computer.compute_travel_times()
        pt_tt.reset_index(drop=True).to_feather(pt_tt_path)
    else:
        print("Loading public transports travel times matrix")
        pt_tt = pd.read_feather(pt_tt_path)

    walk_tt_path = f"{processed_path}/walk_tt.feather"
    if not os.path.exists(walk_tt_path):
        print("Computing walking travel times matrix")
        travel_time_matrix_computer = TravelTimeMatrixComputer(
            transport_network,
            origins=grid,
            transport_modes=[TransportMode.WALK])
        walk_tt = travel_time_matrix_computer.compute_travel_times()
        walk_tt.reset_index(drop=True).to_feather(walk_tt_path)
    else:
        print("Loading walk travel times matrix")
        walk_tt = pd.read_feather(walk_tt_path)

    bike_tt_path = f"{processed_path}/bike_tt.feather"
    if not os.path.exists(bike_tt_path):
        print("Computing bike travel times matrix")
        travel_time_matrix_computer = TravelTimeMatrixComputer(
            transport_network,
            origins=grid,
            transport_modes=[TransportMode.BICYCLE])
        bike_tt = travel_time_matrix_computer.compute_travel_times()
        bike_tt.reset_index(drop=True).to_feather(bike_tt_path)
    else:
        print("Loading bike travel times matrix")
        bike_tt = pd.read_feather(bike_tt_path)
#car_tt2, car_distances = get_matrices(graph, grid)
from IPython import embed; embed()
