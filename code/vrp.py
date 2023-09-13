import vroom
problem_instance = vroom.Input()
problem_instance.set_durations_matrix(
     profile="car",
     matrix_input=[[0, 2104, 197, 1299],
                   [2103, 0, 2255, 3152],
                   [197, 2256, 0, 1102],
                   [1299, 3153, 1102, 0]],
)
problem_instance.add_vehicle([vroom.Vehicle(47, start=0, end=0),
                               vroom.Vehicle(48, start=2, end=2)])
problem_instance.add_job([vroom.Job(1414, location=0),
                           vroom.Job(1515, location=1),
                           vroom.Job(1616, location=2),
                           vroom.Job(1717, location=3)])
solution = problem_instance.solve(exploration_level=5, nb_threads=4)
solution.summary.cost
solution.routes[["vehicle_id", "type", "arrival", "location_index", "id"]]
from IPython import embed; embed()
