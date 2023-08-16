#from IPython import embed; embed()
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sys
import yaml
import datetime
import numpy as np
from itertools import product
from shapely.geometry import Point
import matplotlib.pyplot as plt
from shapely.ops import nearest_points
import osmnx as ox
import pandas as pd
from network import get_matrices
import pandana as pdna
import urbanaccess as ua


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
    area = gdf.dissolve().to_crs(4326)
    if os.path.exists(path_graph_drive):
        print("Loading road network")
        graph_drive = ox.load_graphml(path_graph_drive)
    else:
        print("Downloading road network")
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph_drive = ox.graph_from_polygon(area.geometry[0], network_type="drive")
        graph_drive = ox.add_edge_speeds(graph_drive)
        graph_drive = ox.add_edge_travel_times(graph_drive)
        ox.save_graphml(graph_drive, filepath=path_graph_drive)

    if os.path.exists(path_graph_walk):
        print("Loading walk network")
        graph_walk = ox.load_graphml(path_graph_walk)
    else:
        print("Downloading walk network")
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph_walk = ox.graph_from_polygon(area.geometry[0], network_type="walk")
        #graph = ox.projection.project_graph(graph, to_crs=2154)
        ox.save_graphml(graph_walk, filepath=path_graph_walk)

    if os.path.exists(path_graph_bike):
        print("Loading bike network")
        graph_bike = ox.load_graphml(path_graph_bike)
    else:
        print("Downloading bike network")
        #cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph_bike = ox.graph_from_polygon(area.geometry[0], network_type="bike")
        #graph = ox.projection.project_graph(graph, to_crs=2154)
        ox.save_graphml(graph_bike, filepath=path_graph_bike)

    return graph_drive, graph_walk, graph_bike


def get_integrated_graph(gdf, graph_w):
    bbox = tuple(gdf.dissolve().to_crs(4326).bounds.iloc[0])
    G_proj = ox.project_graph(graph_w)
    graph_w = ox.consolidate_intersections(G_proj, rebuild_graph=True, tolerance=40, dead_ends=False)
    graph_w = ox.project_graph(graph_w, 4326)
    nodes, edges = ox.graph_to_gdfs(graph_w)
    print("Nombre de noeuds: ", len(nodes))
    loaded_feeds = ua.gtfs.load.gtfsfeed_to_df(gtfs_path, validation=True,
                                                        verbose=True, bbox=bbox,
                                                        remove_stops_outsidebbox=True,
                                                        append_definitions=True)
    ua.gtfs.network.create_transit_net(gtfsfeeds_dfs=loaded_feeds,
                                       day='monday',
                                       timerange=['07:00:00', '10:00:00'],
                                       calendar_dates_lookup=None)
    ua.gtfs.headways.headways(gtfsfeeds_df=loaded_feeds,headway_timerange=['07:00:00','10:00:00'])

    edges["distance"] = edges.to_crs(2154).length
    ua.osm.network.create_osm_net(osm_edges=edges, osm_nodes=nodes, travel_speed_mph=3)

    urbanaccess_net = ua.network.ua_network

    from IPython import embed; embed()
    #TODO: does not work because of memory issues


    ua.network.integrate_network(urbanaccess_network=urbanaccess_net,
                             headways=True,
                             urbanaccess_gtfsfeeds_df=loaded_feeds,
                             headway_statistic='mean')
    return urbanaccess_net

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

    path_graph_drive = f"{processed_path}/graph_drive.graphml"
    path_graph_walk = f"{processed_path}/graph_walk.graphml"
    path_graph_bike= f"{processed_path}/graph_bike.graphml"
    path_osm = f"{processed_path}/graph.osm"
    path_pbf = f"{processed_path}/graph.osm.pbf"
    zone_path = f"{processed_path}/zone.feather"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    gdf = get_gdf()
    graph_d, graph_w, graph_b = get_network(gdf)
    grid = make_grid(gdf)

    i_graph = get_integrated_graph(gdf, graph_w)

    #plot_grid(gdf, grid, graph)

    #car_tt2, car_distances = get_matrices(graph, grid)
