import pytest
from src.storage.schemas import Node, Edge
from src.storage.csr_store import CSRHash, CSRBuffer


# --- Node fixtures ---

@pytest.fixture
def alice():
    return Node(node_id="Alice", label="Person", props={"role": "author"})

@pytest.fixture
def bob():
    return Node(node_id="Bob", label="Person", props={"role": "author"})

@pytest.fixture
def graphdb_paper():
    return Node(node_id="GraphDB Paper", label="Paper", props={"year": 2024})

@pytest.fixture
def ml_paper():
    return Node(node_id="ML Paper", label="Paper", props={"year": 2023})


# --- Edge fixtures ---

@pytest.fixture
def edge_alice_graphdb():
    return Edge(src_id="Alice", dest_id="GraphDB Paper", relation_type="authored")

@pytest.fixture
def edge_alice_ml():
    return Edge(src_id="Alice", dest_id="ML Paper", relation_type="authored")

@pytest.fixture
def edge_bob_ml():
    return Edge(src_id="Bob", dest_id="ML Paper", relation_type="authored")

@pytest.fixture
def edge_graphdb_ml():
    return Edge(src_id="GraphDB Paper", dest_id="ML Paper", relation_type="cites")


# --- Populated hash fixture ---
# Alice=0, Bob=1, GraphDB Paper=2, ML Paper=3

@pytest.fixture
def populated_hash(alice, bob, graphdb_paper, ml_paper):
    h = CSRHash()
    h.add_node_hash(alice)
    h.add_node_hash(bob)
    h.add_node_hash(graphdb_paper)
    h.add_node_hash(ml_paper)
    return h


# --- Populated buffer fixture (threshold high so no auto-compact) ---

@pytest.fixture
def populated_buffer(alice, bob, graphdb_paper, ml_paper,
                     edge_alice_graphdb, edge_alice_ml,
                     edge_bob_ml, edge_graphdb_ml):
    buf = CSRBuffer(threshold=100)
    buf.hash.add_node_hash(alice)
    buf.hash.add_node_hash(bob)
    buf.hash.add_node_hash(graphdb_paper)
    buf.hash.add_node_hash(ml_paper)
    buf.add_edge_to_buffer(edge_alice_graphdb)
    buf.add_edge_to_buffer(edge_alice_ml)
    buf.add_edge_to_buffer(edge_bob_ml)
    buf.add_edge_to_buffer(edge_graphdb_ml)
    return buf
