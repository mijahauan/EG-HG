"""
test_transformations.py

This script contains a suite of pytest-based tests for the EGTransformation
controller, verifying that the rules of inference are applied correctly and
that the graph remains in a well-formed state after each transformation.
"""

import pytest
from eg_hypergraph import EGHg, Node, Hyperedge
from eg_transformations import EGTransformation

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
    # 1. Setup: Create a graph with two predicates on the Sheet of Assertion.
    hg = EGHg()
    t = EGTransformation(hg)
    
    # (Cat x)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    
    # (Dog y)
    dog_node = hg.add_node(Node('variable', {'name': 'y'}))
    dog_predicate = hg.add_edge(Hyperedge('predicate', [dog_node.id], {'name': 'Dog'}))

    # Initial state assertions
    assert hg.get_context_depth(cat_predicate.id) == 0
    assert len(hg.get_items_in_context(None)) == 4 # 2 nodes, 2 edges

    # 2. Action: Add a double cut around the (Cat x) graph.
    items_to_enclose = [cat_node.id, cat_predicate.id]
    t.add_double_cut(items_to_enclose)

    # 3. Verification
    # Find the new cuts
    sa_items = hg.get_items_in_context(None)
    assert len(sa_items) == 3 # (Dog y) graph + the new outer cut
    
    outer_cut = [hg.edges[i] for i in sa_items if hg.edges.get(i) and hg.edges[i].type == 'cut'][0]
    assert outer_cut is not None
    
    items_in_outer_cut = hg.get_items_in_context(outer_cut.id)
    assert len(items_in_outer_cut) == 1
    
    inner_cut = hg.edges[items_in_outer_cut[0]]
    assert inner_cut.type == 'cut'

    # Check that the items were moved correctly
    items_in_inner_cut = hg.get_items_in_context(inner_cut.id)
    assert len(items_in_inner_cut) == 2
    assert cat_node.id in items_in_inner_cut
    assert cat_predicate.id in items_in_inner_cut

    # Verify the new context depth
    assert hg.get_context_depth(cat_predicate.id) == 2
    # Verify the other item was not affected
    assert hg.get_context_depth(dog_predicate.id) == 0
    
    # 4. Final Integrity Check
    _verify_graph_integrity(hg)

def test_add_empty_double_cut_in_nested_context():
    """
    Tests adding an empty double cut to a pre-existing negative context.
    It verifies the final structure and the overall integrity of the graph.
    """
    # 1. Setup: Create a graph with a cut: (not ( ... ))
    hg = EGHg()
    t = EGTransformation(hg)
    
    # Create the outer context
    existing_cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    assert hg.get_context_depth(existing_cut.id) == 0

    # 2. Action: Add an empty double cut inside the existing cut.
    t.add_double_cut(item_ids=[], container_id=existing_cut.id)

    # 3. Verification
    # The existing cut should now contain one item: the new outer cut.
    items_in_existing_cut = hg.get_items_in_context(existing_cut.id)
    assert len(items_in_existing_cut) == 1
    
    new_outer_cut = hg.edges[items_in_existing_cut[0]]
    assert new_outer_cut.type == 'cut'
    
    # The new outer cut should contain one item: the new inner cut.
    items_in_new_outer_cut = hg.get_items_in_context(new_outer_cut.id)
    assert len(items_in_new_outer_cut) == 1
    
    new_inner_cut = hg.edges[items_in_new_outer_cut[0]]
    assert new_inner_cut.type == 'cut'
    
    # The new inner cut should be empty.
    assert len(hg.get_items_in_context(new_inner_cut.id)) == 0
    
    # Verify context depths
    assert hg.get_context_depth(new_outer_cut.id) == 1
    assert hg.get_context_depth(new_inner_cut.id) == 2
    
    # 4. Final Integrity Check
    _verify_graph_integrity(hg)

