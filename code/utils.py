import osmium
import pandas as pd
import geopandas as gpd

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
