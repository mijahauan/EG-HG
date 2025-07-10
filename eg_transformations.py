"""
eg_transformations.py

This module provides a class for applying Peirce's transformation rules
(Alpha and Beta) to an Existential Graph represented by the EGHg model.

Each method corresponds to a rule of inference and includes checks to ensure
the rule is applied validly according to the logical context of the elements.
"""

import uuid
from typing import List, Optional

from eg_hypergraph import EGHg, Hyperedge, Node, NodeId, EdgeId

class EGTransformation:
    """
    A controller class that applies transformation rules to an EGHg object.
    """
    def __init__(self, hg: EGHg):
        """
        Initializes the transformation controller.

        Args:
            hg (EGHg): The hypergraph object to be transformed.
        """
        self.hg = hg

    def add_double_cut(self, item_ids: List[uuid.UUID], container_id: Optional[EdgeId] = None):
        """
        Alpha Rule: Inserts a double cut.

        - If item_ids are provided, it draws the cut around them. All items
          must reside in the same context. If container_id is also provided,
          it is used for validation.
        - If item_ids is empty, it draws an empty double cut in the context
          specified by container_id.

        Args:
            item_ids (List[uuid.UUID]): A list of IDs to enclose.
            container_id (Optional[EdgeId]): The context in which to place the
                new cut. If None, the context is the Sheet of Assertion.
        """
        # --- Validation Step ---
        if item_ids:
            # If items are given, determine their container and validate consistency.
            inferred_container_id = self.hg.containment.get(item_ids[0])
            if container_id is not None and container_id != inferred_container_id:
                raise ValueError("Provided container_id does not match the container of the items.")
            
            # Use the inferred container as the true container.
            container_id = inferred_container_id

            for item_id in item_ids[1:]:
                if self.hg.containment.get(item_id) != container_id:
                    raise ValueError("All items for a double cut must be in the same container.")
        
        container = self.hg.edges.get(container_id) if container_id else None
        if container_id and not container:
             raise ValueError(f"Target container with ID {container_id} does not exist.")

        # 1. Create the outer and inner cuts.
        outer_cut = Hyperedge(edge_type='cut', nodes=[])
        inner_cut = Hyperedge(edge_type='cut', nodes=[])

        # 2. Place the cuts in the graph.
        self.hg.add_edge(outer_cut, container)
        self.hg.add_edge(inner_cut, outer_cut)

        # 3. Move the specified items inside the new inner cut.
        if item_ids:
            # Get the original container's list of items to modify it.
            original_container_list = None
            if container_id:
                original_container_list = self.hg.edges[container_id].contained_items

            for item_id in list(item_ids):
                if original_container_list is not None:
                    original_container_list.remove(item_id)
                else: # Item was on the Sheet of Assertion
                    # We need to update the containment map directly
                    pass
            
                self.hg.containment[item_id] = inner_cut.id
                inner_cut.contained_items.append(item_id)
                
    def remove_double_cut(self, outer_cut_id: EdgeId):
        """
        Alpha Rule: Removes a double cut.

        This is valid only if the outer cut contains nothing but a single
        inner cut. Ligatures passing through the space between the cuts are
        permitted.

        Args:
            outer_cut_id (EdgeId): The ID of the outer cut of the double cut pair.
        """
        # --- Validation Step ---
        outer_cut = self.hg.edges.get(outer_cut_id)
        if not outer_cut or outer_cut.type != 'cut':
            raise ValueError(f"Item {outer_cut_id} is not a valid cut.")

        # The space between the cuts must be empty of any predicates or nodes.
        # It should contain exactly one item: the inner cut.
        contained_items = outer_cut.contained_items
        if len(contained_items) != 1:
            raise ValueError("Invalid double cut: Outer cut is not empty besides the inner cut.")

        inner_cut_id = contained_items[0]
        inner_cut = self.hg.edges.get(inner_cut_id)
        if not inner_cut or inner_cut.type != 'cut':
            raise ValueError("Invalid double cut: Item inside outer cut is not a cut itself.")

        # --- Transformation Step ---
        # Get the container of the outer cut.
        parent_container_id = self.hg.containment.get(outer_cut_id)
        parent_container = self.hg.edges.get(parent_container_id) if parent_container_id else None

        # Items from the inner cut will be "promoted" to the parent container.
        items_to_promote = list(inner_cut.contained_items)

        for item_id in items_to_promote:
            self.hg.containment[item_id] = parent_container_id
            if parent_container:
                parent_container.contained_items.append(item_id)

        # Remove the double cut from the graph.
        if parent_container:
            parent_container.contained_items.remove(outer_cut_id)
        
        del self.hg.edges[outer_cut_id]
        del self.hg.edges[inner_cut_id]
        del self.hg.containment[outer_cut_id]
        del self.hg.containment[inner_cut_id]

