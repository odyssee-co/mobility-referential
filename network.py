from tqdm.contrib.itertools import product
import osmnx as ox
import pandas as pd

def get_route_details(graph, route):
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
