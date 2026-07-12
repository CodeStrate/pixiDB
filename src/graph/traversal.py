from collections import deque
import heapq
from src.storage.index import GraphIndex

class GraphTraversal:
    def __init__(self, index: GraphIndex):
        self.index = index

    def bfs(self, start, relation_type=None, node_label=None, max_depth=None):
        # TODO: WE should augment edges return here.
        if not self.index.has_node(start):
            return []
        
        visited_set = set()
        traversed_path: list[tuple] = [] # nodes + edges
        q = deque()
        visited_set.add(start)
        q.append((start, 0)) # 0 is depth

        while q:
            current_node, depth = q.popleft()
            traversed_path.append((current_node, depth))
            if max_depth is not None and depth >= max_depth:
                continue # skips all nodes past depth but still computes nodes at max_depth by ignoring.
            neighbors = self.index.get_neighbors(current_node) if relation_type is None else self.index.get_neighbors_by_relation(current_node, relation_type)
            neighbor_nodes = [node for node in neighbors if self.index.get_node_label(node) == node_label] if node_label is not None else neighbors
            for neighbor in neighbor_nodes:
                if neighbor not in visited_set:
                    visited_set.add(neighbor)
                    q.append((neighbor, depth + 1))
            
        
        return traversed_path

    def shortest_path(self, start, end, weight_key=None): # dijkstra if weight, fall back to bfs otherwise
        if not self.index.has_node(start) or not self.index.has_node(end):
            return []

        if start == end:
            return [start]

        if weight_key is None:
            return self._bfs_shortest_path(start, end)
        return self._dijkstra_shortest_path(start, end, weight_key)

    def _bfs_shortest_path(self, start, end):
        parent = {start: None}
        q = deque([start])

        while q:
            current_node = q.popleft()
            if current_node == end:
                return self._reconstruct_path(parent, end)
            for neighbor in self.index.get_neighbors(current_node):
                if neighbor not in parent:
                    parent[neighbor] = current_node
                    q.append(neighbor)

        return []

    def _dijkstra_shortest_path(self, start, end, weight_key):
        parent = {start: None}
        dist = {start: 0}
        heap = [(0, start)]

        while heap:
            current_dist, current_node = heapq.heappop(heap)
            if current_node == end:
                return self._reconstruct_path(parent, end)
            if current_dist > dist[current_node]:
                continue # stale entry: a shorter path to this node was already found

            for neighbor, props in self.index.get_neighbor_edges(current_node):
                weight = props.get(weight_key, 1)
                if weight < 0:
                    raise ValueError(
                        f"Negative edge weight ({weight}) between {current_node} and {neighbor} "
                        "is not supported by Dijkstra's algorithm."
                    )

                new_dist = current_dist + weight
                if new_dist < dist.get(neighbor, float('inf')):
                    dist[neighbor] = new_dist
                    parent[neighbor] = current_node
                    heapq.heappush(heap, (new_dist, neighbor))

        return []

    @staticmethod
    def _reconstruct_path(parent, end):
        path = []
        node = end
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path
