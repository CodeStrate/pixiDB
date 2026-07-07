import numpy as np
import pytest
from src.storage.store import CSR


SIMPLE_EDGES = [
    (0, 1, {}),
    (0, 2, {}),
    (1, 3, {}),
    (2, 1, {}),
    (3, 0, {}),
]


@pytest.fixture
def simple_csr():
    csr = CSR()
    csr._build_csr(SIMPLE_EDGES, num_nodes=4)
    return csr


def test_build_csr_indptr(simple_csr):
    np.testing.assert_array_equal(simple_csr.indptr, [0, 2, 3, 4, 5])


def test_build_csr_indices(simple_csr):
    np.testing.assert_array_equal(simple_csr.indices, [1, 2, 3, 1, 0])


def test_build_csr_edge_props(simple_csr):
    assert len(simple_csr.edge_props) == 5
    assert simple_csr.edge_props[0] == {}   # first edge (0→1) has empty props
    assert simple_csr.edge_props[4] == {}   # last edge (3→0) has empty props


def test_build_csr_edge_props_with_values():
    edges = [(0, 1, {"weight": 1.0}), (0, 2, {"weight": 2.0}), (1, 0, {"weight": 0.5})]
    csr = CSR()
    csr._build_csr(edges, num_nodes=3)
    assert csr.edge_props[0] == {"weight": 1.0}
    assert csr.edge_props[1] == {"weight": 2.0}
    assert csr.edge_props[2] == {"weight": 0.5}


def test_csr_from_arrays():
    indices = [1, 2, 3, 1, 0]
    indptr = [0, 2, 3, 4, 5]
    edge_props = [{}, {}, {}, {}, {}]
    csr = CSR.csr_from_arrays(indices, indptr, edge_props)
    np.testing.assert_array_equal(csr.indices, indices)
    np.testing.assert_array_equal(csr.indptr, indptr)
    assert len(csr.edge_props) == 5


def test_build_csr_unsorted_input():
    unsorted = [
        (3, 0, {}),
        (0, 2, {}),
        (1, 3, {}),
        (2, 1, {}),
        (0, 1, {}),
    ]
    csr = CSR()
    csr._build_csr(unsorted, num_nodes=4)
    np.testing.assert_array_equal(csr.indptr, [0, 2, 3, 4, 5])
    np.testing.assert_array_equal(csr.indices, [2, 1, 3, 1, 0])


def test_build_csr_single_edge():
    csr = CSR()
    csr._build_csr([(0, 1, {})], num_nodes=2)
    np.testing.assert_array_equal(csr.indptr, [0, 1, 1])
    np.testing.assert_array_equal(csr.indices, [1])


def test_build_csr_empty_edges():
    csr = CSR()
    csr._build_csr([], num_nodes=3)
    np.testing.assert_array_equal(csr.indptr, [0, 0, 0, 0])
    assert len(csr.indices) == 0


def test_csr_initializes_none():
    csr = CSR()
    assert csr.indices is None
    assert csr.indptr is None
    assert csr.edge_props is None
