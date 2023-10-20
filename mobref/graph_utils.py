import osmium
import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandana as pdn
import urbanaccess as ua
from urbanaccess.network import ua_network
from mobref.patched_ua import integrate_network
import pickle

# Convert the .osm file to .osm.pbf format using osmium
class OSMToPBFHandler(osmium.SimpleHandler):
    """
    OSMToPBFHandler is a handler class for converting OSM data to PBF format.

    This class inherits from osmium.SimpleHandler and overrides methods to process OSM data types
    (nodes, ways, relations) and write them to a PBF file using the provided writer.
    """

    def __init__(self, writer):
        super(OSMToPBFHandler, self).__init__()
        self.writer = writer
    def node(self, n):
        self.writer.add_node(n)
    def way(self, w):
        self.writer.add_way(w)
    def relation(self, r):
        self.writer.add_relation(r)

def osm_to_pbf(graph_input, graph_output):
    """
    Convert OSM data to PBF format.

    This function takes an input OSM file, processes its data using the OSMToPBFHandler,
    and writes the result to an output PBF file.

    Args:
        graph_input (str): The path to the input OSM file.
        graph_output (str): The path to the output PBF file.
    """
    writer = osmium.SimpleWriter(graph_output)
    handler = OSMToPBFHandler(writer)
    handler.apply_file(graph_input)
    writer.close()


def save_graph(nodes, edges, path):
    """
        Save graph nodes and edges as a dictionary and store it in a binary file.

    Args:
        nodes (pandas.DataFrame): DataFrame containing node information.
        edges (pandas.DataFrame): DataFrame containing edge information.
        path (str): Path to the file where the graph will be saved.

    Raises:
        ValueError: If either the 'nodes' or 'edges' DataFrame is empty.
    """
    if edges.empty or nodes.empty:
        raise ValueError("Net_edges or net_nodes are empty.")
    nodes = gpd.GeoDataFrame(nodes)
    edges = gpd.GeoDataFrame(edges)
    graph = {"nodes": nodes, "edges": edges}
    with open(path, "wb") as file:
        pickle.dump(graph, file)


def load_graph(path):
    """
    Load graph nodes and edges from a binary file.

    Args:
        path (str): Path to the file containing the saved graph.

    Returns:
        pandas.DataFrame, pandas.DataFrame: Loaded nodes and edges DataFrames.
    """
    with open(path, "rb") as file:
        graph = pickle.load(file)
    nodes = graph["nodes"]
    edges = graph["edges"]
    return nodes, edges


def create_nx_graph(nodes, edges, retain_all=False, bidirectional=False):
    """
    Create a NetworkX graph from nodes and edges DataFrames.

    Args:
        nodes (pandas.DataFrame): DataFrame containing node information.
        edges (pandas.DataFrame): DataFrame containing edge information.
        retain_all (bool, optional): If True, retain all nodes even if not connected. Default is False.
        bidirectional (bool, optional): If True, create a bidirectional graph. Default is False.

    Returns:
        networkx.MultiDiGraph: NetworkX graph created from the nodes and edges DataFrames.
    """
    metadata = {
        "crs": "EPSG:4326"
    }
    G = nx.MultiDiGraph(**metadata)

    # Remove edges with uknown nodes
    edges = edges[edges["to_int"].isin(nodes.index) & edges["from_int"].isin(nodes.index)]

    # Add nodes from the nodes DataFrame
    for id, row in nodes.iterrows():
        G.add_node(id, orig_id=row["id"], x=row["x"], y=row["y"])

    # Add edges from the edges DataFrame
    for _, row in edges.iterrows():
        G.add_edge(row["from_int"],
                   row["to_int"],
                   travel_time=row["weight"],
                   length=row["distance"])

    # retain only the largest connected component if retain_all is False
    if not retain_all:
        G = ox.utils_graph.get_largest_component(G)

    return G


