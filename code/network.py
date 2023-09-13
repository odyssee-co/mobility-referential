from tqdm.contrib.itertools import product
import osmnx as ox
import pandas as pd

def get_route_details(graph, route):
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
        data = graph.get_edge_data(route[i], route[i+1])[0]
        travel_time += data["travel_time"]
        distance += data["length"]
    return travel_time, distance

def get_matrices(graph, grid):
    """
    Calculate travel time and distance matrices for pairs of locations in a grid
    using a given network graph.

    Parameters:
    - graph (ox.Graph): The network graph representing the transportation network.
    - grid (pd.DataFrame): A DataFrame containing information about grid locations,
      including their IDs.

    Returns:
    - tt_matrix (pd.DataFrame): A DataFrame containing travel time values between
      each pair of locations.
    - d_matrix (pd.DataFrame): A DataFrame containing distance values between
      each pair of locations.
    """

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
#parallel version is slower than single process
def process_pair(args):
    graph, from_id, to_id = args
    route = ox.shortest_path(graph, from_id, to_id, weight='travel_time', cpus=None)
    tt, d = get_route_details(graph, route)
    return {"from_id": from_id, "to_id": to_id, "travel_time": tt}, {"from_id": from_id, "to_id": to_id, "distance": d}

def get_matrices_parallel(graph, grid):
    tt_matrix = []
    d_matrix = []
    pair_list = [(graph, grid.id.iloc[i], grid.id.iloc[j])
                 for i, j in product(grid.index, grid.index)]
    with Pool() as pool, tqdm(total=len(pair_list)) as pbar:
        results = []
        for result in pool.imap_unordered(process_pair, pair_list):
            results.append(result)
            pbar.update(1)
    for tt, d in results:
        tt_matrix.append(tt)
        d_matrix.append(d)
    return pd.DataFrame(tt_matrix), pd.DataFrame(d_matrix)
"""
