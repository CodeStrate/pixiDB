import pytest
from src.storage.schemas import Node, Edge
from src.storage.csr_store import CSRBuffer
from src.storage.csr_indexing import CSRIndexing


@pytest.fixture
def indexing(alice, bob, graphdb_paper, ml_paper):
    buf = CSRBuffer(threshold=100)
    idx = CSRIndexing(buf)
    idx.add_node(alice)
    idx.add_node(bob)
    idx.add_node(graphdb_paper)
    idx.add_node(ml_paper)
    return idx


@pytest.fixture
def populated_indexing(indexing, edge_alice_graphdb, edge_alice_ml,
                       edge_bob_ml, edge_graphdb_ml):
    indexing.add_edge(edge_alice_graphdb)
    indexing.add_edge(edge_alice_ml)
    indexing.add_edge(edge_bob_ml)
    indexing.add_edge(edge_graphdb_ml)
    return indexing


def test_index_built_on_add_edge(populated_indexing):
    assert "authored" in populated_indexing.secondary_index
    assert "cites" in populated_indexing.secondary_index


def test_authored_edges_correct(populated_indexing):
    # Alice=0, Bob=1, GraphDB Paper=2, ML Paper=3
    edges = populated_indexing.get_edges_by_relation_type("authored")
    assert (0, 2) in edges  # Alice → GraphDB Paper
    assert (0, 3) in edges  # Alice → ML Paper
    assert (1, 3) in edges  # Bob → ML Paper


def test_cites_edges_correct(populated_indexing):
    edges = populated_indexing.get_edges_by_relation_type("cites")
    assert (2, 3) in edges  # GraphDB Paper → ML Paper


def test_unknown_relation_returns_empty(populated_indexing):
    edges = populated_indexing.get_edges_by_relation_type("unknown_relation")
    assert edges == []


def test_edge_also_added_to_buffer(populated_indexing):
    alice_idx = populated_indexing.buf.hash.node_to_idx["Alice"]
    assert len(populated_indexing.buf.pendingBuffer[alice_idx]) == 2


def test_duplicate_edge_not_duplicated_in_index(indexing):
    edge = Edge(src_id="Alice", dest_id="GraphDB Paper",
                relation_type="authored", props={"weight": 1})
    indexing.add_edge(edge)
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"weight": 2}))
    edges = indexing.get_edges_by_relation_type("authored")
    alice_idx = indexing.buf.hash.node_to_idx["Alice"]
    graphdb_idx = indexing.buf.hash.node_to_idx["GraphDB Paper"]
    assert edges.count((alice_idx, graphdb_idx)) == 1  # index — buffer dedupes
