import osmium
import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandana as pdn
import urbanaccess as ua
from urbanaccess.network import ua_network
from patched_ua import integrate_network
import pickle
from IPython import embed

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
    if edges.empty or nodes.empty:
        raise ValueError("Net_edges or net_nodes are empty.")
    nodes = gpd.GeoDataFrame(nodes)
    edges = gpd.GeoDataFrame(edges)
    graph = {"nodes": nodes, "edges": edges}
    with open(path, "wb") as file:
        pickle.dump(graph, file)


def load_graph(path):
    with open(path, "rb") as file:
        graph = pickle.load(file)
    nodes = graph["nodes"]
    edges = graph["edges"]
    return nodes, edges


"""
def save_graph(nodes, edges, dir, name):
    if edges.empty or nodes.empty:
        raise ValueError("Net_edges or net_nodes are empty.")
    nodes = gpd.GeoDataFrame(nodes)
    nodes.reset_index(drop=True).to_feather(f"{dir}/{name}_nodes.feather")
    edges = gpd.GeoDataFrame(edges)
    edges.reset_index(drop=True).to_feather(f"{dir}/{name}_edges.feather")


def load_graph(dir, name):
    nodes = pd.read_feather(f"{dir}/{name}_nodes.feather")
    edges = pd.read_feather(f"{dir}/{name}_edges.feather")
    return nodes, edges
"""


def create_nx_graph(nodes, edges, retain_all=False, bidirectional=False):
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


def create_pdn_graph(nodes, edges):
    """
    Create a hierarchical graph to greatly improve the shortest paths computations
    see: "A Generalized Computational Framework for Accessibility: From
    the Pedestrian to the Metropolitan Scale" for more details
    """

    # Remove edges with uknown nodes
    edges = edges[edges["to_int"].isin(nodes.index) & edges["from_int"].isin(nodes.index)]
    network = pdn.Network(nodes["x"],
                           nodes["y"],
                           edges["from_int"],
                           edges["to_int"],
                           edges[["weight"]],
                           twoway=False)
    network.precompute(3000)
    return network


def get_integrated_graph(gdf, nodes, edges, processed_path, gtfs_path):
    """
    Retrieve or build an integrated multi-modal transportation network graph
    for a specified geographic area.

    Parameters:
    - gdf (geopandas.GeoDataFrame): The GeoDataFrame representing the geographic
      area of interest.
    - graph_w (ox.Graph): The walking network graph for the same area.

    Returns:
    - ua_network (ua.network.ua_network): The integrated multi-modal
      transportation network.
    """
    print("Building integrated network")
    bbox = tuple(gdf.dissolve().to_crs(4326).bounds.iloc[0])
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
