from pydantic import BaseModel, Field, model_validator
from uuid import UUID , uuid5, uuid4
from src.utils.namespace import get_ns_uuid

class Node(BaseModel):
    id: UUID = Field(default_factory=uuid4) # random
    name: str
    label: str 
    props: dict = Field(default_factory=dict)


class Edge(BaseModel):
    id: UUID | None = None # random but deterministic, for serialization cycles and deduplication
    src_id: UUID
    dst_id: UUID
    relation_type: str
    props: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _set_id(self):
        pixidb_ns = get_ns_uuid()
        if self.id is None:
            self.id = uuid5(pixidb_ns, f"{self.src_id}:{self.relation_type}:{self.dst_id}")
        return self

EdgeKey = tuple[UUID, str, UUID] # src , rel type , dst