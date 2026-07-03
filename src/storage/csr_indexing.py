from collections import defaultdict
from src.storage.schemas import Node, Edge
from src.storage.csr_store import CSRBuffer


class CSRIndexing:
    def __init__(self, buffer:CSRBuffer):
        self.secondary_index = defaultdict(list)
        self.buf = buffer

    def add_edge(self, edge:Edge):
        src = self.buf.hash.node_to_idx[edge.src_id]
        dst = self.buf.hash.node_to_idx[edge.dest_id]
        if (src, dst) in self.secondary_index[edge.relation_type]:
            return
        self.secondary_index[edge.relation_type].append((src, dst))
        self.buf._add_edge(edge)

    def add_node(self, node:Node):
        self.buf._add_node(node)

    def get_edges_by_relation_type(self, relation_type) -> list[tuple]:
        return self.secondary_index[relation_type]