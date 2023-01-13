# -*- coding:utf-8 -*-
# Copyright(C) Huawei Technologies Co.,Ltd. 2022. All rights reserved.

import networkx as nx
import matplotlib.pyplot as plt


class KgPainter:
    def __init__(self, nodes, edges):
        self.graph = nx.Graph()
        self.nodes = self._wrap_nodes(nodes)
        self.edges = self._wrap_edges(edges)

    def start_kg_paint_job(self, output_path):
        pass

    def _paint(self):
        pass

    def save_figure(self):
        pass

    def _wrap_nodes(self, nodes):
        return

    def _wrap_edges(self, edges):
        return


node_list = [
    {
        "group": 1,
        "id": 0,
        "level": 0,
        "name": "FailedToLoadTheModel_Alarm"
    },
    {
        "group": 1,
        "id": 1,
        "level": 0,
        "name": "NotifyWaitExecuteFailed_Alarm",
        "rootCause": True
    },
    {
        "group": 1,
        "id": 2,
        "level": 0,
        "name": "FailedToApplyForResources_Alarm",
        "rootCause": True
    },
    {
        "group": 1,
        "id": 3,
        "level": 0,
        "name": "MemoryAsyncCopyFailed_Alarm",
        "rootCause": True
    },
    {
        "group": 1,
        "id": 4,
        "level": 1,
        "name": "RegisteredResourcesExceedsTheMaximum_Alarm",
        "rootCause": True
    },
    {
        "group": 1,
        "id": 5,
        "level": 2,
        "name": "FailedToexecuteTheAICpuOperator_Alarm",
        "rootCause": True
    },
    {
        "group": 1,
        "id": 6,
        "level": 2,
        "name": "RuntimeFaulty_Alarm"
    },
    {
        "group": 1,
        "id": 7,
        "level": 0,
        "name": "FailedToRestartTheProcess_Alarm"
    }
]

relation_list = [
    {
        "source": 7,
        "target": 6,
        "value": 1
    },
    {
        "source": 3,
        "target": 6,
        "value": 1
    },
    {
        "source": 2,
        "target": 7,
        "value": 1
    },
    {
        "source": 0,
        "target": 6,
        "value": 1
    },
    {
        "source": 5,
        "target": 6,
        "value": 1
    },
    {
        "source": 4,
        "target": 0,
        "value": 1
    },
    {
        "source": 1,
        "target": 6,
        "value": 1
    }
]

if __name__ == '__main__':

    graph = nx.DiGraph()
    COLOR_LIST = ["b", "g", "r"]

    id_to_name = dict()
    for node in node_list:
        node_id, node_name, node_level = node.get("id"), node.get("name"), int(node.get("level"))
        id_to_name[node_id] = node_name
        color = COLOR_LIST[node_level] if node_level < 3 else "r"
        graph.add_node(node_name, node_color=color)

    for edge in relation_list:
        source_id, target_id, rel_value = edge.get("source"), edge.get("target"), edge.get("value")
        start_name, target_name = id_to_name.get(source_id), id_to_name.get(target_id)
        graph.add_edge(start_name, target_name, value=int(rel_value))

    pos = nx.circular_layout(graph)

    plt.figure(figsize=(10, 10))
    plt.subplot(111)

    nx.draw(graph, pos, with_labels=True)

    # set edge value
    edge_value = nx.get_edge_attributes(graph, "value")
    nx.draw_networkx_edge_labels(graph, pos, edge_value)
    plt.show()
