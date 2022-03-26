
from src import constants as co
from src.preprocessing import graph_utils as gu

import numpy as np
import random


def find_path_picker(id, G, paths, repair_mode, is_oracle=False):
    if len(paths) == 0:
        print("No paths to recover.")
        return

    if id == co.ProtocolPickingPath.RANDOM:
        return __pick_random_repair_path(G, paths)

    elif id == co.ProtocolPickingPath.MAX_BOT_CAP:
        return __pick_cedar_repair_path(G, paths)

    elif id == co.ProtocolPickingPath.MIN_COST_BOT_CAP:
        return __pick_tomocedar_repair_path(G, paths, repair_mode, is_oracle=is_oracle)

    elif id == co.ProtocolPickingPath.MAX_INTERSECT:
        return __pick_max_intersection(G, paths, repair_mode, is_oracle)


def __pick_max_intersection(G, paths, repair_mode, is_oracle):
    """ Picks th epath that has more elements in common with the other paths. """

    path_elements = dict()
    print(paths)
    for pid, pp in enumerate(paths):
        elements = set()
        for i in range(len(pp)-1):
            n1, n2 = gu.make_existing_edge(G, pp[i], pp[i+1])
            elements.add(n1)
            elements.add(n2)
            elements.add((n1, n2))
        path_elements[pid] = elements

    commons_path_elements = {i: 0 for i in range(len(path_elements))}  # path id : his max intersection
    for i in path_elements:
        for j in path_elements:
            if i > j:
                n_commons_path_elements = len(path_elements[i].intersection(path_elements[j]))
                if n_commons_path_elements > commons_path_elements[i]:
                    commons_path_elements[i] = n_commons_path_elements
                if n_commons_path_elements > commons_path_elements[j]:
                    commons_path_elements[j] = n_commons_path_elements

    container_items = sorted(commons_path_elements.items(), key=lambda x: x[1], reverse=True)

    # TIE BREAKING: repair the least expected cost
    # group dict by key
    n_intersections_paths = dict()  # k: number of intersections, v: paths
    for key, value in container_items:
        n_intersections_paths.setdefault(value, []).append(key)

    intersected_paths_ids = list(n_intersections_paths.items())[0][1]
    intersected_paths = [paths[i] for i in intersected_paths_ids]

    if len(intersected_paths) > 1:
        path_to_fix = __pick_tomocedar_repair_path(G, intersected_paths, repair_mode, is_oracle)
    else:
        pid = intersected_paths[0]
        path_to_fix = paths[pid]

    return path_to_fix


def __pick_cedar_repair_path(G, paths):
    if len(paths) > 0:
        # PICK MAX CAPACITY
        # Map the path to its bottleneck capacity
        paths_caps = []
        for path_nodes in paths:
            cap = gu.get_path_residual_capacity(G, path_nodes)
            paths_caps.append(cap)

        path_id_to_fix = np.argmax(paths_caps)
        print("> Selected path to recover has capacity", paths_caps[path_id_to_fix])

        # 5. Repair edges and nodes
        path_to_fix = paths[path_id_to_fix]  # 1, 2, 3
        print("> Repairing path", path_to_fix)
        return path_to_fix


def __pick_tomocedar_repair_path(G, paths, repair_mode, is_oracle=False):
    if len(paths) > 0:
        # 3. Map the path to its bottleneck capacity
        paths_exp_cost = []

        is_oracle = is_oracle and repair_mode == co.ProtocolRepairingPath.MIN_COST_BOT_CAP

        for path_nodes in paths:  # TODO: randomize
            # min_cap = get_path_cost(G, path_nodes)
            exp_cost = gu.get_path_cost_VN(G, path_nodes, is_oracle)  # MINIMIZE expected cost of repair
            paths_exp_cost.append(exp_cost)

        # 4. Get the path that maximizes the minimum bottleneck capacity
        path_id_to_fix = np.argmin(paths_exp_cost)
        print("> Selected path to recover has capacity", gu.get_path_residual_capacity(G, paths[path_id_to_fix]))

        # 5. Repair edges and nodes
        path_to_fix = paths[path_id_to_fix]  # 1, 2, 3
        print("> Repairing path", path_to_fix)
        print("cost >", paths_exp_cost[path_id_to_fix])
        return path_to_fix


def __pick_random_repair_path(G, paths):
    if len(paths) > 0:
        # PICK RANDOM PATH
        path_id_to_fix = random.randint(0, len(paths) - 1)
        print("> Selected path to recover has capacity", gu.get_path_residual_capacity(G, paths[path_id_to_fix]))

        # 5. Repair edges and nodes
        path_to_fix = paths[path_id_to_fix]  # 1, 2, 3
        print("> Repairing path", path_to_fix)
        return path_to_fix
