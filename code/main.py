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
import matplotlib
from matplotlib import pyplot as plt
from shapely.ops import nearest_points
import osmnx as ox
import pandas as pd
from network import get_matrices, create_graph, get_route_details
import pandana as pdna
import urbanaccess as ua
from utils import save_network, load_network
from pandana.loaders import osm
import random

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

def random_point_in_polygon(polygon):
    """
    This function generates a random point within a given polygon. It ensures that the generated point is located
    inside the specified polygon by repeatedly generating points within the bounding box of the polygon until
    a point inside the polygon is found.

    Parameters:
        polygon (shapely.geometry.Polygon): The polygon within which to generate the random point.

    Returns:
        tuple: A tuple containing the x and y coordinates of the generated random point.
    """
    # Generate a random point within the bounding box of the polygon
    min_x, min_y, max_x, max_y = polygon.bounds
    random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
    # Check if the random point is within the polygon
    while not polygon.contains(random_point):
        random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
    return random_point.x, random_point.y

def get_gdf():
    """
    Load or process a GeoDataFrame (gdf) representing a specific geographic zone
    by filtering it based on a list of municipality IDs read from a file.
    The resulting GeoDataFrame is then saved as a Feather file for future use and returned.

    Returns:
    - gdf (geopandas.GeoDataFrame): A GeoDataFrame representing the geographic zone.
    """

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
    Compute a grid that uniformly covers the shape of the input GeoDataFrame (gdf).

    Parameters:
    - gdf (geopandas.GeoDataFrame): The input GeoDataFrame representing a geographic area.

    Returns:
    - grid (geopandas.GeoDataFrame): A GeoDataFrame representing the computed grid.
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
        """
        #Interpolate the grid to the existing nodes
        grid["id"]=ox.distance.nearest_nodes(graph, grid.geometry.x,
                                               grid.geometry.y, return_dist=False)
        nodes, roads = ox.graph_to_gdfs(graph)
        grid = grid[["id"]].merge(nodes[["geometry"]],
                                                    left_on="id",
                                                    right_on="osmid",
                                                    how="left")
        """
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
    Return the nearest grid centroid ID from the given x and y coordinates of a point.

    Parameters:
    - grid (geopandas.GeoDataFrame): The GeoDataFrame representing the grid centroids.
    - x (float): The x-coordinate (longitude) of the point.
    - y (float): The y-coordinate (latitude) of the point.

    Returns:
    - int: The ID of the nearest grid centroid to the provided coordinates (x, y).
    """

    geometry = gpd.GeoSeries(gpd.points_from_xy(grid.x, grid.y))
    g = grid.copy()
    g["geometry"] = geometry
    queried, nearest = nearest_points(Point(x, y), geometry.unary_union)
    return int(grid[g.geometry == nearest].index[0])

def get_network(gdf):
    """
    Retrieve or download road, walk, and bike network graphs for a specific
    geographic area.

    Parameters:
    - gdf (geopandas.GeoDataFrame): The GeoDataFrame representing the
      geographic area of interest.

    Returns:
    - graph_drive (ox.Graph): The road network graph for driving.
    - graph_walk (ox.Graph): The network graph for walking.
    - graph_bike (ox.Graph): The network graph for biking.
    """

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
    """
    Retrieve or build an integrated multi-modal transportation network graph
    for a specified geographic area.

    Parameters:
    - gdf (geopandas.GeoDataFrame): The GeoDataFrame representing the geographic
      area of interest.
    - graph_w (ox.Graph): The walking network graph for the same area.

    Returns:
    - urbanaccess_net (ua.network.ua_network): The integrated multi-modal
      transportation network.
    """
    if os.path.exists(integrated_edges_path) and os.path.exists(integrated_nodes_path):
        print("Loading integrated network")
        urbanaccess_net = load_network(dir=processed_path)
    else:
        print("Building integrated network")
        bbox = tuple(gdf.dissolve().to_crs(4326).bounds.iloc[0])
        """
        #Simplify walking graph
        G_proj = ox.project_graph(graph_w)
        graph_w = ox.consolidate_intersections(G_proj,
                                               rebuild_graph=True,
                                               tolerance=15,
                                               dead_ends=False)
        graph_w = ox.project_graph(graph_w, 4326)
        """

        nodes, edges = ox.graph_to_gdfs(graph_w)
        nodes["id"]=nodes.index
        edges["distance"] = edges.to_crs(2154).length
        edges["from"]=edges.index.get_level_values(0)
        edges["to"]=edges.index.get_level_values(1)
        ua.osm.network.create_osm_net(osm_edges=edges,
                                      osm_nodes=nodes,
                                      travel_speed_mph=3)

        loaded_feeds = ua.gtfs.load.gtfsfeed_to_df(gtfs_path,
                                                   validation=True,
                                                   verbose=True,
                                                   bbox=bbox,
                                                   remove_stops_outsidebbox=True,
                                                   append_definitions=True)
        #Simplify transit feeds
        area = gdf.dissolve().to_crs(4326)
        stops_inside_box = []
        loaded_feeds.stops["geometry"] = gpd.points_from_xy(loaded_feeds.stops.stop_lon, loaded_feeds.stops.stop_lat)
        print("Removing stops that are outside area")
        for id, s in loaded_feeds.stops.iterrows():
            if area.contains(s.geometry)[0]:
                stops_inside_box.append(s.stop_id)
        loaded_feeds.stops = loaded_feeds.stops[loaded_feeds.stops['stop_id'].
                                                        isin(stops_inside_box)]
        loaded_feeds.stop_times = loaded_feeds.stop_times[loaded_feeds.
                                    stop_times['stop_id'].isin(stops_inside_box)]

        ua.gtfs.network.create_transit_net(gtfsfeeds_dfs=loaded_feeds,
                                           day='monday',
                                           timerange=['07:00:00', '10:00:00'],
                                           calendar_dates_lookup=None)
        ua.gtfs.headways.headways(gtfsfeeds_df=loaded_feeds,
                                  headway_timerange=['07:00:00','10:00:00'])
        urbanaccess_net = ua.network.ua_network

        ua.integrate_network(urbanaccess_network=urbanaccess_net,
                                 headways=True,
                                 urbanaccess_gtfsfeeds_df=loaded_feeds,
                                 headway_statistic='mean')
        save_network(urbanaccess_network=urbanaccess_net, dir=processed_path)
        #TODO: check miles km compatibility
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
    integrated_edges_path= f"{processed_path}/net_edges.feather"
    integrated_nodes_path= f"{processed_path}/net_nodes.feather"

    if not os.path.isdir(processed_path):
        os.mkdir(processed_path)

    gdf = get_gdf()
    graph_d, graph_w, graph_b = get_network(gdf)
    grid = make_grid(gdf)

    # Create the transit/walk multimodal network
    urbanaccess_net = get_integrated_graph(gdf, graph_w)

    # Remove edges with uknown nodes
    nodes = urbanaccess_net.net_nodes
    edges = urbanaccess_net.net_edges
    edges = edges[edges['to_int'].isin(nodes.index) & edges['from_int'].isin(nodes.index)]

    # Create a hierarchical graph to greatly improve the shortest paths computations
    # see: "A Generalized Computational Framework for Accessibility: From
    # the Pedestrian to the Metropolitan Scale" for more details
    transit_ped_net = pdna.Network(nodes["x"],
                                   nodes["y"],
                                   edges["from_int"],
                                   edges["to_int"],
                                   edges[["weight"]],
                                   twoway=False)
    transit_ped_net.precompute(3000)
    network = transit_ped_net

    #find distance between two random points
    bbox = tuple(gdf.dissolve().to_crs(4326).bounds.iloc[0])
    polygon = gdf.dissolve().to_crs(4326).geometry[0]
    r1 = random_point_in_polygon(polygon)
    r2 = random_point_in_polygon(polygon)
    res = pd.DataFrame([r1, r2], columns=["lon", "lat"])
    nodes_ids = network.get_node_ids(res.lon, res.lat).values
    shortest_path = network.shortest_path(nodes_ids[0], nodes_ids[1])
    #network.shortest_path_length(nodes_ids[0], nodes_ids[1])
    graph_i = create_graph(urbanaccess_net.net_nodes, urbanaccess_net.net_edges)

    from IPython import embed; embed()
    get_route_details(graph_i, list(shortest_path))

    """
    #find distance matrix between all restaurants to all restaurant
    restaurants = osm.node_query(bbox[1], bbox[0], bbox[3], bbox[2],
                                 tags='"amenity"="restaurant"')
    restaurant_nodes = network.get_node_ids(restaurants.lon, restaurants.lat)
    origs = [o for o in restaurant_nodes.values for d in restaurant_nodes.values]
    dests = [d for o in restaurant_nodes.values for d in restaurant_nodes.values]
    # this vectorized version of the shortest path computation is way more efficient
    distances = network.shortest_path_lengths(origs, dests)
    print(distances)

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
    #plot_grid(gdf, grid, graph)
