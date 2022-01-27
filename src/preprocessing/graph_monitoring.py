import numpy as np

from src.preprocessing.graph_utils import *
import networkx as nx
import sys
np.set_printoptions(threshold=sys.maxsize)

import tqdm
import src.utilities.util_routing_stpath as mxv
import scipy.special as sci
import src.utilities.util as util
from itertools import combinations

# OK
# lists of edges are not symmetric, check symmetric edge every time
def broken_paths_without_n(G, paths, broken_paths, broken_edges_T, broken_nodes_T, elements_val_id, elements_id_val, element=None):
    """ Returns the set of paths by ID that contain at least 1 broken element or that do not pass through an element. """

    if broken_paths is None:
        broken_paths = []
        for path_nodes in paths:
            # adds a path to broken_paths if a node or an edge of the path is broken, i.e. the path is broken
            is_path_broken = False

            # check if path broken
            for i in range(len(path_nodes) - 1):
                n1, n2 = path_nodes[i], path_nodes[i + 1]
                n1, n2 = make_existing_edge(G, n1, n2)
                is_path_broken = n1 in broken_nodes_T or n2 in broken_nodes_T or (n1, n2, co.EdgeType.SUPPLY.value) in broken_edges_T
                if is_path_broken:
                    break

            # if the path was working, then set all as discovered working
            if not is_path_broken:
                for i in range(len(path_nodes) - 1):
                    n1, n2 = path_nodes[i], path_nodes[i + 1]
                    n1, n2 = make_existing_edge(G, n1, n2)
                    discover_node(G, n1, 1)
                    discover_node(G, n2, 1)
                    discover_edge(G, n1, n2, 1)
            else:
                # if the path is not working and there is only one unknown or broken element, set it as discovered broken
                broken_unk_path_node = [n for n in path_nodes if G.nodes[n][co.ElemAttr.POSTERIOR_BROKEN.value] > 0]  # uncertainty or broken

                broken_unk_path_edge = []
                for i in range(len(path_nodes) - 1):
                    n1, n2 = path_nodes[i], path_nodes[i + 1]
                    n1, n2 = make_existing_edge(G, n1, n2)
                    if G.edges[n1, n2, co.EdgeType.SUPPLY.value][co.ElemAttr.POSTERIOR_BROKEN.value] > 0:
                        broken_unk_path_edge.append((n1, n2))

                if len(broken_unk_path_node) + len(broken_unk_path_edge) == 1:  # single element is broken or unknown
                    if len(broken_unk_path_node) == 1:
                        bun = broken_unk_path_node[0]
                        discover_node(G, bun, is_working=0)     # bool
                    else:
                        bue = broken_unk_path_edge[0]
                        n1, n2 = make_existing_edge(G, bue[0], bue[1])
                        discover_edge(G, n1, n2, is_working=0)  # bool

                path_els = [elements_val_id[n] for n in path_nodes]
                path_els += [elements_val_id[make_existing_edge(G, path_nodes[i], path_nodes[i + 1])] for i in range(len(path_nodes) - 1)]
                broken_paths.append(path_els)

    paths_out = broken_paths[:]
    remove_ids = []
    if element is not None:
        # saves the index of the path to remove
        for i in range(len(broken_paths)):
            if elements_val_id[element] in broken_paths[i]:
                remove_ids.append(i)

        paths_out = []
        # keeps the paths that are not traversed by 'element'
        for i in range(len(broken_paths)):
            if i not in remove_ids:
                paths_out.append(broken_paths[i])

    return paths_out


