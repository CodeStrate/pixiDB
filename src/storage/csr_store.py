import numpy as np
from src.storage.schemas import Node, Edge
from collections import defaultdict

class CSR:
    def __init__(self):
        self.indices = None # JA
        self.indptr = None # IA
        self.edge_props = None # A

    @classmethod
    def csr_from_arrays(cls, indices, indptr, edge_props):
        obj = cls()
        obj.indices = np.array(indices)
        obj.indptr = np.array(indptr)
        obj.edge_props = np.array(edge_props)
        return obj

    def _build_csr(self, edges, num_nodes):
        # sort by src
        graph_edges = sorted(edges, key=lambda e: e[0]) # edges are [(src, dest, props/vals), (...), ..]

        edge_counts = np.zeros(num_nodes, dtype=int)
        indices = []
        vals = []
        for src, dest, props in graph_edges: 
            edge_counts[src] += 1
            indices.append(dest)
            vals.append(props)

        self.indptr = np.concatenate([[0], np.cumsum(edge_counts)])
        self.indices = np.array(indices)
        self.edge_props = np.array(vals)


class CSRHash:
    def __init__(self):  
        self.node_to_idx = {}
        self.idx_to_node = {}
        self.node_props = {}

    def _add_node_hash(self, node: Node):
        if node.node_id not in self.node_to_idx:
            idx = len(self.node_to_idx) 
            self.node_to_idx[node.node_id] = idx
            self.idx_to_node[idx] = node.node_id
            self.node_props[idx] = node.props
        else:
            raise ValueError(f'{node.node_id} already exists in hash.')

    def _neighbors(self, node_id, csr:CSR, buf: "CSRBuffer"):
        idx = self.node_to_idx[node_id]
        csr_neighbors = []
        buf_neighbors = buf.pendingBuffer.get(idx, [])
        if csr.indptr is not None:
            start, end = csr.indptr[idx], csr.indptr[idx+1]
            csr_neighbors = list(csr.indices[start:end]) if csr.indices is not None else []

        neighbor_names = [self.idx_to_node[i] for i in csr_neighbors] + [self.idx_to_node[dst] for dst, _ in buf_neighbors]

        return neighbor_names
    
class CSRBuffer:
    def __init__(self, threshold):
        self.pendingBuffer = defaultdict(list)
        self.pendingCount: int = 0
        self.hash = CSRHash()
        self.csr = CSR()

        self.threshold = threshold

    def add_edge(self, edge: Edge):
        src = self.hash.node_to_idx[edge.src_id]
        dst = self.hash.node_to_idx[edge.dest_id]
        props = edge.props
        self.pendingBuffer[src].append((dst, props))
        self.pendingCount += 1
        if self.pendingCount >= self.threshold:
            self._compact()
    
    def add_node(self, node:Node):
        self.hash._add_node_hash(node)

    def _compact(self):
        # collect all csr edges

        all_edges: list = []
        if self.csr.indices is not None:
            for src in range(len(self.csr.indptr) - 1):
                for i, dst in enumerate(self.csr.indices[self.csr.indptr[src]:self.csr.indptr[src+1]]):
                    all_edges.append((src, dst, self.csr.edge_props[self.csr.indptr[src] + i]))

        # collect all buf edges

        for src, vals in self.pendingBuffer.items():
            for dst, props in vals:
                all_edges.append((src, dst, props))

        self.csr._build_csr(all_edges, num_nodes= len(self.hash.node_to_idx))

        self.pendingBuffer.clear()
        self.pendingCount = 0
