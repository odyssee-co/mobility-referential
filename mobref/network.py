import osmnx as ox
import pandas as pd
import numpy as np
import os
from mobref.graph_utils import create_pdn_graph, get_integrated_graph, load_graph, save_graph
import matplotlib
from matplotlib import pyplot as plt
import math
import urbanaccess as ua

class Network():

    def __init__(self, area, mode, processed_path, gtfs_path=None):
        """
        Initialize a transportation network for a specified area and mode.

        Args:
            area: Area object representing the specified geographic area.
            mode (str): Mode of transportation (transit, drive, bike, or walk).
            processed_path (str): Path to the processed data directory.
            gtfs_path (str, optional): Path to the GTFS (General Transit Feed Specification) data. Required only for transit mode.
        """
        if mode == "transit" and gtfs_path == None:
            raise Exception("No gtfs provided when mode is set to transit")
        self.processed_path = processed_path
        self.area = area
        self.mode = mode
        self.gtfs_path = gtfs_path
        self.create_network()


    def create_network(self):
        """
        Create and integrate a transportation network based on the specified mode (transit, drive, bike, or walk).

        Returns:
        None: Integrated network nodes and edges are stored in the corresponding attributes.
        """
        path = f"{self.processed_path}/{self.mode}.pkl"
        if os.path.exists(path):
            print(f"Loading {self.mode} network...")
            nodes, edges = load_graph(path)
        else:
            #cf = '["highway"~"motorway|trunk|primary|secondary"]'
            if self.mode == "transit":
                graph_w_path = f"{self.processed_path}/walk.pkl"
                if os.path.exists(graph_w_path):
                    nodes, edges = load_graph(graph_w_path)
                else:
                    print("Downloading walk network...")
                    graph = ox.graph_from_polygon(self.area.polygon, network_type="walk")
                    nodes, edges = ox.graph_to_gdfs(graph)
                nodes, edges = get_integrated_graph(self.area, nodes, edges, self.processed_path, self.gtfs_path)
            else:
                print(f"Downloading {self.mode} network...")
                graph = ox.graph_from_polygon(self.area.polygon, network_type=self.mode)
                if self.mode=="drive":
                    graph = ox.add_edge_speeds(graph)
                    graph = ox.add_edge_travel_times(graph)
                    nodes, edges = ox.graph_to_gdfs(graph)
                elif self.mode=="bike":
                    nodes, edges = ox.graph_to_gdfs(graph)
                    edges = edges.to_crs("epsg:32633") #because bike network is projected
                    travel_time = edges["length"] / (20/3.6) #TODO adapt bike speed to topography
                    edges["travel_time"] = travel_time.values
                elif self.mode=="walk":
                    nodes, edges = ox.graph_to_gdfs(graph)
                    travel_time =  edges["length"] / (4.8/3.6)
                    edges["travel_time"] = travel_time.values
                edges["weight"] = edges.travel_time
                edges["from_int"]=edges.index.get_level_values(0)
                edges["to_int"]=edges.index.get_level_values(1)
            save_graph(nodes, edges, path)
        self.pdn = create_pdn_graph(nodes, edges)
        self.nodes = nodes
        self.edges= edges
        print() #cleaner stdout

    def convert_path_to_osmid(self, path):
        """
        Converts a list of node IDs to OSM IDs.

        Args:
        path (list): List of node IDs.

        Returns:
        list: List of corresponding OSM IDs.
        """
        path_osmid = []
        for n in path:
            path_osmid.append(self.nodes.loc[n].id)
        return path_osmid


    def shortest_path(self, r1, r2):
        """
        Finds the shortest path between two locations and returns route details.

        Args:
        r1 (dict): Dictionary with keys 'lon' and 'lat' representing the coordinates of the starting point.
        r2 (dict): Dictionary with keys 'lon' and 'lat' representing the coordinates of the destination.

        Returns:
        dict: A dictionary containing the following keys:
        - "shortest_path" (list): List of node IDs representing the shortest path.
        - "travel_time" (float): Total travel time along the shortest path.
        - "distance" (float): Total distance of the shortest path.
        """
        req = pd.DataFrame([r1, r2], columns=["lon", "lat"])
        nodes_ids = self.pdn.get_node_ids(req.lon, req.lat).values
        shortest_path = self.pdn.shortest_path(nodes_ids[0], nodes_ids[1])
        if self.mode == "transit":
            shortest_path = self.convert_path_to_osmid(shortest_path)
        route_details = self.get_route_details(list(shortest_path))
        res = { "shortest_path": shortest_path,
                "travel_time"  : route_details["travel_time"],
                "distance"     : route_details["distance"]}
        return res


    def get_route_details(self, route):
        """
        Calculates travel time and distance for the given route.

        Args:
        route (list): List of node IDs representing the route.

        Returns:
        dict: A dictionary containing the following keys:
        - "travel_time" (float): Total travel time along the route.
        - "distance" (float): Total distance of the route.
        """
        travel_time = 0
        distance = 0
        if route==[]:
            return None, None
        for i in range(len(route)-1):
            data = self.edges.loc[route[i], route[i+1], 0]
            travel_time += data["travel_time"]
            if not np.isnan(data["length"]): #tt travels have nan distances
                distance += data["length"]
        return {"travel_time":travel_time, "distance":distance}


    def get_matrices(self, pois):
        """
        Computes matrices of travel times and distances between given Points of Interest (POIs).

        Args:
        pois (DataFrame): DataFrame containing POI locations with columns 'lon' and 'lat'.

        Returns:
        dict: A dictionary containing the following keys:
        - "time" (DataFrame): Matrix of travel times between POIs.
        - "distance" (DataFrame): Matrix of distances between POIs.
        """
        pois_nodes = self.pdn.get_node_ids(pois.lon, pois.lat)
        origs = [o for o in pois_nodes.values for d in pois_nodes.values]
        dests = [d for o in pois_nodes.values for d in pois_nodes.values]
        # this vectorized version of the shortest path computation is way more efficient than calling multiple times shortest_path_length
        times = self.pdn.shortest_path_lengths(origs, dests)
        n = int(math.sqrt(len(times)))
        a = np.array(times).reshape((n, n))
        m_t = pd.DataFrame(a, index=pois.index, columns=pois.index)
        pdn = create_pdn_graph(self.nodes, self.edges, impedence="length")
        distances = pdn.shortest_path_lengths(origs, dests)
        a = np.array(distances).reshape((n, n))
        m_d = pd.DataFrame(a, index=pois.index, columns=pois.index)
        return {"time": m_t, "distance": m_d}

    def find_closest(self, pois, maxtime=600, maxitems=None):
        """
        Finds the closest Points of Interest (POIs) to each location within a maximum travel time.

        Args:
        pois (DataFrame): DataFrame containing POI locations with columns 'lon' and 'lat'.
        maxtime (int, optional): Maximum travel time in seconds. Defaults to 600.
        maxitems (int, optional): Maximum number of closest POIs to return for each location. Defaults to None.

        Returns:
        dict: A dictionary containing closest POIs to each location. Keys are node IDs, and values are lists of
        dictionaries containing 'poi_id', 'lon', 'lat', and 'travel_time' for each nearby POI.
        """
        self.pdn.set_pois(category = 'pois',
                          maxdist = maxtime,
                          maxitems = maxitems,
                          x_col = pois.lon,
                          y_col = pois.lat)
        results = self.pdn.nearest_pois(distance = maxtime,
                                       category = 'pois',
                                       num_pois = maxitems,
                                       include_poi_ids = True)
        return results


    def plot_accessibility(self, pois, time=300):
        """
        Plots accessibility of Points of Interest (POIs) within the given time limit from each location.

        Args:
        pois (DataFrame): DataFrame containing POI locations with columns 'lon' and 'lat'.
        time (int, optional): Maximum travel time in seconds. Defaults to 300.
        """
        #how many pois are within time seconds of each node?
        pois_nodes = self.pdn.get_node_ids(pois.lon, pois.lat)
        self.pdn.set(pois_nodes, name = 'pois')
        accessibility = self.pdn.aggregate(time, type = 'count', name = 'pois')
        fig, ax = plt.subplots(figsize=(10,8))
        plt.title(f'Restaurants within {time/60}min by {self.mode}')
        plt.scatter(self.pdn.nodes_df.x, self.pdn.nodes_df.y,
                    c=accessibility, s=1, cmap='YlOrBr',
                    norm=matplotlib.colors.LogNorm())
        cb = plt.colorbar()
        plt.show()


    def plot_net_by_travel_time(self):
        """
        Plots the network graph with edge colors based on travel time.
        """
        edgecolor = ua.plot.col_colors(df=self.edges, col='weight', cmap='Blues', num_bins=5)
        ua.plot.plot_net(nodes=self.nodes,
                         edges=self.edges,
                         bbox=self.area.bbox,
                         fig_height=30, margin=0.02,
                         edge_color=edgecolor, edge_linewidth=1, edge_alpha=0.7,
                         node_color='black', node_size=0, node_alpha=1, node_edgecolor='none', node_zorder=3, nodes_only=False)
