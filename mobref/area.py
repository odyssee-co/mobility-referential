import geopandas as gpd
import os
import numpy as np
from itertools import product
from shapely.geometry import Point
import osmnx as ox
from matplotlib import pyplot as plt
from shapely.ops import nearest_points
import random
from pandana.loaders import osm
import pandas as pd

class Area():

    def __init__(self, processed_path, municipalities_path, administrative_cutting_path):
        """
        Initializes an Area object with geographic data.

        Args:
        processed_path (str): Path to processed data.
        municipalities_path (str): Path to municipalities data.
        administrative_cutting_path (str): Path to administrative cutting.
        """
        self.processed_path = processed_path
        self.municipalities_path = municipalities_path
        self.administrative_cutting_path = administrative_cutting_path
        self.make_gdf()
        self.bbox = tuple(self.gdf.dissolve().to_crs(4326).bounds.iloc[0])
        self.polygon = self.gdf.dissolve().to_crs(4326).geometry[0]

    def make_gdf(self):
        """
        Load or process geographical data and store it in a GeoDataFrame (gdf).

        This function first checks if the processed area data file exists. If it does, it loads
        the data into a GeoDataFrame. If not, it processes the area data from the specified
        municipalities file and administrative cutting path, filters the data based on
        'insee' values, and saves the processed data to a feather file. The resulting GeoDataFrame
        is stored in the instance variable `self.gdf`.
        """
        area_path = f"{self.processed_path}/area.feather"
        if os.path.exists(area_path):
            print("Loading area...")
            gdf = gpd.read_feather(area_path)
        else:
            print("Processing area...")
            muni = open(self.municipalities_path).read().split("\n")
            gdf = gpd.read_file(self.administrative_cutting_path).to_crs(4326)
            gdf = gdf[gdf["insee"].isin(muni)]
            gdf.reset_index(drop=True).to_feather(area_path)
        self.gdf = gdf
        print() #cleaner stdout

    def make_grid(self, grid_size):
        """
        Create a grid of points within the bounding box of the given GeoDataFrame.

        Args:
        grid_size (float): Size of the grid
        """

        grid_path = f"{self.processed_path}/grid.feather"
        if os.path.exists(grid_path):
            print("Loading grid...")
            grid = gpd.read_feather(grid_path)
        else:
            print("Processing grid...")
            min_lon, min_lat, max_lon, max_lat = self.gdf.total_bounds
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
            grid = gpd.clip(points, self.gdf)
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
        self.grid = grid


    def plot_grid(self, net):
        roads = net.nodes
        ax = self.gdf.plot()
        roads.plot(ax=ax, color="white", linewidth=1, alpha=0.2, zorder=3)
        self.grid.plot(ax=ax, color="red", markersize=5, zorder=10)
        ax.set_axis_off()
        plt.show()

    def get_grid_id(self, x, y):
        """
        Get the ID of the grid cell closest to the specified coordinates (x, y).

        Args:
        x (float): X-coordinate of the point.
        y (float): Y-coordinate of the point.

        Returns:
        int: ID of the grid cell

        Raises:
        Exception: If no grid has been set.
        """
        grid = self.grid
        if not grid:
            raise Exception("No grid have been set.")
        geometry = gpd.GeoSeries(gpd.points_from_xy(grid.x, grid.y))
        g = grid.copy()
        g["geometry"] = geometry
        queried, nearest = nearest_points(Point(x, y), geometry.unary_union)
        return int(grid[g.geometry == nearest].index[0])

    def random_point(self):
        """
        Generate a random point within the bounding area defined by the GeoDataFrame.

        Returns:
        tuple: A tuple containing the X and Y coordinates of the randomly generated point.
        """
        polygon = self.gdf.dissolve().to_crs(4326).geometry[0]
        min_x, min_y, max_x, max_y = polygon.bounds

        # Generate a random point within the bounding box of the polygon
        random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))

        # Check if the random point is within the polygon
        while not polygon.contains(random_point):
            random_point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))

        return (random_point.x, random_point.y)


    def random_points(self, n):
        """
        Generate a DataFrame of n random points within the bounding area defined by the GeoDataFrame.

        Args:
        n (int): Number of random points to generate.

        Returns:
        pandas.DataFrame: DataFrame containing 'n' random points with columns 'lat' and 'lon'.
        """
        points = []
        for i in range(n):
            x, y = self.random_point()
            points.append({"lat": y, "lon": x})
        return pd.DataFrame(points)


    def find_pois(self, tags):
        """
        Find points of interest within the area based on specified OSM tags.

        Args:
        tags (str): OSM tags in the format '"key"="value"', for example, '"amenity"="restaurant"'.

        Returns:
        gpd.GeoDataFrame: GeoDataFrame containing points of interest within the specified area.
        """
        bbox = self.bbox
        pois = osm.node_query(bbox[1], bbox[0], bbox[3], bbox[2],tags)
        #filter pois that are outside the area
        pois = gpd.GeoDataFrame(pois, geometry=gpd.points_from_xy(pois.lon, pois.lat))
        pois = pois[self.polygon.contains(pois.geometry)]
        return pois
