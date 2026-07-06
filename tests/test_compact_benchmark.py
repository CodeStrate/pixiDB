from src.storage.csr_store import CSRBuffer
from src.storage.schemas import Node

def test_multiple_compact_cycles(alice, bob, graphdb_paper, ml_paper):
    buf = CSRBuffer(threshold=2)
    buf._add_node(alice)
    buf._add_node(bob)
    buf._add_node(graphdb_paper)
    buf._add_node(ml_paper)

    def add(src_id, dst_id):
        buf._add_edge(buf.hash.node_to_idx[src_id], buf.hash.node_to_idx[dst_id], {})

    # first compact triggers at 2 edges
    add("Alice", "GraphDB Paper")
    add("Alice", "ML Paper")

    # second compact
    add("Bob", "ML Paper")
    add("GraphDB Paper", "ML Paper")

    assert len(buf.csr.indices) == 4
    assert buf.pendingCount == 0

def stress_test_buffer_with_many_edges(num_edges: int):
    buf = CSRBuffer(threshold=num_edges+1)
    for i in range(num_edges+1):
        buf._add_node(Node(node_id=str(i), label="Number", props={}))
    for j in range(num_edges):
        buf._add_edge(buf.hash.node_to_idx[str(j)], buf.hash.node_to_idx[str(j+1)], {})

    buf._compact()
    assert len(buf.csr.indices) == num_edges

def test_benchmark_stress(benchmark):
    benchmark(stress_test_buffer_with_many_edges, 10000)

def test_empty_buffer_compact():
    buf = CSRBuffer(threshold=2)
    buf._compact()
    assert buf.csr.indices is None or len(buf.csr.indices) == 0
    assert buf.pendingCount == 0
