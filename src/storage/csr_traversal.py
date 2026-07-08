from collections import deque
from src.storage.index import GraphIndex


class CSRTraversal:
    def __init__(self, index: GraphIndex):
        self.index = index
        self.hash = index.buf.hash

    def bfs(self, start_id, target_id=None) -> list[str]:
        start = self.hash.node_to_idx[start_id]
        visited = {start}
        order = [start]
        q = deque([start])
        while q:
            u = q.popleft()
            if self.hash.idx_to_node[u] == target_id:
                break
            for v, _ in self.index.get_neighbor_edges(u):
                if v not in visited:
                    visited.add(v)
                    order.append(v)
                    q.append(v)
        return [self.hash.idx_to_node[i] for i in order]
