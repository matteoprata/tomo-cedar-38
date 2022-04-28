import numpy as np

import src.constants as co


class Configuration:
    def __init__(self):
        self.seed = 10

        self.mute_log = False
        self.algo_name = co.AlgoName.CEDARNEW.value
        self.graph_dataset = co.GraphName.MINNESOTA
        self.graph_path = self.graph_dataset.value

        self.destruction_show_plot = False
        self.destruction_save_plot = False

        self.destruction_type = co.Destruction.GAUSSIAN_PROGRESSIVE
        self.destruction_quantity = None

        self.destruction_width = .05
        self.destruction_precision = 1000  # density of the [1,0] grid
        self.n_destruction = 2

        self.demand_capacity: float = 10.0  # if this > that, multiple paths required to fix
        self.supply_capacity = (30, None)

        # clique world
        self.is_demand_clique = False
        self.n_demand_clique = 5

        # Edges world
        self.n_demand_pairs = 6
        self.n_demand_pairs = int(self.n_demand_clique * (self.n_demand_clique-1) / 2) if self.is_demand_clique else self.n_demand_pairs

        self.rand_generator_capacities = None
        self.rand_generator_path_choice = None
        self.monitoring_type = co.PriorKnowledge.TOMOGRAPHY

        self.monitors_budget = 25
        self.monitors_budget_residual = None
        self.monitoring_messages_budget = np.inf

        self.n_backbone_pairs = 5
        self.percentage_flow_backbone = 1  # increase in flow quantity

        self.repairing_mode = None  # co.ProtocolRepairingPath.MIN_COST_BOT_CAP
        self.picking_mode = None  # co.ProtocolPickingPath.MIN_COST_BOT_CAP

        # self.is_adaptive_prior = True
        self.is_oracle_baseline = False  # baseline TOMOCEDAR
        self.fixed_unvarying_seed = 0
        self.experiment_ind_var = None

        self.is_dynamic_prior = True
        self.UNK_prior = None

        self.protocol_monitor_placement = None  # co.ProtocolMonitorPlacement.STEP_BY_STEP
        self.is_exhaustive_paths = True

        self.force_recompute = True
        self.log_execution_details = True

