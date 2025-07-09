"""
eg_hypergraph.py

This module defines the core data structures for representing Existential Graphs (EGs)
as a property hypergraph. This model serves as a robust, central representation
for translation to and from other logical syntaxes like CLIF and CGIF.

A property hypergraph is chosen for its ability to model:
1.  Nested Contexts: A 'Cut' is a hyperedge that contains a subgraph of nodes
    and other hyperedges, naturally representing EG's nested structure.
2.  N-ary Relations: A 'Predicate' is a hyperedge that connects a relation symbol
    with an arbitrary number of arguments (Lines of Identity), which are nodes.
3.  Lines of Identity: A 'Line' is modeled as a node that represents a variable
    or object. Its connections across different predicates are established by
    having that same Line node participate in multiple Predicate hyperedges.
4.  Properties: Both nodes and hyperedges can store arbitrary metadata (properties),
    useful for storing names, types, GUI information, or translation hints.
"""

import uuid
from typing import Dict, Any, Set, List, Optional

# Type aliases for clarity
NodeId = uuid.UUID
EdgeId = uuid.UUID
Properties = Dict[str, Any]

class Node:
    """
    Represents a node in the hypergraph.

    In the context of EGs, a Node can represent:
    - A Line of Identity (a variable).
    - A constant or individual marker.
    - A function symbol (as per Dau's extensions).
    """
    def __init__(self, node_type: str, props: Optional[Properties] = None, node_id: Optional[NodeId] = None):
        """
        Initializes a Node.

        Args:
            node_type (str): The type of the node (e.g., 'variable', 'constant').
            props (Optional[Properties]): A dictionary of key-value properties.
            node_id (Optional[NodeId]): A specific UUID for the node. If None, a new one is generated.
        """
        self.id: NodeId = node_id or uuid.uuid4()
        self.type: str = node_type
        self.properties: Properties = props or {}

    def __repr__(self) -> str:
        return f"Node(id={str(self.id)[-4:]}, type='{self.type}', props={self.properties})"

class Hyperedge:
    """
    Represents a hyperedge in the hypergraph, connecting a set of nodes.

    In the context of EGs, a Hyperedge can represent:
    - A Predicate application, connecting a relation to its arguments (Nodes).
    - A Cut (negation), which contains a set of nodes and other hyperedges.
    """
    def __init__(self, edge_type: str, nodes: Set[NodeId], props: Optional[Properties] = None, edge_id: Optional[EdgeId] = None):
        """
        Initializes a Hyperedge.

        Args:
            edge_type (str): The type of the edge (e.g., 'predicate', 'cut').
            nodes (Set[NodeId]): A set of Node IDs that this edge connects.
            props (Optional[Properties]): A dictionary of key-value properties.
            edge_id (Optional[EdgeId]): A specific UUID for the edge. If None, a new one is generated.
        """
        self.id: EdgeId = edge_id or uuid.uuid4()
        self.type: str = edge_type
        # The set of nodes directly connected by this hyperedge.
        self.nodes: Set[NodeId] = nodes
        self.properties: Properties = props or {}
        # For 'cut' hyperedges, this will store the IDs of items (nodes/edges) inside it.
        self.contained_items: Set[uuid.UUID] = set()

    def __repr__(self) -> str:
        node_ids_short = {str(n)[-4:] for n in self.nodes}
        return f"Hyperedge(id={str(self.id)[-4:]}, type='{self.type}', nodes={node_ids_short}, props={self.properties})"

