import numpy as np
from src.storage.schemas import Node
from collections import defaultdict
import warnings

class CSR:
    def __init__(self):
        self.indices = None # JA
        self.indptr = None # IA
        self.edge_props = None # A

    @classmethod
    def csr_from_arrays(cls, indices: np.ndarray, indptr: np.ndarray, edge_props: np.ndarray):
        obj = cls()
        obj.indices = np.array(indices)
        obj.indptr = np.array(indptr)
        obj.edge_props = np.array(edge_props)
        return obj

    def _build_csr(self, edges: list[tuple], num_nodes: int):
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
        if node.name not in self.node_to_idx:
            idx = len(self.node_to_idx) 
            self.node_to_idx[node.name] = idx
            self.idx_to_node[idx] = node.name
            self.node_props[idx] = node.props
        else:
            warnings.warn(f'{node.name} already exists in hash, skipping.', UserWarning)

    def _neighbors(self, node_name: str, csr:CSR, buf: "CSRBuffer"):
        idx = self.node_to_idx[node_name]
        csr_neighbors = []
        buf_neighbors = buf.pendingBuffer.get(idx, [])
        if csr.indptr is not None:
            start, end = csr.indptr[idx], csr.indptr[idx+1]
            csr_neighbors = list(csr.indices[start:end]) if csr.indices is not None else []

        neighbor_names = [self.idx_to_node[i] for i in csr_neighbors] + [self.idx_to_node[dst] for dst, _ in buf_neighbors]

        return neighbor_names

    def _neighbor_edges(self, node_name: str, csr: CSR, buf: "CSRBuffer") -> list[tuple[str, dict]]:
        idx = self.node_to_idx[node_name]
        edges = []
        if csr.indptr is not None:
            start, end = csr.indptr[idx], csr.indptr[idx + 1]
            for i in range(start, end):
                edges.append((self.idx_to_node[csr.indices[i]], csr.edge_props[i]))
        edges.extend([(self.idx_to_node[dst], edge_props) for dst, edge_props in buf.pendingBuffer.get(idx, [])])
        return edges

class CSRBuffer:
    def __init__(self, threshold):
        self.pendingBuffer = defaultdict(list)
        self.pendingCount: int = 0
        self.hash = CSRHash()
        self.csr = CSR()

        self.threshold = threshold

    def _add_edge(self, src_idx: int, dst_idx: int, props: dict):
        if src_idx in self.pendingBuffer:
            for i, values in enumerate(self.pendingBuffer[src_idx]):
                old_dst_idx, old_props = values
                if dst_idx == old_dst_idx:
                    self.pendingBuffer[src_idx][i] = (dst_idx, {**old_props, **props})
                    return
        self.pendingBuffer[src_idx].append((dst_idx, props))
        self.pendingCount += 1
        if self.pendingCount >= self.threshold:
            self._compact()
    
    def _add_node(self, node:Node):
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
