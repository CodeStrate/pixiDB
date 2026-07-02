import pytest
from src.storage.schemas import Edge
from src.storage.csr_store import CSRBuffer


def test_add_edge_appears_in_buffer(populated_buffer):
    # Alice=0, GraphDB Paper=2 — first edge added
    assert (2, {}) in populated_buffer.pendingBuffer[0]


def test_add_edge_increments_count(populated_buffer):
    assert populated_buffer.pendingCount == 4


def test_compact_clears_buffer(populated_buffer):
    populated_buffer.compact()
    assert len(populated_buffer.pendingBuffer) == 0
    assert populated_buffer.pendingCount == 0


def test_compact_builds_csr(populated_buffer):
    populated_buffer.compact()
    # 4 edges total, CSR should be populated
    assert populated_buffer.csr.indices is not None
    assert len(populated_buffer.csr.indices) == 4


def test_compact_triggers_at_threshold(alice, bob, graphdb_paper, ml_paper,
                                       edge_alice_graphdb, edge_alice_ml,
                                       edge_bob_ml, edge_graphdb_ml):
    buf = CSRBuffer(threshold=3)
    buf.hash.add_node_hash(alice)
    buf.hash.add_node_hash(bob)
    buf.hash.add_node_hash(graphdb_paper)
    buf.hash.add_node_hash(ml_paper)
    buf.add_edge_to_buffer(edge_alice_graphdb)
    buf.add_edge_to_buffer(edge_alice_ml)
    buf.add_edge_to_buffer(edge_bob_ml)  # triggers compact at threshold=3
    assert buf.pendingCount == 0
    assert buf.csr.indices is not None


def test_add_edge_unknown_src_raises(alice, graphdb_paper):
    buf = CSRBuffer(threshold=100)
    buf.hash.add_node_hash(alice)
    # graphdb_paper not added to hash
    edge = Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored")
    with pytest.raises(KeyError):
        buf.add_edge_to_buffer(edge)
