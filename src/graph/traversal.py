from collections import deque
import heapq
from src.storage.index import GraphIndex

class GraphTraversal:
    def __init__(self, index: GraphIndex):
        self.index = index

    def bfs(self, start, relation_type=None, max_depth=None):
        # TODO: WE should augment edges return here.
        visited_set = set()
        traversed_path: list[tuple] = [] # nodes + edges
        q = deque()
        visited_set.add(start)
        q.append((start, 0)) # 0 is depth

        while q:
            current_node, depth = q.popleft()
            traversed_path.append((current_node,depth))
            if max_depth is not None and depth >= max_depth:
                continue # skips all nodes past depth but still computes nodes at max_depth by ignoring.
            neighbors = self.index.get_neighbors(current_node) if not relation_type else self.index.get_edges_by_relation_type(relation_type)
            for neighbor in neighbors:
                if neighbor not in visited_set:
                    visited_set.add(neighbor)
                    q.append((neighbor, depth + 1))
        
        return traversed_path

    def shortest_path(self, start, end, weight_key=None): # dijikstra if weight, fall back to bfs otherwise
        if weight_key is None:
            # TODO: BFS till end
            pass
        