import osmium
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandana as pdn
import urbanaccess as ua
import os

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


class urbanaccess_network(object):
    """
    A urbanaccess object of Pandas DataFrames representing
    the components of a graph network

    Parameters
    ----------
    transit_nodes : pandas.DataFrame
    transit_edges : pandas.DataFrame
    net_connector_edges : pandas.DataFrame
    osm_nodes : pandas.DataFrame
    osm_edges : pandas.DataFrame
    net_nodes : pandas.DataFrame
    net_edges : pandas.DataFrame
    """
    def __init__(self,
                 transit_nodes=pd.DataFrame(),
                 transit_edges=pd.DataFrame(),
                 net_connector_edges=pd.DataFrame(),
                 osm_nodes=pd.DataFrame(),
                 osm_edges=pd.DataFrame(),
                 net_nodes=pd.DataFrame(),
                 net_edges=pd.DataFrame()):
        self.transit_nodes = transit_nodes
        self.transit_edges = transit_edges
        self.net_connector_edges = net_connector_edges
        self.osm_nodes = osm_nodes
        self.osm_edges = osm_edges
        self.net_nodes = net_nodes
        self.net_edges = net_edges

def save_network(urbanaccess_network, dir):
    """
    Write a urbanaccess_network integrated nodes and edges to a node and edge
    feather files

    Parameters
    ----------
    urbanaccess_network : object
        urbanaccess_network object with net_edges and net_nodes DataFrames
    dir : string
        directory to save feather files

    Returns
    -------
    None
    """
    if urbanaccess_network is None or urbanaccess_network.net_edges.empty or \
            urbanaccess_network.net_nodes.empty:
        raise ValueError('Either no urbanaccess_network specified or '
                         'net_edges or net_nodes are empty.')
    urbanaccess_network.net_edges = gpd.GeoDataFrame(urbanaccess_network.net_edges)
    urbanaccess_network.net_edges.reset_index(drop=True).to_feather(f"{dir}/net_edges.feather")
    urbanaccess_network.net_nodes = gpd.GeoDataFrame(urbanaccess_network.net_nodes)
    urbanaccess_network.net_nodes.reset_index(drop=True).to_feather(f"{dir}/net_nodes.feather")

def load_network(dir):
    """
    Read an integrated network node and edge data from feather files to
    a urbanaccess_network object

    Parameters
    ----------
    dir : string
        directory to read feather files
    Returns
    -------
    ua_network : object
        urbanaccess_network object with net_edges and net_nodes DataFrames
    ua_network.net_edges : object
    ua_network.net_nodes : object
    """
    ua_network = urbanaccess_network()
    ua_network.net_edges = pd.read_feather(f"{dir}/net_edges.feather")
    ua_network.net_nodes = pd.read_feather(f"{dir}/net_nodes.feather")
    return ua_network


def create_nx_graph(nodes, edges, retain_all=False, bidirectional=False):
    metadata = {
        "crs": "EPSG:4326"
    }
    G = nx.MultiDiGraph(**metadata)

    # Remove edges with uknown nodes
    edges = edges[edges['to_int'].isin(nodes.index) & edges['from_int'].isin(nodes.index)]

    # Add nodes from the nodes DataFrame
    for id, row in nodes.iterrows():
        G.add_node(id, x=row["x"], y=row["y"])

    # Add edges from the edges DataFrame
    for _, row in edges.iterrows():
        G.add_edge(row['from_int'],
                   row['to_int'],
                   travel_time=row['weight'],
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
    edges = edges[edges['to_int'].isin(nodes.index) & edges['from_int'].isin(nodes.index)]
    network = pdn.Network(nodes["x"],
                           nodes["y"],
                           edges["from_int"],
                           edges["to_int"],
                           edges[["weight"]],
                           twoway=False)
    network.precompute(3000)
    return network


def get_integrated_graph(gdf, graph_w, processed_path, gtfs_path):
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
    integrated_edges_path= f"{processed_path}/net_edges.feather"
    integrated_nodes_path= f"{processed_path}/net_nodes.feather"
    if os.path.exists(integrated_edges_path) and os.path.exists(integrated_nodes_path):
        print("Loading integrated network")
        urbanaccess_net = load_network(dir=processed_path)
    else:
        print("Building integrated network")
        bbox = tuple(gdf.dissolve().to_crs(4326).bounds.iloc[0])
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
