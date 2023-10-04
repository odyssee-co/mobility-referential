import osmnx as ox
import pandas as pd
import numpy as np
import os
from graph_utils import create_nx_graph, create_pdn_graph, get_integrated_graph
import networkx as nx
from IPython import embed

class Network():

    def __init__(self, gdf, mode, processed_path, gtfs_path=None):
        if mode == "transit" and gtfs_path == None:
            raise Exception("No gtfs provided when mode is set to transit")
        self.processed_path = processed_path
        self.gdf = gdf
        self.mode = mode
        self.gtfs_path = gtfs_path
        self.ml, self.pdn = self.create_network()


    def create_network(self):
        area = self.gdf.dissolve().to_crs(4326)
        path = f"{self.processed_path}/graph_{self.mode}.graphml"
        if os.path.exists(path):
            print(f"Loading {self.mode} network")
            graph = ox.load_graphml(path)
        else:
            print(f"Downloading {self.mode} network")
            #cf = '["highway"~"motorway|trunk|primary|secondary"]'
            if self.mode == "transit":
                graph = ox.graph_from_polygon(area.geometry[0], network_type="walk")
                urbanaccess_net = get_integrated_graph(self.gdf, graph, self.processed_path, self.gtfs_path)
                graph = create_nx_graph(urbanaccess_net.net_nodes, urbanaccess_net.net_edges)
                ox.save_graphml(graph, filepath=path)
            else:
                graph = ox.graph_from_polygon(area.geometry[0], network_type=self.mode)
                if self.mode=="drive":
                    graph = ox.add_edge_speeds(graph)
                    graph = ox.add_edge_travel_times(graph)
                elif self.mode=="bike":
                    edges = ox.graph_to_gdfs(graph, nodes=False)
                    edges = edges.to_crs("epsg:32633") #because bike network is projected
                    travel_time = edges["length"] / (20/3.6) #TODO adapt bike speed to topography
                    edges["travel_time"] = travel_time.values
                    nx.set_edge_attributes(graph, values=edges["travel_time"], name="travel_time")
                    nx.set_edge_attributes(graph, values=edges["geometry"], name="geometry")
                elif self.mode=="walk":
                    edges = ox.graph_to_gdfs(graph, nodes=False)
                    travel_time =  edges["length"] / (4.8/3.6) #4.8 Km/H = 3 M/H
                    edges["travel_time"] = travel_time.values
                    nx.set_edge_attributes(graph, values=edges["travel_time"], name="travel_time")
                ox.save_graphml(graph, filepath=path)
        nodes, edges = ox.graph_to_gdfs(graph)
        edges["weight"] = edges.travel_time
        edges["from_int"]=edges.index.get_level_values(0)
        edges["to_int"]=edges.index.get_level_values(1)
        pdn_graph = create_pdn_graph(nodes, edges)
        return graph, pdn_graph


    def shortest_path(self, r1, r2):
        req = pd.DataFrame([r1, r2], columns=["lon", "lat"])
        nodes_ids = self.pdn.get_node_ids(req.lon, req.lat).values
        shortest_path = self.pdn.shortest_path(nodes_ids[0], nodes_ids[1])
        travel_time, distance = self.get_route_details(list(shortest_path))
        res = { "shortest_path": shortest_path,
                "travel_time"  : travel_time,
                "distance"     : distance}
        return res


    def get_route_details(self, route):
        """
        Calculate travel time and distance for a given route on a graph.

        Parameters:
        - graph (NetworkX Graph): The graph representing the transportation network.
        - route (list): A list of nodes representing the route to be analyzed.

        Returns:
        - travel_time (float): The total travel time along the route (sum of travel times for individual edges).
        - distance (float): The total distance covered along the route (sum of edge lengths).
        """
        travel_time = 0
        distance = 0
        if not route:
            return None, None
        for i in range(len(route)-1):
            data = self.ml.get_edge_data(route[i], route[i+1])[0]
            travel_time += data["travel_time"]
            if not np.isnan(data["length"]): #necessary because tt travels have nan distances
                distance += data["length"]
        return travel_time, distance


    """
    def get_matrices(graph, grid):
        tt_matrix = []
        d_matrix = []
        for i, j in product(grid.index, grid.index):
            route = ox.shortest_path(graph, grid.id.iloc[i], grid.id.iloc[j],
                                 weight='travel_time', cpus=None)
            tt, d = get_route_details(graph, route)
            tt_matrix.append({"from_id": grid.id[i], "to_id": grid.id[j], "travel_time": tt})
            d_matrix.append({"from_id": grid.id[i], "to_id": grid.id[j], "distance": d})
        return pd.DataFrame(tt_matrix), pd.DataFrame(d_matrix)
    """
