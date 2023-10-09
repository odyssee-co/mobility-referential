import vroom
import pandas as pd

def solve_vrp(network, vehicles, jobs):
    jobs["id"] = ["job_" + str(i) for i in range(1, len(jobs) + 1)]
    vehicles["id"] = ["vehicle_" + str(i) for i in range(1, len(vehicles) + 1)]
    pois = pd.concat([jobs, vehicles])
    pois.index = pd.RangeIndex(start=0, stop=len(pois), step=1)
    matrix = network.get_matrices(pois)["time"]
    problem_instance = vroom.Input()
    problem_instance.set_durations_matrix(profile="car",
                                          matrix_input=matrix.values.tolist())
    for index, v in pois.iterrows():
        type, n = v.id.split("_")
        n = int(n)
        if type == "vehicle":
            problem_instance.add_vehicle([vroom.Vehicle(n, start=index, end=index)])
        elif type == "job":
            problem_instance.add_job([vroom.Job(n, location=index)])
    solution = problem_instance.solve(exploration_level=5, nb_threads=4)
    return solution
