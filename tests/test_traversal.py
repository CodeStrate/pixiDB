import pytest
from src.storage.schemas import Node, Edge
from src.storage.store import CSRBuffer
from src.storage.index import GraphIndex
from src.graph.traversal import GraphTraversal


# --- shared fixtures (built on conftest's alice/bob/graphdb_paper/ml_paper) ---

@pytest.fixture
def indexing(alice, bob, graphdb_paper, ml_paper):
    buf = CSRBuffer(threshold=100)
    idx = GraphIndex(buf)
    idx.add_node(alice)
    idx.add_node(bob)
    idx.add_node(graphdb_paper)
    idx.add_node(ml_paper)
    return idx


@pytest.fixture
def populated_indexing(indexing, edge_alice_graphdb, edge_alice_ml,
                       edge_bob_ml, edge_graphdb_ml):
    # Alice -> GraphDB Paper -> ML Paper (2 hops)
    # Alice -> ML Paper directly (1 hop)
    # Bob -> ML Paper
    indexing.add_edge(edge_alice_graphdb)
    indexing.add_edge(edge_alice_ml)
    indexing.add_edge(edge_bob_ml)
    indexing.add_edge(edge_graphdb_ml)
    return indexing


@pytest.fixture
def traversal(populated_indexing):
    return GraphTraversal(populated_indexing)


@pytest.fixture
def weighted_traversal():
    # a --(w=1)--> b --(w=1)--> c --(w=2)--> d   total weight 4, 3 hops
    # a --(w=10)-----------------------------> c  direct edge, then c->d (w=2)
    #                                              total weight 12, 2 hops
    buf = CSRBuffer(threshold=100)
    idx = GraphIndex(buf)
    for n in ["a", "b", "c", "d", "isolated"]:
        idx.add_node(Node(n, "label"))
    idx.add_edge(Edge("a", "b", "rel", {"weight": 1}))
    idx.add_edge(Edge("b", "c", "rel", {"weight": 1}))
    idx.add_edge(Edge("c", "d", "rel", {"weight": 2}))
    idx.add_edge(Edge("a", "c", "rel", {"weight": 10}))
    return GraphTraversal(idx)


# --- shortest_path: general / shared edge cases ---

def test_shortest_path_same_node_returns_single_node(traversal):
    assert traversal.shortest_path("Alice", "Alice") == ["Alice"]


def test_shortest_path_unknown_start_returns_empty(traversal):
    assert traversal.shortest_path("Unknown", "Alice") == []


def test_shortest_path_unknown_end_returns_empty(traversal):
    assert traversal.shortest_path("Alice", "Unknown") == []


def test_shortest_path_both_unknown_returns_empty(traversal):
    assert traversal.shortest_path("Unknown1", "Unknown2") == []


# --- shortest_path: BFS (unweighted, weight_key=None) ---

def test_bfs_shortest_path_direct_edge(traversal):
    assert traversal.shortest_path("Alice", "GraphDB Paper") == ["Alice", "GraphDB Paper"]


def test_bfs_shortest_path_prefers_fewer_hops(traversal):
    # direct Alice->ML Paper (1 hop) beats Alice->GraphDB Paper->ML Paper (2 hops)
    assert traversal.shortest_path("Alice", "ML Paper") == ["Alice", "ML Paper"]


def test_bfs_shortest_path_no_outgoing_edges(traversal):
    # ML Paper has no outgoing edges -> no path back to Alice
    assert traversal.shortest_path("ML Paper", "Alice") == []


def test_bfs_shortest_path_disconnected_nodes(traversal):
    # Bob and GraphDB Paper are not connected in either direction
    assert traversal.shortest_path("Bob", "GraphDB Paper") == []


def test_bfs_shortest_path_ignores_weight(weighted_traversal):
    # fewest-hops path (a->c->d) even though it costs more than a->b->c->d
    assert weighted_traversal.shortest_path("a", "d") == ["a", "c", "d"]


# --- shortest_path: Dijkstra (weighted, weight_key set) ---

def test_dijkstra_prefers_lower_cost_over_fewer_hops(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "d", weight_key="weight") == ["a", "b", "c", "d"]


def test_dijkstra_direct_edge(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "b", weight_key="weight") == ["a", "b"]


def test_dijkstra_no_path_isolated_node(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "isolated", weight_key="weight") == []


def test_dijkstra_missing_weight_prop_defaults_to_one(weighted_traversal):
    # new direct edge a->d has no "weight" prop -> should default to cost 1,
    # beating the existing a->b->c->d path (cost 4)
    weighted_traversal.index.add_edge(Edge("a", "d", "shortcut", {}))
    assert weighted_traversal.shortest_path("a", "d", weight_key="weight") == ["a", "d"]


def test_dijkstra_unknown_weight_key_defaults_to_one_for_all_edges(weighted_traversal):
    # weight_key that no edge has -> every edge costs 1 -> behaves like hop count
    assert weighted_traversal.shortest_path("a", "d", weight_key="nonexistent") == ["a", "c", "d"]


def test_dijkstra_negative_weight_raises(weighted_traversal):
    # merges into existing a->b edge, overriding weight to -5
    weighted_traversal.index.add_edge(Edge("a", "b", "neg", {"weight": -5}))
    with pytest.raises(ValueError):
        weighted_traversal.shortest_path("a", "b", weight_key="weight")


def test_dijkstra_same_node_short_circuits_before_touching_weights(weighted_traversal):
    # should return immediately without needing any edge/weight lookup
    assert weighted_traversal.shortest_path("a", "a", weight_key="weight") == ["a"]


# --- bfs(): relation_type call-site fix ---

def test_bfs_relation_type_filters_correctly(populated_indexing):
    traversal = GraphTraversal(populated_indexing)
    result = traversal.bfs("Alice", relation_type="authored")
    visited_nodes = {node for node, _ in result}
    assert visited_nodes == {"Alice", "GraphDB Paper", "ML Paper"}


def test_bfs_relation_type_no_match_only_visits_start(populated_indexing):
    traversal = GraphTraversal(populated_indexing)
    result = traversal.bfs("Bob", relation_type="cites")
    assert result == [("Bob", 0)]
