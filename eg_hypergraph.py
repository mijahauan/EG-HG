"""
eg_hypergraph.py

This module defines the core data structures for representing Existential Graphs (EGs)
as a property hypergraph. This model serves as a robust, central representation
for translation to and from other logical syntaxes like CLIF and CGIF.

The property hypergraph is a powerful data structure for this purpose because it
naturally models the key features of Existential Graphs:

1.  **Nested Contexts**: A 'Cut' in an EG, which represents negation, is modeled
    as a hyperedge that contains its own subgraph of nodes and other hyperedges.
    This allows for an elegant representation of arbitrarily deep nesting.

2.  **N-ary Relations**: A 'Predicate' is a hyperedge that connects a relation
    symbol with an arbitrary number of arguments (which are nodes). This directly
    models predicates of any arity.

3.  **Lines of Identity**: A 'Line of Identity' in an EG, which represents a
    variable or co-reference, is modeled as a single `Node` in the hypergraph.
    The "line" itself is formed by the participation of this same node in
    multiple predicate hyperedges, perfectly capturing its logical role.

4.  **Functions and Constants**: Following extensions to EGs (e.g., by Dau),
    constants and functional terms are also represented as nodes, with a clear
    distinction in their `node_type`.
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
        """
        Initializes a Node.

        Args:
            node_type (str): The type of the node (e.g., 'variable', 'constant').
            props (Optional[Properties]): A dictionary of key-value properties,
                such as a 'name' for a variable or constant.
            node_id (Optional[NodeId]): A specific UUID for the node. If None,
                a new one is generated automatically.
        """
        self.id: NodeId = node_id or uuid.uuid4()
        self.type: str = node_type
        self.properties: Properties = props or {}

    def __repr__(self) -> str:
        """Provides a concise string representation of the node."""
        return f"Node(id={str(self.id)[-4:]}, type='{self.type}', props={self.properties})"

class Hyperedge:
    """
    Represents a hyperedge in the hypergraph. In the context of EGs, this can be
    a predicate, a function, or a cut (negation).
    """
    def __init__(self, edge_type: str, nodes: List[NodeId], props: Optional[Properties] = None, edge_id: Optional[EdgeId] = None):
        """
        Initializes a Hyperedge.

        Args:
            edge_type (str): The type of the edge (e.g., 'predicate', 'cut', 'function').
            nodes (List[NodeId]): An ORDERED list of Node IDs that this edge connects.
                Order is critical for representing arguments to predicates and functions.
            props (Optional[Properties]): A dictionary of key-value properties.
            edge_id (Optional[EdgeId]): A specific UUID for the edge. If None,
                a new one is generated automatically.
        """
        self.id: EdgeId = edge_id or uuid.uuid4()
        self.type: str = edge_type
        self.nodes: List[NodeId] = nodes
        self.properties: Properties = props or {}
        # For 'cut' hyperedges, this stores an ordered list of the IDs of the
        # nodes and edges contained within the cut.
        self.contained_items: List[uuid.UUID] = []

    def __repr__(self) -> str:
        """Provides a concise string representation of the hyperedge."""
        node_ids_short = [str(n)[-4:] for n in self.nodes]
        return f"Hyperedge(id={str(self.id)[-4:]}, type='{self.type}', nodes={node_ids_short}, props={self.properties})"

class EGHg:
    """
    The main container for the Existential Graph Hypergraph (EGHg). This class
    manages the entire collection of nodes and hyperedges, as well as the
    containment relationships that define the graph's nested structure.
    """
    def __init__(self):
        """Initializes an empty hypergraph."""
        self.nodes: Dict[NodeId, Node] = {}
        self.edges: Dict[EdgeId, Hyperedge] = {}
        # The containment map tracks which cut (if any) each item belongs to.
        # An item with a container_id of None is on the Sheet of Assertion.
        self.containment: Dict[uuid.UUID, Optional[EdgeId]] = {}

    def add_node(self, node: Node, container: Optional[Hyperedge] = None) -> Node:
        """
        Adds a node to the graph and registers its container.

        Args:
            node (Node): The node object to add.
            container (Optional[Hyperedge]): The 'cut' hyperedge that contains
                this node. If None, the node is placed on the Sheet of Assertion.

        Returns:
            Node: The node that was added.
        """
        if node.id in self.nodes: raise ValueError(f"Node with ID {node.id} already exists.")
        self.nodes[node.id] = node
        container_id = container.id if container else None
        if container_id:
            if container_id not in self.edges: raise ValueError(f"Container edge {container_id} does not exist.")
            self.edges[container_id].contained_items.append(node.id)
        self.containment[node.id] = container_id
        return node

    def add_edge(self, edge: Hyperedge, container: Optional[Hyperedge] = None) -> Hyperedge:
        """
        Adds a hyperedge to the graph and registers its container.

        Args:
            edge (Hyperedge): The hyperedge object to add.
            container (Optional[Hyperedge]): The 'cut' hyperedge that contains
                this edge. If None, the edge is placed on the Sheet of Assertion.

        Returns:
            Hyperedge: The hyperedge that was added.
        """
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

        Args:
            container_id (Optional[EdgeId]): The ID of the 'cut' hyperedge to
                inspect. If None, returns items on the Sheet of Assertion.

        Returns:
            List[uuid.UUID]: An ordered list of the contained item IDs.
        """
        if container_id:
            if container_id not in self.edges: raise ValueError(f"Container edge {container_id} does not exist.")
            return self.edges[container_id].contained_items
        else:
            # Return top-level items (those not contained in any edge).
            return [item_id for item_id, c_id in self.containment.items() if c_id is None]

    def get_context_depth(self, item_id: uuid.UUID) -> int:
        """
        Calculates the nesting depth of an item (how many cuts it is inside).
        The Sheet of Assertion is at depth 0.

        Args:
            item_id (uuid.UUID): The ID of the node or edge.

        Returns:
            int: The nesting depth of the item.
        """
        if item_id not in self.containment:
            raise ValueError(f"Item {item_id} not found in graph.")
        
        depth = 0
        current_container_id = self.containment[item_id]
        while current_container_id is not None:
            depth += 1
            # Move up to the next container
            current_container_id = self.containment.get(current_container_id)
        return depth

    def __repr__(self) -> str:
        """Provides a concise string representation of the entire graph."""
        return f"EGHg(nodes={len(self.nodes)}, edges={len(self.edges)})"
