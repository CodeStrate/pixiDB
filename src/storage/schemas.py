from dataclasses import dataclass, field

@dataclass
class Node:
    name: str
    # label: str  not in use yet
    props: dict = field(default_factory=dict)

@dataclass
class Edge:
    src_name: str
    dst_name: str
    relation_type: str
    props: dict = field(default_factory=dict)
