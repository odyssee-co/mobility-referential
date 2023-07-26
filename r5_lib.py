from r5py import TransportNetwork, TravelTimeMatrixComputer, TransportMode
import utils


if not os.path.exists(path_osm):
    ox.save_graph_xml(graph, filepath=path_osm)
if not os.path.exists(path_pbf):
    utils.osm_to_pbf(path_osm, path_pbf)

transport_network = TransportNetwork(path_pbf, [gtfs_file])

car_tt_path = f"{processed_path}/car_tt.feather"
if not os.path.exists(car_tt_path):
    print("Computing car travel times matrix")
    travel_time_matrix_computer = TravelTimeMatrixComputer(
        transport_network,
        origins=grid,
        transport_modes=[TransportMode.CAR])
    car_tt = travel_time_matrix_computer.compute_travel_times()
    car_tt.reset_index(drop=True).to_feather(car_tt_path)
else:
    print("Loading car travel times matrix")
    car_tt = pd.read_feather(car_tt_path)

pt_tt_path = f"{processed_path}/pt_tt.feather"
if not os.path.exists(pt_tt_path):
    print("Computing public transports travel times matrix")
    travel_time_matrix_computer = TravelTimeMatrixComputer(
        transport_network,
        departure=datetime.datetime(2023,7,1,8,30),
        origins=grid,
        transport_modes=[TransportMode.TRANSIT])
    pt_tt = travel_time_matrix_computer.compute_travel_times()
    pt_tt.reset_index(drop=True).to_feather(pt_tt_path)
else:
    print("Loading public transports travel times matrix")
    pt_tt = pd.read_feather(pt_tt_path)

walk_tt_path = f"{processed_path}/walk_tt.feather"
if not os.path.exists(walk_tt_path):
    print("Computing walking travel times matrix")
    travel_time_matrix_computer = TravelTimeMatrixComputer(
        transport_network,
        origins=grid,
        transport_modes=[TransportMode.WALK])
    walk_tt = travel_time_matrix_computer.compute_travel_times()
    walk_tt.reset_index(drop=True).to_feather(walk_tt_path)
else:
    print("Loading walk travel times matrix")
    walk_tt = pd.read_feather(walk_tt_path)

bike_tt_path = f"{processed_path}/bike_tt.feather"
if not os.path.exists(bike_tt_path):
    print("Computing bike travel times matrix")
    travel_time_matrix_computer = TravelTimeMatrixComputer(
        transport_network,
        origins=grid,
        transport_modes=[TransportMode.BICYCLE])
    bike_tt = travel_time_matrix_computer.compute_travel_times()
    bike_tt.reset_index(drop=True).to_feather(bike_tt_path)
else:
    print("Loading bike travel times matrix")
    bike_tt = pd.read_feather(bike_tt_path)