def create_pdn_graph(nodes, edges, impedence="weight"):
    """

    Create a hierarchical graph for efficient shortest paths computations
    see: "A Generalized Computational Framework for Accessibility: From
    the Pedestrian to the Metropolitan Scale" for more details

    Args:
        nodes (pandas.DataFrame): DataFrame containing node information.
        edges (pandas.DataFrame): DataFrame containing edge information.
        impedance (str, optional): Edge attribute representing impedance for path calculations. Default is "weight".

    Returns:
        pdn.Network: pandana graph created from nodes and edges DataFrames.
    """

    # Remove edges with uknown nodes
    edges = edges[edges["to_int"].isin(nodes.index) & edges["from_int"].isin(nodes.index)]
    network = pdn.Network(nodes["x"],
                           nodes["y"],
                           edges["from_int"],
                           edges["to_int"],
                           edges[[impedence]],
                           twoway=False)
    network.precompute(3000)
    return network


def get_integrated_graph(area, nodes, edges, processed_path, gtfs_path):
    """
    Retrieve or build an integrated multi-modal transportation network graph
    for a specified geographic area.

    Args:
        area: Area object representing the specified geographic area.
        nodes (pandas.DataFrame): DataFrame containing node information.
        edges (pandas.DataFrame): DataFrame containing edge information.
        processed_path (str): Path to the processed data directory.
        gtfs_path (str): Path to the GTFS (General Transit Feed Specification) data.

    Returns:
        pandas.DataFrame, pandas.DataFrame: Integrated network nodes and edges DataFrames.
    """
    print("Building integrated network")
    nodes["id"]=nodes.index

    edges = edges.to_crs("epsg:32633")
    edges["distance"] = edges["length"]
    #edges["distance"] = edges.to_crs(2154).length

    edges["from"]=edges.index.get_level_values(0)
    edges["to"]=edges.index.get_level_values(1)

    walking_speed_kph = 4.8
    edges["weight"] = edges["distance"] / ((walking_speed_kph*1000)/60)
    # assign node and edge net type
    edges["net_type"] = "walk"
    nodes["net_type"] = "walk"
    ua_network.osm_nodes = nodes
    ua_network.osm_edges = edges

    loaded_feeds = ua.gtfs.load.gtfsfeed_to_df(gtfs_path,
                                               validation=True,
                                               verbose=True,
                                               bbox=area.bbox,
                                               remove_stops_outsidebbox=True,
                                               append_definitions=True)
    #Simplify transit feeds
    stops_inside_box = []
    loaded_feeds.stops["geometry"] = gpd.points_from_xy(loaded_feeds.stops.stop_lon, loaded_feeds.stops.stop_lat)
    print("Removing stops that are outside area")
    for id, s in loaded_feeds.stops.iterrows():
        if area.polygon.contains(s.geometry):
            stops_inside_box.append(s.stop_id)
    loaded_feeds.stops = loaded_feeds.stops[loaded_feeds.stops["stop_id"].
                                                    isin(stops_inside_box)]
    loaded_feeds.stop_times = loaded_feeds.stop_times[loaded_feeds.
                                stop_times["stop_id"].isin(stops_inside_box)]

    ua.gtfs.network.create_transit_net(gtfsfeeds_dfs=loaded_feeds,
                                       day="monday",
                                       timerange=["07:00:00", "10:00:00"],
                                       calendar_dates_lookup=None)
    ua.gtfs.headways.headways(gtfsfeeds_df=loaded_feeds,
                              headway_timerange=["07:00:00","10:00:00"])

    integrate_network(urbanaccess_network=ua_network,
                             headways=True,
                             urbanaccess_gtfsfeeds_df=loaded_feeds,
                             headway_statistic="mean")
    ua_network.net_nodes = ua_network.net_nodes[["id", "x", "y"]]
    ua_network.net_edges = ua_network.net_edges[["weight", "unique_trip_id",
    "sequence", "unique_route_id", "net_type", "from", "to", "from_int", "to_int", "length",
    "service", "distance", "mean"]]
    ua_network.net_edges["weight"] *= 60 #to convert time in seconds
    ua_network.net_edges["travel_time"] = ua_network.net_edges["weight"]
    ua_network.net_edges["key"] = 0 #for consistancy with osmnx
    ua_network.net_edges.set_index(["from", "to", "key"], drop=False, inplace=True)
    duplicates = ua_network.net_edges.index.duplicated(keep='first')
    ua_network.net_edges = ua_network.net_edges[~duplicates].set_index(["from", "to", "key"])
    return ua_network.net_nodes, ua_network.net_edges
