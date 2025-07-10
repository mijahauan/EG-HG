"""
eg_transformations.py

This module provides a class for applying Peirce's transformation rules
(Alpha and Beta) to an Existential Graph represented by the EGHg model.
"""

import uuid
from typing import List, Optional, Dict, Set

from eg_hypergraph import EGHg, Hyperedge, Node, NodeId, EdgeId

class EGTransformation:
    """
    A controller class that applies transformation rules to an EGHg object.
    """
    def __init__(self, hg: EGHg):
        self.hg = hg

    def _validate_subgraph(self, item_ids: List[uuid.UUID]) -> Optional[EdgeId]:
        """
        Validates that a list of item IDs constitutes a proper subgraph within
        a single context.
        """
        if not item_ids:
            raise ValueError("Item list cannot be empty for this operation.")
        first_item_id = item_ids[0]
        if first_item_id not in self.hg.containment:
            raise ValueError(f"Item {first_item_id} not found in the graph.")
        container_id = self.hg.containment[first_item_id]
        for item_id in item_ids[1:]:
            if self.hg.containment.get(item_id) != container_id:
                raise ValueError("All items must be in the same container.")
        return container_id

    def _get_canonical_signature(self, item_ids: List[uuid.UUID]) -> str:
        """
        Generates a canonical, sorted string signature for a subgraph.
        This signature represents the structure and connections of the subgraph,
        allowing for isomorphism checks.
        """
        subgraph_nodes = {i for i in item_ids if i in self.hg.nodes}
        subgraph_edges = [i for i in item_ids if i in self.hg.edges]

        edge_signatures = []
        for edge_id in subgraph_edges:
            edge = self.hg.edges[edge_id]
            # For each node connected to the edge, represent it as either
            # 'internal' (if part of the subgraph) or by its external ID.
            node_reprs = []
            for node_id in edge.nodes:
                if node_id in subgraph_nodes:
                    node_reprs.append(f"internal_{self.hg.nodes[node_id].properties.get('name', 'unnamed')}")
                else:
                    node_reprs.append(f"external_{node_id}")
            
            edge_signatures.append(
                f"{edge.properties.get('name', edge.type)}:{','.join(sorted(node_reprs))}"
            )
        
        return ";".join(sorted(edge_signatures))

    def add_double_cut(self, item_ids: List[uuid.UUID], container_id: Optional[EdgeId] = None):
        """Alpha Rule: Inserts a double cut."""
        if item_ids:
            inferred_container_id = self._validate_subgraph(item_ids)
            if container_id is not None and container_id != inferred_container_id:
                raise ValueError("Provided container_id does not match the container of the items.")
            container_id = inferred_container_id
        
        container = self.hg.edges.get(container_id) if container_id else None
        if container_id and not container:
             raise ValueError(f"Target container with ID {container_id} does not exist.")

        outer_cut = self.hg.add_edge(Hyperedge(edge_type='cut', nodes=[]), container)
        inner_cut = self.hg.add_edge(Hyperedge(edge_type='cut', nodes=[]), container=outer_cut)

        if item_ids:
            original_container_list = self.hg.edges[container_id].contained_items if container_id else None
            for item_id in list(item_ids):
                if original_container_list is not None:
                    if item_id in original_container_list:
                         original_container_list.remove(item_id)
                self.hg.containment[item_id] = inner_cut.id
                inner_cut.contained_items.append(item_id)
                
    def remove_double_cut(self, outer_cut_id: EdgeId):
        """Alpha Rule: Removes a double cut."""
        outer_cut = self.hg.edges.get(outer_cut_id)
        if not outer_cut or outer_cut.type != 'cut':
            raise ValueError(f"Item {outer_cut_id} is not a valid cut.")
        if len(outer_cut.contained_items) != 1:
            raise ValueError("Invalid double cut: Outer cut is not empty besides the inner cut.")
        inner_cut_id = outer_cut.contained_items[0]
        inner_cut = self.hg.edges.get(inner_cut_id)
        if not inner_cut or inner_cut.type != 'cut':
            raise ValueError("Invalid double cut: Item inside outer cut is not a cut itself.")

        parent_container_id = self.hg.containment.get(outer_cut_id)
        parent_container = self.hg.edges.get(parent_container_id) if parent_container_id else None
        items_to_promote = list(inner_cut.contained_items)

        if parent_container:
            parent_container.contained_items.remove(outer_cut_id)
        
        for item_id in items_to_promote:
            self.hg.containment[item_id] = parent_container_id
            if parent_container:
                parent_container.contained_items.append(item_id)

        del self.hg.containment[outer_cut_id]
        del self.hg.containment[inner_cut_id]
        del self.hg.edges[outer_cut_id]
        del self.hg.edges[inner_cut_id]

    def erase(self, item_ids: List[uuid.UUID]):
        """Beta Rule: Erases a subgraph from a positive context."""
        if not item_ids: return
        self._validate_subgraph(item_ids)
        depth = self.hg.get_context_depth(item_ids[0])
        if depth % 2 != 0:
            raise ValueError(f"Erasure is not permitted in a negative context (depth {depth}).")
        for item_id in item_ids:
            self._erase_recursive(item_id)

    def _erase_recursive(self, item_id: uuid.UUID):
        """Helper to recursively erase an item and its contents."""
        item = self.hg.nodes.get(item_id) or self.hg.edges.get(item_id)
        if not item: return

        if isinstance(item, Hyperedge) and item.type == 'cut':
            for contained_id in list(item.contained_items):
                self._erase_recursive(contained_id)

        container_id = self.hg.containment.get(item_id)
        if container_id and self.hg.edges.get(container_id):
            if item_id in self.hg.edges[container_id].contained_items:
                self.hg.edges[container_id].contained_items.remove(item_id)

        if item_id in self.hg.nodes: del self.hg.nodes[item_id]
        elif item_id in self.hg.edges: del self.hg.edges[item_id]
        if item_id in self.hg.containment: del self.hg.containment[item_id]

    def insert(self, subgraph: EGHg, target_container_id: Optional[EdgeId]):
        """Beta Rule: Inserts (copies) a subgraph into a negative context."""
        if target_container_id is None:
             raise ValueError("Insertion is only permitted in negative contexts (i.e., inside a cut).")
        
        depth = self.hg.get_context_depth(target_container_id) + 1
        if depth % 2 == 0:
            raise ValueError(f"Insertion is not permitted in a positive context (depth {depth}).")

        target_container = self.hg.edges.get(target_container_id)
        if not target_container or target_container.type != 'cut':
            raise ValueError("Target container for insertion must be a cut.")

        self._copy_recursive(subgraph, None, target_container)

    def iterate(self, item_ids: List[uuid.UUID], target_container_id: Optional[EdgeId]):
        """Beta Rule: Copies a subgraph into the same or a deeper context."""
        source_container_id = self._validate_subgraph(item_ids)
        if not self.hg.is_ancestor(source_container_id, target_container_id):
            raise ValueError("Iteration is only permitted into the same or a deeper context.")

        target_container = self.hg.edges.get(target_container_id)
        if target_container_id and not target_container:
            raise ValueError(f"Target container {target_container_id} does not exist.")

        id_map = {}
        nodes_in_subgraph = {item_id for item_id in item_ids if item_id in self.hg.nodes}
        edges_in_subgraph = [item_id for item_id in item_ids if item_id in self.hg.edges]

        for node_id in nodes_in_subgraph:
            source_node = self.hg.nodes[node_id]
            new_node = Node(source_node.type, source_node.properties.copy())
            self.hg.add_node(new_node, target_container)
            id_map[node_id] = new_node.id

        for edge_id in edges_in_subgraph:
            source_edge = self.hg.edges[edge_id]
            new_node_ids = [id_map.get(n_id, n_id) for n_id in source_edge.nodes]
            new_edge = Hyperedge(source_edge.type, new_node_ids, source_edge.properties.copy())
            self.hg.add_edge(new_edge, target_container)
            id_map[edge_id] = new_edge.id

            if new_edge.type == 'cut':
                temp_subgraph = EGHg()
                for item in source_edge.contained_items:
                    if item in self.hg.nodes:
                        temp_subgraph.add_node(Node(self.hg.nodes[item].type, self.hg.nodes[item].properties.copy(), node_id=item))
                    elif item in self.hg.edges:
                        temp_subgraph.add_edge(Hyperedge(self.hg.edges[item].type, self.hg.edges[item].nodes, self.hg.edges[item].properties.copy(), edge_id=item))
                self._copy_recursive(temp_subgraph, None, new_edge, id_map)

    def deiterate(self, item_ids: List[uuid.UUID]):
        """
        Beta Rule: Removes a subgraph that is a redundant copy of a graph
        in an enclosing context.
        """
        if not item_ids: return
        container_id = self._validate_subgraph(item_ids)
        
        # Generate the signature of the graph to be de-iterated.
        target_signature = self._get_canonical_signature(item_ids)

        # Walk up the ancestor contexts to find a match.
        current_container_id = container_id
        match_found = False
        while not match_found:
            # Move to the parent context.
            if current_container_id is None: break # Reached the SA, no more ancestors
            current_container_id = self.hg.containment.get(current_container_id)

            # Check all items in the ancestor context for a match.
            ancestor_items = self.hg.get_items_in_context(current_container_id)
            for potential_match_id in ancestor_items:
                # A simple check: if it's a predicate, does the name match?
                # This is a heuristic to avoid checking every single item.
                if potential_match_id in self.hg.edges:
                    potential_match_sig = self._get_canonical_signature([potential_match_id])
                    if potential_match_sig == target_signature:
                        match_found = True
                        break
            if match_found: break
        
        if not match_found:
            raise ValueError("De-iteration is not valid: no identical graph found in an enclosing context.")
            
        # If a match was found, the de-iteration is valid, so we can erase.
        for item_id in item_ids:
            self._erase_recursive(item_id)

    def _copy_recursive(self, source_graph: EGHg, source_container_id: Optional[EdgeId], target_container: Optional[Hyperedge], id_map: Optional[Dict[uuid.UUID, uuid.UUID]] = None):
        """
        Recursively copies the contents of a source container into a target container.
        """
        if id_map is None: id_map = {}
        source_items = source_graph.get_items_in_context(source_container_id)

        for item_id in source_items:
            if item_id in source_graph.nodes and source_graph.containment.get(item_id) == source_container_id:
                source_node = source_graph.nodes[item_id]
                if item_id not in id_map:
                    new_node = Node(source_node.type, source_node.properties.copy())
                    self.hg.add_node(new_node, target_container)
                    id_map[item_id] = new_node.id
            elif item_id in source_graph.edges:
                source_edge = source_graph.edges[item_id]
                new_node_ids = [id_map.get(n_id, n_id) for n_id in source_edge.nodes]
                new_edge = Hyperedge(source_edge.type, new_node_ids, source_edge.properties.copy())
                self.hg.add_edge(new_edge, target_container)
                id_map[item_id] = new_edge.id
                if new_edge.type == 'cut':
                    self._copy_recursive(source_graph, item_id, new_edge, id_map)
