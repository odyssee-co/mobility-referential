import geopandas as gpd
import os
import numpy as np
from itertools import product
from shapely.geometry import Point
import osmnx as ox
from matplotlib import pyplot as plt
from shapely.ops import nearest_points
import random

def get_gdf(data_path, processed_path, municipalities_file):
    """
    Load or process a GeoDataFrame (gdf) representing a specific geographic zone
    by filtering it based on a list of municipality IDs read from a file.
    The resulting GeoDataFrame is then saved as a Feather file for future use and returned.

    Returns:
    - gdf (geopandas.GeoDataFrame): A GeoDataFrame representing the geographic zone.
    """

    zone_path = f"{processed_path}/zone.feather"
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

def make_grid(gdf, processed_path, grid_size):
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

def random_point_in_area(gdf):
    """
    This function generates a random point within a given polygon. It ensures that the generated point is located
    inside the specified polygon by repeatedly generating points within the bounding box of the polygon until
    a point inside the polygon is found.

    Parameters:
        polygon (shapely.geometry.Polygon): The polygon within which to generate the random point.

    Returns:
        tuple: A tuple containing the x and y coordinates of the generated random point.
    """
    polygon = gdf.dissolve().to_crs(4326).geometry[0]
    min_x, min_y, max_x, max_y = polygon.bounds

    # Generate a random point within the bounding box of the polygon
    random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))

    # Check if the random point is within the polygon
    while not polygon.contains(random_point):
        random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        
    return random_point.x, random_point.y
