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


def test_add_edge_unknown_node_raises(indexing):
    edge = Edge(src_id="Alice", dest_id="Unknown", relation_type="authored")
    with pytest.raises(KeyError):
        indexing.add_edge(edge)


# --- get_neighbors ---

def test_get_neighbors_returns_correct_names(populated_indexing):
    result = populated_indexing.get_neighbors("Alice")
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_get_neighbors_no_outgoing(populated_indexing):
    result = populated_indexing.get_neighbors("ML Paper")
    assert result == []


def test_get_neighbors_unknown_node_raises(populated_indexing):
    with pytest.raises(KeyError):
        populated_indexing.get_neighbors("Unknown")


# --- get_neighbors_by_relation ---

def test_get_neighbors_by_relation_authored(populated_indexing):
    result = populated_indexing.get_neighbors_by_relation("Alice", "authored")
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_get_neighbors_by_relation_cites(populated_indexing):
    result = populated_indexing.get_neighbors_by_relation("GraphDB Paper", "cites")
    assert result == ["ML Paper"]


def test_get_neighbors_by_relation_no_match(populated_indexing):
    result = populated_indexing.get_neighbors_by_relation("Alice", "cites")
    assert result == []


# --- get_edge_props ---

def test_get_edge_props_from_buffer(indexing):
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"weight": 5}))
    props = indexing.get_edge_props("Alice", "GraphDB Paper")
    assert props == {"weight": 5}


def test_get_edge_props_empty_props(populated_indexing):
    # fixture edges have props={} — should not raise KeyError
    props = populated_indexing.get_edge_props("Alice", "GraphDB Paper")
    assert props == {}


def test_get_edge_props_from_csr_after_compact(indexing):
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"weight": 3}))
    indexing.buf._compact()
    props = indexing.get_edge_props("Alice", "GraphDB Paper")
    assert props == {"weight": 3}


def test_get_edge_props_merges_csr_and_buf(indexing):
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"weight": 1}))
    indexing.buf._compact()
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"label": "core"}))
    props = indexing.get_edge_props("Alice", "GraphDB Paper")
    assert props.get("weight") == 1       # from CSR
    assert props.get("label") == "core"   # from buffer


def test_get_edge_props_not_found_raises(indexing):
    with pytest.raises(KeyError):
        indexing.get_edge_props("Alice", "GraphDB Paper")


def test_get_edge_props_unknown_node_raises(indexing):
    with pytest.raises(KeyError):
        indexing.get_edge_props("Alice", "Unknown")


def test_duplicate_edge_not_duplicated_in_index(indexing):
    edge = Edge(src_id="Alice", dest_id="GraphDB Paper",
                relation_type="authored", props={"weight": 1})
    indexing.add_edge(edge)
    indexing.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                           relation_type="authored", props={"weight": 2}))
    edges = indexing.get_edges_by_relation_type("authored")
    alice_idx = indexing.buf.hash.node_to_idx["Alice"]
    graphdb_idx = indexing.buf.hash.node_to_idx["GraphDB Paper"]
    assert edges.count((alice_idx, graphdb_idx)) == 1
    assert indexing.get_edge_props("Alice", "GraphDB Paper") == {"weight": 2}