def gain_knowledge_of_n_APPROX(SG, element, element_type, broken_paths, broken_paths_padded, tot_els, paths, broken_edges_T,
                            broken_nodes_T, elements_val_id, elements_id_val):
    """ Approximated """

    bp_without_n = broken_paths_without_n(SG, paths, broken_paths, broken_edges_T, broken_nodes_T, elements_val_id, elements_id_val, element=element)
    bp_with_n = set([tuple(p) for p in broken_paths]) - set([tuple(p) for p in bp_without_n])

    working_edges_P = get_element_by_state_KT(SG, co.GraphElement.EDGE, co.NodeState.WORKING, co.Knowledge.KNOW)
    working_nodes_P = get_element_by_state_KT(SG, co.GraphElement.NODE, co.NodeState.WORKING, co.Knowledge.KNOW)
    working_elements_ids = [elements_val_id[make_existing_edge(SG, n1, n2)] for n1, n2, _ in working_edges_P] + [elements_val_id[n] for n in working_nodes_P]

    if element_type == co.GraphElement.EDGE:
        n1, n2 = make_existing_edge(SG, element[0], element[1])
        ide = elements_val_id[(n1, n2)]
    else:
        ide = elements_val_id[element]

    # if the id of the element is in the working nodes, return that the edge works
    if ide in working_elements_ids:
        return 0

    # remove working elements in broken paths with n
    new_bp_with_n = []
    for list_elements in bp_with_n:
        bp = []
        #nodes, edges = get_path_elements(path)
        for n in list_elements:
            if n not in working_elements_ids:
                bp.append(n)
        new_bp_with_n.append(bp)

    # 0 if there's at least a path that crosses the element with len 1
    is_broken = sum([1 for p in new_bp_with_n if len(p) == 1]) > 0
    if is_broken:  # is broken
        return 1

    el_bp = set()
    for li in new_bp_with_n:
        el_bp |= set(li)

    eps = (len(el_bp) - 1) / len(el_bp)
    P = len(new_bp_with_n) / len(el_bp)

    # print(P, len(new_bp_with_n), len(el_bp))
    # print(min(max(np.floor(P) - 1, 0), 1))
    # print(1-eps / P - P)
    # print()
    # print()
    # P  > 0 // < 1 // 1.5

    T2 = P + heavyside(np.floor(P) - 1) * (1 - eps / P - P)
    T1 = np.ceil(sum([np.floor(1/len(p)) for p in new_bp_with_n]) / len(new_bp_with_n))
    C = max(T1, T2)

    if not 1 >= C >= 0:
        print("WARNING! Probability was", C)   # TODO FIX!
        exit()
    return C


def heavyside(x):
    return 1 if x >= 0 else 0


def gain_knowledge_of_n_EXACT(SG, element, element_type, broken_paths, broken_paths_padded, tot_els, paths, broken_edges_T,
                              broken_nodes_T, elements_val_id, elements_id_val):
    bp_without_n = broken_paths_without_n(SG, paths, broken_paths, broken_edges_T, broken_nodes_T, elements_val_id, elements_id_val, element=element)

    broken_paths_without_n_padded = np.zeros(shape=(len(bp_without_n), tot_els))
    for i, p in enumerate(bp_without_n):
        broken_paths_without_n_padded[i, :len(p)] = p

    broken_paths_padded = broken_paths_padded.copy()
    working_edges_P = get_element_by_state_KT(SG, co.GraphElement.EDGE, co.NodeState.WORKING, co.Knowledge.KNOW)
    working_nodes_P = get_element_by_state_KT(SG, co.GraphElement.NODE, co.NodeState.WORKING, co.Knowledge.KNOW)

    working_elements_ids = [elements_val_id[make_existing_edge(SG, n1, n2)] for n1, n2, _ in working_edges_P] + [elements_val_id[n] for n in working_nodes_P]

    if element_type == co.GraphElement.EDGE:
        n1, n2 = make_existing_edge(SG, element[0], element[1])
        a_prior = SG.edges[n1, n2, co.EdgeType.SUPPLY.value][co.ElemAttr.PRIOR_BROKEN.value]
    else:
        a_prior = SG.nodes[element][co.ElemAttr.PRIOR_BROKEN.value]

    if len(bp_without_n) == 0:
        num = 1
    else:
        num = probability_broken(broken_paths_without_n_padded, a_prior, working_elements_ids)

    den = probability_broken(broken_paths_padded, a_prior, working_elements_ids)
    prob_n_broken = a_prior * num / den

    error1 = "den gt prior: {}, {}".format(den, a_prior)
    error2 = "probability leak: {}, {}, {}".format(num, den, prob_n_broken)

    # assert a_prior >= den, error1
    assert 1 >= num >= 0 and 1 >= den >= 0 and 1 >= prob_n_broken >= 0, error2
    return prob_n_broken


