import pytest
from src.storage.schemas import Edge, Node
from src.storage.store import CSRBuffer
from src.storage.index import GraphIndex


def test_add_edge_appears_in_buffer(populated_buffer):
    # Alice=0, GraphDB Paper=2 — first edge added
    assert (2, {}) in populated_buffer.pendingBuffer[0]


def test_add_edge_increments_count(populated_buffer):
    assert populated_buffer.pendingCount == 4


def test_compact_clears_buffer(populated_buffer):
    populated_buffer._compact()
    assert len(populated_buffer.pendingBuffer) == 0
    assert populated_buffer.pendingCount == 0


def test_compact_builds_csr(populated_buffer):
    populated_buffer._compact()
    assert populated_buffer.csr.indices is not None
    assert len(populated_buffer.csr.indices) == 4


def test_compact_triggers_at_threshold(alice, bob, graphdb_paper, ml_paper,
                                       edge_alice_graphdb, edge_alice_ml,
                                       edge_bob_ml, edge_graphdb_ml):
    buf = CSRBuffer(threshold=3)
    buf._add_node(alice)
    buf._add_node(bob)
    buf._add_node(graphdb_paper)
    buf._add_node(ml_paper)
    for e in [edge_alice_graphdb, edge_alice_ml, edge_bob_ml]:
        buf._add_edge(buf.hash.node_to_idx[e.src_id], buf.hash.node_to_idx[e.dest_id], e.props)
    # third edge triggers compact at threshold=3
    assert buf.pendingCount == 0
    assert buf.csr.indices is not None


def test_add_edge_unknown_node_raises(alice):
    buf = CSRBuffer(threshold=100)
    idx = GraphIndex(buf)
    idx.add_node(alice)
    # GraphDB Paper never added — KeyError on hash lookup
    edge = Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored")
    with pytest.raises(KeyError):
        idx.add_edge(edge)


def test_duplicate_edge_merges_props(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf._add_node(alice)
    buf._add_node(graphdb_paper)

    alice_idx = buf.hash.node_to_idx["Alice"]
    graphdb_idx = buf.hash.node_to_idx["GraphDB Paper"]
    buf._add_edge(alice_idx, graphdb_idx, {"weight": 1})
    buf._add_edge(alice_idx, graphdb_idx, {"weight": 2, "note": "updated"})
    entries = buf.pendingBuffer[alice_idx]

    assert len(entries) == 1
    _, merged_props = entries[0]
    assert merged_props == {"weight": 2, "note": "updated"}


def test_duplicate_edge_does_not_increment_count(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf._add_node(alice)
    buf._add_node(graphdb_paper)

    alice_idx = buf.hash.node_to_idx["Alice"]
    graphdb_idx = buf.hash.node_to_idx["GraphDB Paper"]
    buf._add_edge(alice_idx, graphdb_idx, {})
    buf._add_edge(alice_idx, graphdb_idx, {})
    assert buf.pendingCount == 1