class EGHg:
    """
    Existential Graph as a Hypergraph (EGHg).

    This class is the main container for the entire graph structure. It manages
    all nodes and hyperedges, and their containment within nested cuts.
    It represents the entire universe of discourse, including the top-level
    Sheet of Assertion (SA).
    """
    def __init__(self):
        self.nodes: Dict[NodeId, Node] = {}
        self.edges: Dict[EdgeId, Hyperedge] = {}
        # Maps an item's ID to the ID of the cut that contains it.
        # The top-level SA is represented by a container_id of None.
        self.containment: Dict[uuid.UUID, Optional[EdgeId]] = {}
        # The top-level Sheet of Assertion is conceptually a Cut, but without the negation.
        # We can represent it with a special, well-known ID or handle it implicitly.
        # For now, items with container_id=None are on the SA.

    def add_node(self, node: Node, container: Optional[Hyperedge] = None) -> Node:
        """Adds a node to the graph and registers its container."""
        if node.id in self.nodes:
            raise ValueError(f"Node with ID {node.id} already exists.")
        self.nodes[node.id] = node
        container_id = container.id if container else None
        if container_id and container_id not in self.edges:
            raise ValueError(f"Container edge with ID {container_id} does not exist.")
        if container_id:
            self.edges[container_id].contained_items.add(node.id)
        self.containment[node.id] = container_id
        return node

    def add_edge(self, edge: Hyperedge, container: Optional[Hyperedge] = None) -> Hyperedge:
        """Adds a hyperedge to the graph and registers its container."""
        if edge.id in self.edges:
            raise ValueError(f"Edge with ID {edge.id} already exists.")
        # Ensure all connected nodes exist
        for node_id in edge.nodes:
            if node_id not in self.nodes:
                raise ValueError(f"Cannot create edge with non-existent node ID {node_id}.")
        self.edges[edge.id] = edge
        container_id = container.id if container else None
        if container_id and container_id not in self.edges:
             raise ValueError(f"Container edge with ID {container_id} does not exist.")
        if container_id:
            self.edges[container_id].contained_items.add(edge.id)
        self.containment[edge.id] = container_id
        return edge

    def get_items_in_context(self, container_id: Optional[EdgeId] = None) -> List[uuid.UUID]:
        """
        Returns a list of all item IDs within a given context (a cut or the SA).
        If container_id is None, returns items on the Sheet of Assertion.
        """
        if container_id and container_id not in self.edges:
            raise ValueError(f"Container edge with ID {container_id} does not exist.")
        
        # This is a simple but inefficient way. A better implementation might cache this.
        return [item_id for item_id, c_id in self.containment.items() if c_id == container_id]

    def __repr__(self) -> str:
        return f"EGHg(nodes={len(self.nodes)}, edges={len(self.edges)})"

# Example Usage:
if __name__ == '__main__':
    # Let's model the graph for "There is a cat that is not black."
    # In EG, this is: (Cat)---(Cut containing (Black))
    # CLIF: (exists (x) (and (Cat x) (not (Black x))))

    # 1. Create the graph container
    eg = EGHg()

    # 2. Define the variable 'x' as a node. It exists on the Sheet of Assertion.
    # This represents the Line of Identity for the cat.
    x_node = Node(node_type='variable', props={'name': 'x'})
    eg.add_node(x_node, container=None) # Add to SA

    # 3. Define the 'Cat' predicate. It's a hyperedge connecting to the 'x' node.
    cat_predicate = Hyperedge(edge_type='predicate', nodes={x_node.id}, props={'name': 'Cat'})
    eg.add_edge(cat_predicate, container=None) # Add to SA

    # 4. Define the 'Cut'. It's a hyperedge that will contain the 'Black' predicate.
    # It doesn't connect to any nodes directly, but it exists on the SA.
    negation_cut = Hyperedge(edge_type='cut', nodes=set())
    eg.add_edge(negation_cut, container=None) # Add to SA

    # 5. Define the 'Black' predicate. It connects to the SAME 'x' node,
    # but it is *contained within* the negation_cut.
    black_predicate = Hyperedge(edge_type='predicate', nodes={x_node.id}, props={'name': 'Black'})
    eg.add_edge(black_predicate, container=negation_cut) # Add INSIDE the cut

    # --- Verification ---
    print("Created EG Hypergraph:")
    print(eg)
    
    sa_items = eg.get_items_in_context(None)
    print(f"\nItems on the Sheet of Assertion ({len(sa_items)}):")
    for item_id in sa_items:
        item = eg.nodes.get(item_id) or eg.edges.get(item_id)
        print(f"- {item}")

    cut_items = eg.get_items_in_context(negation_cut.id)
    print(f"\nItems inside the Cut ({len(cut_items)}):")
    for item_id in cut_items:
        item = eg.nodes.get(item_id) or eg.edges.get(item_id)
        print(f"- {item}")

    # Check containment mapping
    assert eg.containment[x_node.id] is None
    assert eg.containment[cat_predicate.id] is None
    assert eg.containment[negation_cut.id] is None
    assert eg.containment[black_predicate.id] == negation_cut.id
    
    print("\nModel structure verified successfully.")

