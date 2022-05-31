
import src.plotting.graph_plotting as pg
from src.preprocessing.graph_preprocessing import *
from src.preprocessing.graph_monitoring import *
from src.preprocessing.graph_utils import *
import src.constants as co
import src.utilities.util_routing_stpath as mxv

from src.recovery_protocols import finder_recovery_path as frp
from src.recovery_protocols import finder_recovery_path_pick as frpp
from src.monitor_placement_protocols import adding_monitors as mon

import time

import src.preprocessing.graph_utils as gru
from gurobipy import *

def run(config):
    stats_list = []

    # read graph and print stats
    G, elements_val_id, elements_id_val = init_graph(co.PATH_TO_GRAPH, config.graph_path, config.supply_capacity, config)
    print_graph_info(G)

    # normalize coordinates and break components
    dim_ratio = scale_coordinates(G)

    distribution, broken_nodes, broken_edges, perc_broken_elements = destroy(G, config.destruction_type, config.destruction_precision, dim_ratio,
                                                                             config.destruction_width, config.n_destruction, config.graph_dataset, config.seed, ratio=config.destruction_quantity,
                                                                             config=config)

    # add_demand_endpoints
    if config.is_demand_clique:
        add_demand_clique(G, config.n_demand_clique, config.demand_capacity, config)
    else:
        add_demand_pairs(G, config.n_demand_pairs, config.demand_capacity, config)

    # hypothetical routability
    if not is_feasible(G, is_fake_fixed=True):
        print("This instance is not solvable. Check the number of demand edges, theirs and supply links capacity.\n\n\n")
        return

    routed_flow = 0
    packet_monitor = 0
    monitors_stats = set()

    K = 2
    # repair demand edges
    demand_node = get_demand_nodes(G)
    for dn in demand_node:
        do_repair_node(G, dn)
        monitors_stats |= {dn}
        G.nodes[dn][co.ElemAttr.IS_MONITOR.value] = True
        packet_monitor += do_k_monitoring(G, dn, K)
        # INITIAL NODES repairs are not counted in the stats

    iter = 0

    assert config.monitors_budget == -1 or config.monitors_budget >= len(get_demand_nodes(G)), \
        "budget is {}, demand nodes are {}".format(config.monitors_budget, len(get_demand_nodes(G)))

    # start of the protocol
    while len(get_demand_edges(G, is_check_unsatisfied=True)) > 0:
        # go on if there are demand edges to satisfy, and still is_feasible


        print("\n\n", "#" * 40, "BEGIN ITERATION", "#" * 40)
        print(len(get_demand_edges(G, is_check_unsatisfied=True)), "demands to prune")

        # check if the graph is still routbale on tot graph,
        if not is_feasible(G, is_fake_fixed=True):
            print("This instance is no more routable!")
            return stats_list

        iter += 1
        print("ITER", iter)

        # packet_monitor -- monitors paced up to iteration i
        # monitors -- monitors placed up to now (no duplicates)
        stats = {"iter": iter,
                 "node": [],
                 "edge": [],
                 "flow": routed_flow,
                 "monitors": monitors_stats,
                 "packet_monitoring": packet_monitor}

        SG = get_supply_graph(G)
        paths = []
        for d1, d2, _ in get_demand_edges(G, is_check_unsatisfied=True):
            path, _, _ = mxv.protocol_repair_cedarlike(SG, d1, d2)
            paths.append(path)

        # filter paths
        paths_filter = []
        for pa in paths:
            if is_known_path(G, pa):
                paths_filter.append(pa)

        if len(paths_filter) > 0:
            path_to_fix = frpp.find_path_picker(co.ProtocolPickingPath.CEDAR_LIKE_MIN, G, paths_filter, None, False)
            print("Chose to repair", path_to_fix)
            fixed_nodes, fixed_edges = do_fix_path(G, path_to_fix)
            stats["edge"] += fixed_nodes
            stats["node"] += fixed_edges

            quantity_pruning = do_prune(G, path_to_fix)
            routed_flow += quantity_pruning
            print("pruned", quantity_pruning, "on", path_to_fix)
        else:
            if len(get_monitor_nodes(G)) < config.monitors_budget:
                v = best_centrality_node(G)
                fixed_node = do_repair_node(G, v)
                if fixed_node:
                    stats["node"] += [fixed_node]

                monitors_stats |= {v}
                G.nodes[v][co.ElemAttr.IS_MONITOR.value] = True
                stats["monitors"] |= monitors_stats

                # k-discovery
                packets_monitoring = do_k_monitoring(G, v, K)
                stats["packet_monitoring"] = packets_monitoring
            else:
                print("No monitors left.")
                stats_list.append(stats)
                return stats_list

        stats_list.append(stats)

    return stats_list