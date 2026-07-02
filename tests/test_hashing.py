import pytest
from src.storage.schemas import Node
from src.storage.csr_store import CSRHash, CSR


def test_add_node_assigns_sequential_idx(alice, bob):
    h = CSRHash()
    h.add_node_hash(alice)
    h.add_node_hash(bob)
    assert h.node_to_idx["Alice"] == 0
    assert h.node_to_idx["Bob"] == 1


def test_add_node_reverse_lookup(alice):
    h = CSRHash()
    h.add_node_hash(alice)
    assert h.idx_to_node[0] == "Alice"


def test_add_node_stores_props(alice):
    h = CSRHash()
    h.add_node_hash(alice)
    assert h.node_props[0] == {"role": "author"}


def test_add_duplicate_node_raises(alice):
    h = CSRHash()
    h.add_node_hash(alice)
    with pytest.raises(ValueError):
        h.add_node_hash(alice)


def test_neighbors_returns_correct_names(populated_hash):
    csr = CSR()
    # Alice=0→GraphDB Paper=2, Alice=0→ML Paper=3
    csr.build_csr([(0, 2, {}), (0, 3, {}), (1, 3, {}), (2, 3, {})], num_nodes=4)
    result = populated_hash.neighbors("Alice", csr)
    assert set(result) == {"GraphDB Paper", "ML Paper"}


def test_neighbors_unknown_node_raises(populated_hash):
    csr = CSR()
    csr.build_csr([], num_nodes=4)
    with pytest.raises(KeyError):
        populated_hash.neighbors("Unknown", csr)


def test_neighbors_no_outgoing_edges(populated_hash):
    csr = CSR()
    # ML Paper (idx=3) has no outgoing edges
    csr.build_csr([(0, 2, {}), (0, 3, {}), (1, 3, {}), (2, 3, {})], num_nodes=4)
    result = populated_hash.neighbors("ML Paper", csr)
    assert result == []
