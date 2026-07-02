from dataclasses import dataclass, field

@dataclass
class Node:
    node_id: str
    label: str
    props: dict = field(default_factory=dict)

@dataclass
class Edge:
    src_id: str
    dest_id: str
    relation_type: str
    props: dict = field(default_factory=dict)
