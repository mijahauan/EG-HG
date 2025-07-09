"""
hypergraph_to_clif.py

This module provides the translator for converting an EGHg (Existential Graph
as a Hypergraph) model back into a CLIF (Common Logic Interchange Format) string.
This version preserves order and reconstructs forall/if statements.
"""

import uuid
from typing import Dict, Any, List, Optional

from eg_hypergraph import EGHg, Node, Hyperedge, NodeId

class HypergraphToClif:
    """
    Translates an EGHg model object into a CLIF string.
    """
    def __init__(self, hg: EGHg):
        self.hg = hg
        self.node_name_map: Dict[NodeId, str] = {}
        self.name_counter = 0

    def translate(self) -> str:
        return self._visit_context(None)

    def _get_node_name(self, node_id: NodeId) -> str:
        if node_id in self.node_name_map: return self.node_name_map[node_id]
        node = self.hg.nodes[node_id]
        name = node.properties.get('name', f"v{self.name_counter}")
        if 'name' not in node.properties: self.name_counter += 1
        self.node_name_map[node_id] = name
        return name

    def _node_to_clif(self, node_id: NodeId) -> str:
        node = self.hg.nodes[node_id]
        if 'source_function' in node.properties:
            for edge in self.hg.edges.values():
                if edge.type == 'function' and node_id == edge.nodes[0]:
                    function_name = edge.properties['name']
                    arg_nodes = edge.nodes[1:]
                    arg_strings = [self._node_to_clif(arg_id) for arg_id in arg_nodes]
                    return f"({function_name} {' '.join(arg_strings)})"
        return self._get_node_name(node_id)

    def _visit_context(self, container_id: Optional[NodeId]) -> str:
        items_in_context = self.hg.get_items_in_context(container_id)
        
        quantified_vars = [
            self._get_node_name(item_id) for item_id in items_in_context
            if isinstance(self.hg.nodes.get(item_id), Node)
            and self.hg.nodes[item_id].type == 'variable'
            and 'source_function' not in self.hg.nodes[item_id].properties
        ]
        
        content_items = [
            item_id for item_id in items_in_context
            if isinstance(self.hg.edges.get(item_id), Hyperedge)
        ]
        
        clif_parts = [self._visit_item(item_id) for item_id in content_items]
        clif_parts = [part for part in clif_parts if part]

        body = ""
        if len(clif_parts) > 1:
            body = f"(and {' '.join(clif_parts)})"
        elif len(clif_parts) == 1:
            body = clif_parts[0]

        if quantified_vars:
            return f"(exists ({' '.join(quantified_vars)}) {body})"
        return body

    def _visit_item(self, item_id: uuid.UUID) -> str:
        edge = self.hg.edges[item_id]
        construct = edge.properties.get('clif_construct')

        if edge.type == 'cut':
            if construct == 'forall': return self._reconstruct_forall(edge)
            if construct == 'if': return self._reconstruct_if(edge)
            inner_content = self._visit_context(edge.id)
            return f"(not {inner_content})"
        
        if edge.type == 'predicate':
            predicate_name = edge.properties.get('name', 'Predicate')
            if predicate_name == 'equals': predicate_name = '='
            term_strings = [self._node_to_clif(node_id) for node_id in edge.nodes]
            return f"({predicate_name} {' '.join(term_strings)})"
            
        if edge.type == 'function': return ""
        return f"<!-- Unknown edge type: {edge.type} -->"

    def _reconstruct_forall(self, edge: Hyperedge) -> str:
        items_in_outer_cut = self.hg.get_items_in_context(edge.id)
        quantified_vars = [
            self._get_node_name(item_id) for item_id in items_in_outer_cut
            if isinstance(self.hg.nodes.get(item_id), Node) and self.hg.nodes[item_id].type == 'variable'
        ]
        inner_cut_ids = [item_id for item_id in items_in_outer_cut if isinstance(self.hg.edges.get(item_id), Hyperedge) and self.hg.edges[item_id].type == 'cut']
        if not inner_cut_ids: raise ValueError("Malformed 'forall' structure.")
        body = self._visit_context(inner_cut_ids[0])
        return f"(forall ({' '.join(quantified_vars)}) {body})"

    def _reconstruct_if(self, edge: Hyperedge) -> str:
        items_in_context = self.hg.get_items_in_context(edge.id)
        inner_cut_id = None
        p_item_ids = []

        for item_id in items_in_context:
            item = self.hg.edges.get(item_id)
            if item and item.type == 'cut' and not item.properties.get('clif_construct'):
                inner_cut_id = item_id
            else:
                p_item_ids.append(item_id)

        if inner_cut_id is None: raise ValueError("Malformed 'if' structure.")
        q_part = self._visit_context(inner_cut_id)
        
        p_clif_parts = [self._visit_item(item_id) for item_id in p_item_ids]
        p_clif_parts = [p for p in p_clif_parts if p]
        
        p_part = f"(and {' '.join(p_clif_parts)})" if len(p_clif_parts) > 1 else p_clif_parts[0] if p_clif_parts else ""
        return f"(if {p_part} {q_part})"
