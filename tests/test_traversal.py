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


@pytest.fixture
def weighted_traversal_compacted():
    # same graph as weighted_traversal but all edges flushed to CSR
    buf = CSRBuffer(threshold=100)
    idx = GraphIndex(buf)
    for n in ["a", "b", "c", "d", "isolated"]:
        idx.add_node(Node(n, "label"))
    idx.add_edge(Edge("a", "b", "rel", {"weight": 1}))
    idx.add_edge(Edge("b", "c", "rel", {"weight": 1}))
    idx.add_edge(Edge("c", "d", "rel", {"weight": 2}))
    idx.add_edge(Edge("a", "c", "rel", {"weight": 10}))
    buf._compact()
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


# --- Dijkstra: post-compact (CSR branch of _neighbor_edges) ---

def test_dijkstra_compacted_prefers_lower_cost(weighted_traversal_compacted):
    assert weighted_traversal_compacted.shortest_path("a", "d", weight_key="weight") == ["a", "b", "c", "d"]


def test_dijkstra_compacted_direct_edge(weighted_traversal_compacted):
    assert weighted_traversal_compacted.shortest_path("a", "b", weight_key="weight") == ["a", "b"]


def test_dijkstra_compacted_no_path(weighted_traversal_compacted):
    assert weighted_traversal_compacted.shortest_path("a", "isolated", weight_key="weight") == []


def test_dijkstra_compacted_unknown_weight_key_behaves_like_hop_count(weighted_traversal_compacted):
    assert weighted_traversal_compacted.shortest_path("a", "d", weight_key="nonexistent") == ["a", "c", "d"]


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


# --- bfs(): node_label filtering ---

@pytest.fixture
def label_traversal():
    # Alice (Person) -knows-> Bob (Person) -authored-> GraphDB Paper (Paper) -cites-> ML Paper (Paper)
    # Chain with non-matching intermediaries — tests that traversal goes through them
    buf = CSRBuffer(threshold=100)
    idx = GraphIndex(buf)
    idx.add_node(Node("Alice", "Person"))
    idx.add_node(Node("Bob", "Person"))
    idx.add_node(Node("GraphDB Paper", "Paper"))
    idx.add_node(Node("ML Paper", "Paper"))
    idx.add_edge(Edge("Alice", "Bob", "knows", {}))
    idx.add_edge(Edge("Bob", "GraphDB Paper", "authored", {}))
    idx.add_edge(Edge("GraphDB Paper", "ML Paper", "cites", {}))
    return GraphTraversal(idx)


def test_bfs_node_label_excludes_non_matching(traversal):
    # Alice is Person — should not appear when filtering by "Paper"
    result = traversal.bfs("Alice", node_label="Paper")
    assert all(node != "Alice" for node, _ in result)


def test_bfs_node_label_includes_matching(traversal):
    # Alice -authored-> GraphDB Paper (Paper), ML Paper (Paper)
    result = traversal.bfs("Alice", node_label="Paper")
    nodes = {node for node, _ in result}
    assert nodes == {"GraphDB Paper", "ML Paper"}


def test_bfs_node_label_traverses_through_non_matching(label_traversal):
    # Alice (Person) -> Bob (Person) -> GraphDB Paper (Paper) -> ML Paper (Paper)
    # Bob is Person and doesn't match "Paper" — but BFS must still traverse through
    # him, otherwise Papers are never reached
    result = label_traversal.bfs("Alice", node_label="Paper")
    nodes = {node for node, _ in result}
    assert nodes == {"GraphDB Paper", "ML Paper"}


def test_bfs_node_label_start_matches_included(traversal):
    # Start node matching the label IS included in results
    result = traversal.bfs("GraphDB Paper", node_label="Paper")
    nodes = {node for node, _ in result}
    assert "GraphDB Paper" in nodes
    assert "ML Paper" in nodes


def test_bfs_node_label_no_matching_nodes_reachable(traversal):
    # ML Paper has no outgoing edges — no Person reachable from it
    result = traversal.bfs("ML Paper", node_label="Person")
    assert result == []


def test_bfs_node_label_combined_with_relation_type(traversal):
    # Follow only "authored" edges; report only "Paper" nodes
    result = traversal.bfs("Alice", relation_type="authored", node_label="Paper")
    nodes = {node for node, _ in result}
    assert nodes == {"GraphDB Paper", "ML Paper"}


def test_bfs_node_label_combined_relation_blocks_path_to_label(label_traversal):
    # Alice -knows-> Bob; Bob -authored-> GraphDB Paper (Paper)
    # relation_type="authored": Alice has no authored edges -> only Alice visited -> no Papers reported
    result = label_traversal.bfs("Alice", relation_type="authored", node_label="Paper")
    assert result == []


# --- shortest_path: relation_type filtering ---

def test_bfs_shortest_path_relation_type_finds_path(traversal):
    assert traversal.shortest_path("Alice", "GraphDB Paper", relation_type="authored") == ["Alice", "GraphDB Paper"]


def test_bfs_shortest_path_relation_type_blocks_wrong_relation(traversal):
    # Alice has no "cites" edges — can't reach ML Paper via cites
    assert traversal.shortest_path("Alice", "ML Paper", relation_type="cites") == []


def test_bfs_shortest_path_relation_type_blocks_cross_relation_hop(traversal):
    # GraphDB Paper -cites-> ML Paper, but with relation_type="authored"
    # GraphDB Paper has no "authored" outgoing edges -> no path
    assert traversal.shortest_path("GraphDB Paper", "ML Paper", relation_type="authored") == []


def test_bfs_shortest_path_relation_type_cross_relation_path_unreachable(label_traversal):
    # Only path Alice -> GraphDB Paper requires crossing "knows" then "authored"
    # With relation_type="knows", Alice -knows-> Bob but Bob has no "knows" edges
    assert label_traversal.shortest_path("Alice", "GraphDB Paper", relation_type="knows") == []


def test_dijkstra_relation_type_finds_path(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "d", weight_key="weight", relation_type="rel") == ["a", "b", "c", "d"]


def test_dijkstra_relation_type_no_path_wrong_relation(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "d", weight_key="weight", relation_type="other") == []


def test_dijkstra_relation_type_direct_edge(weighted_traversal):
    assert weighted_traversal.shortest_path("a", "b", weight_key="weight", relation_type="rel") == ["a", "b"]