def gain_knowledge_tomography(G, stats_packet_monitoring_so_far, threshold_monitor_message, elements_val_id, elements_id_val):
    broken_edges_T = get_element_by_state_KT(G, co.GraphElement.EDGE, co.NodeState.BROKEN, co.Knowledge.TRUTH)
    broken_nodes_T = get_element_by_state_KT(G, co.GraphElement.NODE, co.NodeState.BROKEN, co.Knowledge.TRUTH)

    bubbles = []
    demand_edges_to_repair = []
    demand_edges_routed_flow = []

    # the list of path between demand nodes
    paths = []
    stats_packet_monitoring = 0
    stats_monitors = set()

    # monitors from all the monitor pairs n*(n-1)/2
    SG = get_supply_graph(G)
    # probabilistic_edge_weights(SG, G)

    monitors = get_monitor_nodes(G)
    demand_nodes = get_demand_nodes(G)

    demand_nodes_residual = get_demand_nodes(G, is_residual=True)
    set_useful_monitors = (set(monitors) - demand_nodes).union(demand_nodes_residual)
    only_monitors = set(monitors) - demand_nodes

    iter, n_to_repair_paths = 0, 0
    n_monitor_couples = len(set_useful_monitors) * (len(set_useful_monitors) - 1) / 2
    priority_paths = {}  # k:path, v:priority

    # if stats_packet_monitoring_so_far + stats_packet_monitoring < threshold_monitor_message:  # threshold sui monitoring messages
    halt_monitoring = False
    while iter < n_monitor_couples - n_to_repair_paths and not halt_monitoring:
        print(iter,  n_monitor_couples - n_to_repair_paths, halt_monitoring)
        n_to_repair_paths = 0
        combs = list(combinations(set_useful_monitors, r=2))
        for n1_node, n2_node in tqdm.tqdm(combs, disable=True):

            if stats_packet_monitoring_so_far + stats_packet_monitoring > threshold_monitor_message:
                halt_monitoring = True
                break

            n1, n2 = make_existing_edge(G, n1_node, n2_node)

            if not ((n1, n2) in get_demand_edges(G, is_capacity=False, is_check_unsatisfied=True)
                    or n1 in only_monitors or n2 in only_monitors):
                continue

            went_through, st_path_out = util.safe_exec(mxv.protocol_routing_stpath, (SG, n1, n2))
            stats_packet_monitoring += 1

            if st_path_out is None:
                print("Flow is not routable.")
                exit()

            path, metric = st_path_out
            paths.append(path)

            if metric < len(G.edges):  # works AND has capacity
                if n1 in demand_nodes and n2 in demand_nodes:
                    if is_bubble(G, path):
                        bubbles.append(path)
                        print("Urrà, found a bubble!", n1, n2)
                    else:
                        priority = heuristic_priority_pruning(G, n1, n2)
                        priority_paths[tuple(path)] = priority

            else:  # path is broken
                print("Il path è rotto", metric, path, (n1, n2))
                if n1 in demand_nodes and n2 in demand_nodes:
                    demand_edges_to_repair.append((n1, n2))
                n_to_repair_paths += 1

        # --- choose a pruning path ---

        if len(bubbles) > 0:
            bubble_path = bubbles[0]
            do_prune(G, bubble_path)
        else:
            if len(priority_paths) > 0:
                priority_paths_items = sorted(priority_paths.items(), key=lambda x: x[1])  # path, priority
                lowest_priority = list(priority_paths_items[0][0])
                do_prune(G, lowest_priority)

        demand_nodes_residual = get_demand_nodes(G, is_residual=True)
        set_useful_monitors = (set(monitors) - demand_nodes).union(demand_nodes_residual)

        bubbles = list()
        priority_paths = dict()
        iter += 1

    if len(paths) < 2:
        print("> No monitoring done. No packets left.")
        return stats_monitors, stats_packet_monitoring

    print("Done computing monitoring paths for", len(stats_monitors), "monitors:", stats_monitors)

    n_edges, n_nodes = len(SG.edges), len(SG.nodes)
    tot_els = n_edges + n_nodes

    # broken_paths
    bp = broken_paths_without_n(G, paths, None, broken_edges_T, broken_nodes_T, elements_val_id, elements_id_val, element=None)
    elements_in_paths = set().union(*bp)
    bp_padded = np.zeros(shape=(len(bp), tot_els))
    for i, p in enumerate(bp):
        bp_padded[i, :len(p)] = p

    # Assign a probability to every element
    pars = tot_els, paths, broken_edges_T, broken_nodes_T, elements_val_id, elements_id_val

    new_node_probs = dict()
    new_edge_probs = dict()

    for n1 in tqdm.tqdm(G.nodes, disable=True):
        original_posterior = G.nodes[n1][co.ElemAttr.POSTERIOR_BROKEN.value]
        node_id = G.nodes[n1][co.ElemAttr.ID.value]
        # print(node_id)
        if original_posterior not in [0, 1] and node_id in elements_in_paths:
            prob = gain_knowledge_of_n_APPROX(G, n1, co.GraphElement.NODE, bp, bp_padded, *pars)
            # print((n1), prob)
            new_node_probs[(n1, co.ElemAttr.POSTERIOR_BROKEN.value)] = prob

    for n1, n2, gt in tqdm.tqdm(G.edges, disable=True):
        if gt == co.EdgeType.SUPPLY.value:
            original_posterior = G.edges[n1, n2, gt][co.ElemAttr.POSTERIOR_BROKEN.value]
            edge_id = G.edges[n1, n2, gt][co.ElemAttr.ID.value]
            if original_posterior not in [0, 1] and edge_id in elements_in_paths:
                prob = gain_knowledge_of_n_APPROX(G, (n1, n2), co.GraphElement.EDGE, bp, bp_padded, *pars)
                # print((n1, n2), prob)
                new_edge_probs[(n1, n2, gt, co.ElemAttr.POSTERIOR_BROKEN.value)] = prob

    for k in new_node_probs:
        n1, att = k
        G.nodes[n1][att] = new_node_probs[k]

    for k in new_edge_probs:
        n1, n2, gt, att = k
        G.edges[n1, n2, gt][att] = new_edge_probs[k]

    return stats_monitors, stats_packet_monitoring, demand_edges_to_repair, demand_edges_routed_flow


