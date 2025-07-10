"""
test_transformations.py

This script contains a suite of pytest-based tests for the EGTransformation
controller, verifying that the rules of inference are applied correctly and
that the graph remains in a well-formed state after each transformation.
"""

import pytest
from eg_hypergraph import EGHg, Node, Hyperedge
from eg_transformations import EGTransformation
from hypergraph_to_clif import HypergraphToClif

def _verify_graph_integrity(hg: EGHg):
    """
    Checks the internal consistency of the hypergraph object. This ensures
    that containment relationships are bidirectional and that all items are
    properly accounted for.

    Args:
        hg (EGHg): The hypergraph to verify.
    """
    all_item_ids = set(hg.nodes.keys()) | set(hg.edges.keys())

    # 1. Every item in the graph must have exactly one entry in the containment map.
    assert all_item_ids == set(hg.containment.keys()), \
        "Mismatch between items in the graph and items in the containment map."

    # 2. Check for bidirectional consistency: if A contains B, then B must point to A.
    for item_id, container_id in hg.containment.items():
        if container_id is None:
            # Item is on the Sheet of Assertion. It should not be in any container's list.
            for edge in hg.edges.values():
                assert item_id not in edge.contained_items, \
                    f"Item {item_id} on SA but found in container {edge.id}"
        else:
            # Item is in a container. It must be in that container's `contained_items` list.
            container_edge = hg.edges.get(container_id)
            assert container_edge is not None, \
                f"Item {item_id} points to a non-existent container {container_id}"
            assert item_id in container_edge.contained_items, \
                f"Item {item_id} not found in its container's ({container_id}) list of contained items."

    # 3. Check that every item listed in a container's `contained_items` points back to that container.
    for container_id, container_edge in hg.edges.items():
        if container_edge.type == 'cut':
            for contained_item_id in container_edge.contained_items:
                assert hg.containment.get(contained_item_id) == container_id, \
                    f"Item {contained_item_id} is in container {container_id}'s list but points to {hg.containment.get(contained_item_id)}"


def test_add_double_cut():
    """
    Tests the Alpha Rule for adding a double cut around items.
    It verifies the final structure and the overall integrity of the graph.
    """
    # 1. Setup
    hg = EGHg()
    t = EGTransformation(hg)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    
    # 2. Action
    t.add_double_cut([cat_node.id, cat_predicate.id])

    # 3. Verification
    sa_items = hg.get_items_in_context(None)
    assert len(sa_items) == 1
    outer_cut = hg.edges[sa_items[0]]
    items_in_outer_cut = hg.get_items_in_context(outer_cut.id)
    assert len(items_in_outer_cut) == 1
    inner_cut = hg.edges[items_in_outer_cut[0]]
    items_in_inner_cut = hg.get_items_in_context(inner_cut.id)
    assert set(items_in_inner_cut) == {cat_node.id, cat_predicate.id}
    assert hg.get_context_depth(cat_predicate.id) == 2
    
    # 4. Final Integrity Check
    _verify_graph_integrity(hg)

def test_add_empty_double_cut_in_nested_context():
    """
    Tests adding an empty double cut to a pre-existing negative context.
    """
    # 1. Setup
    hg = EGHg()
    t = EGTransformation(hg)
    existing_cut = hg.add_edge(Hyperedge('cut', nodes=[]))

    # 2. Action
    t.add_double_cut(item_ids=[], container_id=existing_cut.id)

    # 3. Verification
    items_in_existing_cut = hg.get_items_in_context(existing_cut.id)
    assert len(items_in_existing_cut) == 1
    new_outer_cut_id = items_in_existing_cut[0]
    assert hg.edges[new_outer_cut_id].type == 'cut'
    assert hg.get_context_depth(new_outer_cut_id) == 1
    
    # 4. Final Integrity Check
    _verify_graph_integrity(hg)

def test_remove_double_cut():
    """
    Tests the Alpha Rule for removing a double cut.
    """
    # 1. Setup: Create a graph with a double cut around (Cat x)
    hg = EGHg()
    t = EGTransformation(hg)
    
    parent_container = hg.add_edge(Hyperedge('cut', nodes=[]))
    outer_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=parent_container)
    inner_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=outer_cut)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}), container=inner_cut)
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}), container=inner_cut)

    # 2. Action: Remove the double cut.
    t.remove_double_cut(outer_cut.id)
    
    # 3. Verification
    items_in_parent = hg.get_items_in_context(parent_container.id)
    assert len(items_in_parent) == 2
    assert cat_node.id in items_in_parent
    assert cat_predicate.id in items_in_parent
    assert outer_cut.id not in hg.edges
    assert inner_cut.id not in hg.edges
    assert hg.get_context_depth(cat_predicate.id) == 1

    # 4. Final Integrity Check
    _verify_graph_integrity(hg)

def test_double_cut_reversibility():
    """
    Tests that adding and then removing a double cut returns the graph
    to its original state.
    """
    # 1. Setup: Create an initial graph.
    hg = EGHg()
    t = EGTransformation(hg)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    dog_node = hg.add_node(Node('variable', {'name': 'y'}))
    dog_predicate = hg.add_edge(Hyperedge('predicate', [dog_node.id], {'name': 'Dog'}))

    # 2. Capture the original state as a CLIF string.
    original_clif = HypergraphToClif(hg).translate()
    assert original_clif == "(exists (x y) (and (Cat x) (Dog y)))"

    # 3. Action: Add a double cut around (Dog y).
    items_to_enclose = [dog_node.id, dog_predicate.id]
    t.add_double_cut(items_to_enclose)

    # Find the new outer cut to use for the reverse transformation.
    sa_items = hg.get_items_in_context(None)
    outer_cut_id = [i for i in sa_items if hg.edges.get(i) and hg.edges[i].type == 'cut'][0]

    # 4. Action: Remove the double cut we just added.
    t.remove_double_cut(outer_cut_id)

    # 5. Verification: Translate back to CLIF and compare with the original.
    final_clif = HypergraphToClif(hg).translate()
    assert final_clif == original_clif

    # 6. Final Integrity Check
    _verify_graph_integrity(hg)

