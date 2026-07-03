import pytest
from src.storage.schemas import Edge, Node
from src.storage.csr_store import CSRBuffer


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
    buf.add_node(alice)
    buf.add_node(bob)
    buf.add_node(graphdb_paper)
    buf.add_node(ml_paper)
    buf.add_edge(edge_alice_graphdb)
    buf.add_edge(edge_alice_ml)
    buf.add_edge(edge_bob_ml)  # triggers compact at threshold=3
    assert buf.pendingCount == 0
    assert buf.csr.indices is not None


def test_add_edge_unknown_src_raises(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf.add_node(alice)
    # graphdb_paper not added to hash
    edge = Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored")
    with pytest.raises(KeyError):
        buf.add_edge(edge)


def test_duplicate_edge_merges_props(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf.add_node(alice)
    buf.add_node(graphdb_paper)

    buf.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                      relation_type="authored", props={"weight": 1}))
    buf.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper",
                      relation_type="authored", props={"weight": 2, "note": "updated"}))

    alice_idx = buf.hash.node_to_idx["Alice"]
    entries = buf.pendingBuffer[alice_idx]

    assert len(entries) == 1
    _, merged_props = entries[0]
    assert merged_props == {"weight": 2, "note": "updated"}


def test_duplicate_edge_does_not_increment_count(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf.add_node(alice)
    buf.add_node(graphdb_paper)

    buf.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored"))
    buf.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored"))

    assert buf.pendingCount == 1
