from src.storage.csr_store import CSRBuffer
from src.storage.schemas import Edge, Node
import pytest


def test_multiple_compact_cycles(alice, bob, graphdb_paper, ml_paper):
    buf = CSRBuffer(threshold=2)
    buf.add_node(alice)
    buf.add_node(bob)
    buf.add_node(graphdb_paper)
    buf.add_node(ml_paper)

    # first compact triggers at 2 edges
    buf.add_edge(Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored"))
    buf.add_edge(Edge(src_id="Alice", dest_id="ML Paper", relation_type="authored"))

    # second compact
    buf.add_edge(Edge(src_id="Bob", dest_id="ML Paper", relation_type="authored"))
    buf.add_edge(Edge(src_id="GraphDB Paper", dest_id="ML Paper", relation_type="cites"))

    assert len(buf.csr.indices) == 4
    assert buf.pendingCount == 0

def stress_test_buffer_with_many_edges(num_edges: int):
    buf = CSRBuffer(threshold=num_edges+1)
    for i in range(num_edges+1):
        buf.add_node(Node(node_id=str(i), label="Number", props={}))
    for j in range(num_edges):
        buf.add_edge(Edge(src_id=str(j), dest_id=str(j+1), relation_type="consecutive"))

    buf._compact()
    assert len(buf.csr.indices) == num_edges

def test_benchmark_stress(benchmark):
    benchmark(stress_test_buffer_with_many_edges, 10000)

def test_empty_buffer_compact():
    buf = CSRBuffer(threshold=2)
    buf._compact()
    assert buf.csr.indices is None or len(buf.csr.indices) == 0
    assert buf.pendingCount == 0
