from collections import defaultdict
from src.storage.schemas import Node, Edge
from src.storage.store import CSRBuffer


class GraphIndex:
    def __init__(self, buffer:CSRBuffer):
        self.relation_index = defaultdict(lambda: defaultdict(list)) # switch from 1D list to 2 level dict
        self.label_to_node_index = defaultdict(list) # label : [node_idxs...]
        self.node_to_label_index: dict[int, str] = {} # node_idx : label
        self.buf = buffer

    def add_edge(self, edge:Edge):
        src_idx = self.buf.hash.node_to_idx[edge.src_name]
        dst_idx = self.buf.hash.node_to_idx[edge.dst_name]
        edge_props = edge.props
        if dst_idx not in self.relation_index[edge.relation_type][src_idx]:
            self.relation_index[edge.relation_type][src_idx].append(dst_idx)
        self.buf._add_edge(src_idx, dst_idx, edge_props)

    def add_node(self, node:Node):
        self.buf._add_node(node)
        node_idx = self.buf.hash.node_to_idx[node.name]
        self.label_to_node_index[node.label].append(node_idx)
        self.node_to_label_index[node_idx] = node.label

    def get_edges_by_relation_type(self, relation_type: str) -> list[tuple[str, str]]:
        edges_by_relation = []
        for src_idx in self.relation_index[relation_type]:
            for dst_idx in self.relation_index[relation_type][src_idx]:
                edges_by_relation.append((src_idx, dst_idx))
        return [(self.buf.hash.idx_to_node[src], self.buf.hash.idx_to_node[dst]) for src, dst in edges_by_relation]
    
    def get_neighbors(self, node_name: str):
        return self.buf.hash._neighbors(node_name, self.buf.csr, self.buf)
    
    def get_neighbor_edges(self, node_name:str):
        return self.buf.hash._neighbor_edges(node_name, self.buf.csr, self.buf)
    
    def get_neighbors_by_relation(self, node_name:str, relation_type:str):
        src_idx = self.buf.hash.node_to_idx[node_name]
        neighbors = [dst_idx for dst_idx in self.relation_index[relation_type][src_idx]]
        neighbor_names = [self.buf.hash.idx_to_node[dst] for dst in neighbors]

        return neighbor_names
    
    def get_neighbor_edges_by_relation(self, node_name: str, relation_type: str) -> list[str, dict]:
        src_idx = self.buf.hash.node_to_idx[node_name]
        results: list[str, dict] = []
        for dst_idx in self.relation_index[relation_type][src_idx]:
            dst_name = self.buf.hash.idx_to_node[dst_idx]
            props = self.get_edge_props(node_name, dst_name)
            results.append((dst_name, props))
        return results
    
    def get_nodes_by_label(self, label:str) -> list[str]:
        return [self.buf.hash.idx_to_node[node] for node in self.label_to_node_index[label]]

    def get_node_label(self, node_name: str) -> str:
        node_idx = self.buf.hash.node_to_idx[node_name]
        return self.node_to_label_index[node_idx]

    def has_node(self, node_name:str) -> bool:
        return node_name in self.buf.hash.node_to_idx
    
    def get_node_props(self, node_name:str) -> dict:
        idx = self.buf.hash.node_to_idx[node_name]
        if idx is None:
            raise KeyError(f"{node_name} doesn't exist")
        return self.buf.hash.node_props[idx]
    
    def get_edge_props(self, src_name:str, dst_name:str) -> dict:
        src_idx = self.buf.hash.node_to_idx[src_name]
        dst_idx = self.buf.hash.node_to_idx[dst_name]
        csr_props = {}
        csr_props_flag = False
        buf_props_flag = False
        buf_props = {}
        if src_idx in self.buf.pendingBuffer:
            for edge_dst, buf_edge_props in self.buf.pendingBuffer[src_idx]:
                if edge_dst == dst_idx:
                    buf_props = buf_edge_props
                    buf_props_flag = True
        if self.buf.csr.indptr is not None:
            start, end = self.buf.csr.indptr[src_idx], self.buf.csr.indptr[src_idx+1]
            for i, csr_dst_idx in enumerate(self.buf.csr.indices[start:end]):
                if csr_dst_idx == dst_idx:
                    csr_props = self.buf.csr.edge_props[start+i]
                    csr_props_flag = True
        
        if not buf_props_flag and not csr_props_flag:
            raise KeyError(f"No props found for pair ({(src_name, dst_name)})")
        
        return {**csr_props, **buf_props} # csr first, buf second ; later key wins in unpacking conflict