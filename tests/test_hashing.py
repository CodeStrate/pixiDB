import pytest
from src.storage.schemas import Node
from src.storage.csr_store import CSRHash, CSR, CSRBuffer


def test_add_node_assigns_sequential_idx(alice, bob):
    h = CSRHash()
    h._add_node_hash(alice)
    h._add_node_hash(bob)
    assert h.node_to_idx["Alice"] == 0
    assert h.node_to_idx["Bob"] == 1


def test_add_node_reverse_lookup(alice):
    h = CSRHash()
    h._add_node_hash(alice)
    assert h.idx_to_node[0] == "Alice"


def test_add_node_stores_props(alice):
    h = CSRHash()
    h._add_node_hash(alice)
    assert h.node_props[0] == {"role": "author"}


def test_add_duplicate_node_raises(alice):
    h = CSRHash()
    h._add_node_hash(alice)
    with pytest.raises(ValueError):
        h._add_node_hash(alice)


def test_neighbors_returns_correct_names(populated_hash):
    csr = CSR()
    buf = CSRBuffer(threshold=1000)
    # Alice=0→GraphDB Paper=2, Alice=0→ML Paper=3
    csr._build_csr([(0, 2, {}), (0, 3, {}), (1, 3, {}), (2, 3, {})], num_nodes=4)
    result = populated_hash._neighbors("Alice", csr, buf)
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_neighbors_unknown_node_raises(populated_hash):
    csr = CSR()
    buf = CSRBuffer(threshold=1000)
    csr._build_csr([], num_nodes=4)
    with pytest.raises(KeyError):
        populated_hash._neighbors("Unknown", csr, buf)


def test_neighbors_no_outgoing_edges(populated_hash):
    csr = CSR()
    buf = CSRBuffer(threshold=1000)
    # ML Paper (idx=3) has no outgoing edges
    csr._build_csr([(0, 2, {}), (0, 3, {}), (1, 3, {}), (2, 3, {})], num_nodes=4)
    result = populated_hash._neighbors("ML Paper", csr, buf)
    assert result == []


def test_neighbors_csr_none_returns_only_buf_neighbors(populated_hash,
                                                        edge_alice_graphdb,
                                                        edge_alice_ml):
    # CSR never built — all edges live in buffer only
    buf = CSRBuffer(threshold=1000)
    for node in [populated_hash.idx_to_node[i] for i in range(4)]:
        pass  # nodes already in populated_hash, buf has its own hash
    buf.hash = populated_hash  # share the hash so node_to_idx is populated
    buf.add_edge(edge_alice_graphdb)
    buf.add_edge(edge_alice_ml)
    csr = CSR()  # indices and indptr are None
    result = populated_hash._neighbors("Alice", csr, buf)
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_neighbors_merges_csr_and_buf(populated_hash,
                                       edge_bob_ml,
                                       edge_alice_graphdb,
                                       edge_alice_ml):
    # Alice→GraphDB in CSR, Bob→ML in buffer
    csr = CSR()
    csr._build_csr([(0, 2, {})], num_nodes=4)  # Alice→GraphDB Paper only
    buf = CSRBuffer(threshold=1000)
    buf.hash = populated_hash
    buf.add_edge(edge_alice_ml)  # Alice→ML Paper in buffer
    result = populated_hash._neighbors("Alice", csr, buf)
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_neighbors_after_compact_returns_all(populated_buffer):
    populated_buffer._compact()
    result = populated_buffer.hash._neighbors("Alice", populated_buffer.csr, populated_buffer)
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_neighbors_buf_only_no_csr_edges_for_node(populated_hash, edge_bob_ml):
    # Bob has no CSR edges, only a buffer edge
    csr = CSR()
    csr._build_csr([(0, 2, {})], num_nodes=4)  # only Alice→GraphDB in CSR
    buf = CSRBuffer(threshold=1000)
    buf.hash = populated_hash
    buf.add_edge(edge_bob_ml)
    result = populated_hash._neighbors("Bob", csr, buf)
    assert set(result) == {"ML Paper"}
