from collections import defaultdict
from src.storage.schemas import Node, Edge
from src.storage.store import CSRBuffer


class GraphIndex:
    def __init__(self, buffer:CSRBuffer):
        self.secondary_index = defaultdict(list)
        self.buf = buffer

    def add_edge(self, edge:Edge):
        src = self.buf.hash.node_to_idx[edge.src_id]
        dst = self.buf.hash.node_to_idx[edge.dest_id]
        edge_props = edge.props
        if (src, dst) not in self.secondary_index[edge.relation_type]:
            self.secondary_index[edge.relation_type].append((src, dst))
        self.buf._add_edge(src, dst, edge_props)

    def add_node(self, node:Node):
        self.buf._add_node(node)

    def get_edges_by_relation_type(self, relation_type) -> list[tuple]:
        return self.secondary_index[relation_type]
    
    def get_neighbors(self, node_id):
        return self.buf.hash._neighbors(node_id, self.buf.csr, self.buf)
    
    def get_neighbors_by_relation(self, node_id, relation_type):
        src_idx = self.buf.hash.node_to_idx[node_id]
        neighbors = [(src, dst) for src, dst in self.secondary_index[relation_type] if src == src_idx]
        neighbor_names = [self.buf.hash.idx_to_node[dst] for _, dst in neighbors]

        return neighbor_names
    
    def get_node_props(self, node_id) -> dict:
        idx = self.buf.hash.node_to_idx[node_id]
        if idx is None:
            raise KeyError(f"{node_id} doesn't exist")
        return self.buf.hash.node_props[idx]
    
    def get_edge_props(self, src_id, dst_id) -> dict:
        src = self.buf.hash.node_to_idx[src_id]
        dst = self.buf.hash.node_to_idx[dst_id]
        csr_props = {}
        csr_props_flag = False
        buf_props_flag = False
        buf_props = {}
        if src in self.buf.pendingBuffer:
            for edge_dst, buf_edge_props in self.buf.pendingBuffer[src]:
                if edge_dst == dst:
                    buf_props = buf_edge_props
                    buf_props_flag = True
        if self.buf.csr.indptr is not None:
            start, end = self.buf.csr.indptr[src], self.buf.csr.indptr[src+1]
            for i, dst_idx in enumerate(self.buf.csr.indices[start:end]):
                if dst_idx == dst:
                    csr_props = self.buf.csr.edge_props[start+i]
                    csr_props_flag = True
        
        if not buf_props_flag and not csr_props_flag:
            raise KeyError(f"No props found for pair ({(src_id, dst_id)})")
        
        return {**csr_props, **buf_props} # csr first, buf second ; later key wins in unpacking conflict