def probability_broken(padded_paths, prior, working_els):
    """ Credits to: Viviana Arrigoni. """

    # TODO: remove rows with same elements
    """ Viviana version! """
    pp = padded_paths.copy()
    if len(working_els) > 0:
        padded_paths[np.isin(padded_paths, working_els)] = 0

    n_paths = padded_paths.shape[0]
    if n_paths == 0:
        return None       # TODO unlikely it executes it

    if n_paths == 1:
        non_zeros_count = np.sum(padded_paths != 0)
        if non_zeros_count == 0:
            return 0
        return 1 - (1 - prior) ** non_zeros_count

    elif n_paths == 2:
        p1, p2 = padded_paths[0, :], padded_paths[1, :]
        p1p2 = np.array(list(set(p1).union(set(p2))))

        l1, l2, l12 = np.sum(p1 > 0), np.sum(p2 > 0), np.sum(p1p2 > 0)
        return 1 - (1 - prior) ** l1 - (1 - prior) ** l2 + (1 - prior) ** l12

    else:
        target = padded_paths.copy()
        target = target[:-1, :]
        target[np.isin(target, padded_paths[-1, :])] = 0
        non_zeros_count_last = np.sum(padded_paths[-1, :] > 0)

        prob = probability_broken(padded_paths[:-1, :], prior, working_els) - \
               probability_broken(target, prior, working_els) * \
               (1 - prior) ** non_zeros_count_last
        return prob


def gain_knowledge_all(G):
    for n in G.nodes:
        G.nodes[n][co.ElemAttr.POSTERIOR_BROKEN.value] = G.nodes[n][co.ElemAttr.STATE_TRUTH.value]

    for n1, n2, et in G.edges:
        G.edges[n1, n2, et][co.ElemAttr.POSTERIOR_BROKEN.value] = G.edges[n1, n2, et][co.ElemAttr.STATE_TRUTH.value]
