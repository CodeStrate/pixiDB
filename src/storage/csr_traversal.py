from collections import deque
from src.storage.csr_indexing import CSRIndexing


class CSRTraversal:
    def __init__(self, indexing: CSRIndexing):
        self.indexing = indexing
        self.hash = indexing.buf.hash

    def bfs(self, start_id, target_id=None) -> list[str]:
        start = self.hash.node_to_idx[start_id]
        visited = {start}
        order = [start]
        q = deque([start])
        while q:
            u = q.popleft()
            if self.hash.idx_to_node[u] == target_id:
                break
            for v, _ in self.indexing.get_neighbor_edges(u):
                if v not in visited:
                    visited.add(v)
                    order.append(v)
                    q.append(v)
        return [self.hash.idx_to_node[i] for i in order]
