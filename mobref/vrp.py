import vroom
import pandas as pd

def solve_vrp(network, vehicles, jobs):
    """
    Solve the Vehicle Routing Problem (VRP) for a given network, vehicles, and jobs.

    Args:
        network: Network object representing the transportation network.
        vehicles (pandas.DataFrame): DataFrame containing vehicle information.
        jobs (pandas.DataFrame): DataFrame containing job (delivery point) information.

    Returns:
        vroom.Solution: Solution object containing the optimized VRP solution.
    """
    jobs["id"] = ["job_" + str(i) for i in range(len(jobs))]
    vehicles["id"] = ["vehicle_" + str(i) for i in range(len(vehicles))]
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
