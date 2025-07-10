"""
eg_hypergraph.py

This module defines the core data structures for representing Existential Graphs (EGs)
as a property hypergraph. This model serves as a robust, central representation
for translation to and from other logical syntaxes like CLIF and CGIF.
"""

import uuid
from typing import Dict, Any, List, Optional

# --- Type Aliases for Clarity ---
NodeId = uuid.UUID
EdgeId = uuid.UUID
Properties = Dict[str, Any]

# --- Core Model Classes ---

class Node:
    """
    Represents a node in the hypergraph. In the context of EGs, a Node can be
    a variable, a constant, or the result of a function.
    """
    def __init__(self, node_type: str, props: Optional[Properties] = None, node_id: Optional[NodeId] = None):
        self.id: NodeId = node_id or uuid.uuid4()
        self.type: str = node_type
        self.properties: Properties = props or {}

    def __repr__(self) -> str:
        return f"Node(id={str(self.id)[-4:]}, type='{self.type}', props={self.properties})"

class Hyperedge:
    """
    Represents a hyperedge in the hypergraph. In the context of EGs, this can be
    a predicate, a function, or a cut (negation).
    """
    def __init__(self, edge_type: str, nodes: List[NodeId], props: Optional[Properties] = None, edge_id: Optional[EdgeId] = None):
        self.id: EdgeId = edge_id or uuid.uuid4()
        self.type: str = edge_type
        self.nodes: List[NodeId] = nodes
        self.properties: Properties = props or {}
        self.contained_items: List[uuid.UUID] = []

    def __repr__(self) -> str:
        node_ids_short = [str(n)[-4:] for n in self.nodes]
        return f"Hyperedge(id={str(self.id)[-4:]}, type='{self.type}', nodes={node_ids_short}, props={self.properties})"

class EGHg:
    """
    The main container for the Existential Graph Hypergraph (EGHg).
    """
    def __init__(self):
        self.nodes: Dict[NodeId, Node] = {}
        self.edges: Dict[EdgeId, Hyperedge] = {}
        self.containment: Dict[uuid.UUID, Optional[EdgeId]] = {}

    def add_node(self, node: Node, container: Optional[Hyperedge] = None) -> Node:
        """Adds a node to the graph and registers its container."""
        if node.id in self.nodes: raise ValueError(f"Node with ID {node.id} already exists.")
        self.nodes[node.id] = node
        container_id = container.id if container else None
        if container_id:
            if container_id not in self.edges: raise ValueError(f"Container edge {container_id} does not exist.")
            self.edges[container_id].contained_items.append(node.id)
        self.containment[node.id] = container_id
        return node

    def add_edge(self, edge: Hyperedge, container: Optional[Hyperedge] = None) -> Hyperedge:
        """Adds a hyperedge to the graph and registers its container."""
        if edge.id in self.edges: raise ValueError(f"Edge with ID {edge.id} already exists.")
        for node_id in edge.nodes:
            if node_id not in self.nodes: raise ValueError(f"Edge connects to non-existent node {node_id}.")
        self.edges[edge.id] = edge
        container_id = container.id if container else None
        if container_id:
            if container_id not in self.edges: raise ValueError(f"Container edge {container_id} does not exist.")
            self.edges[container_id].contained_items.append(edge.id)
        self.containment[edge.id] = container_id
        return edge

    def get_items_in_context(self, container_id: Optional[EdgeId]) -> List[uuid.UUID]:
        """
        Returns an ordered list of all item IDs within a given context.
        """
        if container_id:
            if container_id not in self.edges: raise ValueError(f"Container edge {container_id} does not exist.")
            return self.edges[container_id].contained_items
        else:
            return [item_id for item_id, c_id in self.containment.items() if c_id is None]

    def get_context_depth(self, item_id: uuid.UUID) -> int:
        """
        Calculates the nesting depth of an item (how many cuts it is inside).
        """
        if item_id not in self.containment:
            raise ValueError(f"Item {item_id} not found in graph.")
        depth = 0
        current_container_id = self.containment[item_id]
        while current_container_id is not None:
            depth += 1
            current_container_id = self.containment.get(current_container_id)
        return depth

    def is_ancestor(self, ancestor_id: Optional[EdgeId], descendant_id: Optional[EdgeId]) -> bool:
        """
        Checks if one container is an ancestor of another (i.e., is shallower
        in the same branch of the graph). The Sheet of Assertion (None) is the
        ancestor of all other contexts.
        """
        if ancestor_id == descendant_id:
            return True # A context is an ancestor of itself for iteration purposes
        if ancestor_id is None:
            return True # The SA is an ancestor of everything
        if descendant_id is None:
            return False # Nothing can be an ancestor of the SA

        current = self.containment.get(descendant_id)
        while current is not None:
            if current == ancestor_id:
                return True
            current = self.containment.get(current)
        return False

    def __repr__(self) -> str:
        return f"EGHg(nodes={len(self.nodes)}, edges={len(self.edges)})"
