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
    Checks the internal consistency of the hypergraph object.
    """
    all_item_ids = set(hg.nodes.keys()) | set(hg.edges.keys())
    assert all_item_ids == set(hg.containment.keys()), "Containment map mismatch"
    for item_id, container_id in hg.containment.items():
        if container_id is not None:
            container_edge = hg.edges.get(container_id)
            assert container_edge is not None, f"Item {item_id} points to non-existent container"
            assert item_id in container_edge.contained_items, f"Item {item_id} not in container's list"
    for container_id, container_edge in hg.edges.items():
        if container_edge.type == 'cut':
            for contained_item_id in container_edge.contained_items:
                assert hg.containment.get(contained_item_id) == container_id, "Containment mismatch"

def test_add_double_cut():
    """Tests adding a double cut around items."""
    hg = EGHg()
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    
    t = EGTransformation(hg)
    new_hg = t.add_double_cut([cat_node.id, cat_predicate.id])

    # Verify original graph is unchanged
    assert len(hg.edges) == 1
    
    # Verify new graph
    assert new_hg.get_context_depth(cat_predicate.id) == 2
    _verify_graph_integrity(new_hg)

def test_remove_double_cut():
    """Tests removing a double cut."""
    hg = EGHg()
    parent_container = hg.add_edge(Hyperedge('cut', nodes=[]))
    outer_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=parent_container)
    inner_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=outer_cut)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}), container=inner_cut)
    
    t = EGTransformation(hg)
    new_hg = t.remove_double_cut(outer_cut.id)
    
    assert hg.get_context_depth(cat_node.id) == 3
    assert new_hg.get_context_depth(cat_node.id) == 1
    _verify_graph_integrity(new_hg)

def test_double_cut_reversibility():
    """Tests that add/remove double cut are inverses."""
    hg = EGHg()
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    original_clif = HypergraphToClif(hg).translate()

    t1 = EGTransformation(hg)
    hg2 = t1.add_double_cut([cat_node.id, cat_predicate.id])
    
    sa_items = hg2.get_items_in_context(None)
    outer_cut_id = [i for i in sa_items if hg2.edges.get(i) and hg2.edges[i].type == 'cut'][0]

    t2 = EGTransformation(hg2)
    hg3 = t2.remove_double_cut(outer_cut_id)
    
    final_clif = HypergraphToClif(hg3).translate()
    assert final_clif == original_clif
    _verify_graph_integrity(hg3)

def test_erase_in_positive_context():
    """Tests the Beta Rule: erasure of a subgraph from a positive context."""
    hg = EGHg()
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    
    t = EGTransformation(hg)
    new_hg = t.erase([cat_node.id, cat_predicate.id])

    assert not new_hg.nodes and not new_hg.edges
    _verify_graph_integrity(new_hg)

def test_general_insert_in_negative_context():
    """Tests the Beta Rule: insertion of a complex subgraph into a negative context."""
    main_hg = EGHg()
    target_cut = main_hg.add_edge(Hyperedge('cut', nodes=[]))
    subgraph = EGHg()
    x_node_sub = subgraph.add_node(Node('variable', {'name': 'x'}))
    subgraph.add_edge(Hyperedge('predicate', [x_node_sub.id], {'name': 'Happy'}))

    t = EGTransformation(main_hg)
    new_hg = t.insert(subgraph, target_cut.id)

    items_in_cut = new_hg.get_items_in_context(target_cut.id)
    assert len(items_in_cut) == 2
    _verify_graph_integrity(new_hg)

def test_iteration():
    """Tests the Beta Rule: iteration into a deeper context."""
    hg = EGHg()
    x_node = hg.add_node(Node('variable', {'name': 'x'}))
    p_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}))
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    q_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'Q'}), container=cut)
    
    t = EGTransformation(hg)
    new_hg = t.iterate([p_pred.id], target_container_id=cut.id)
    
    clif_translator = HypergraphToClif(new_hg)
    generated_clif = clif_translator.translate()
    
    assert generated_clif == "(exists (x) (and (P x) (not (and (Q x) (P x)))))"
    _verify_graph_integrity(new_hg)

def test_iteration_reversibility():
    """Tests that iterate/deiterate are inverses."""
    hg = EGHg()
    x_node = hg.add_node(Node('variable', {'name': 'x'}))
    p_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}))
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'Q'}), container=cut)
    
    original_clif = HypergraphToClif(hg).translate()

    t1 = EGTransformation(hg)
    hg2 = t1.iterate([p_pred.id], target_container_id=cut.id)
    
    items_in_cut = hg2.get_items_in_context(cut.id)
    new_p_pred_id = [i for i in items_in_cut if hg2.edges[i].properties['name'] == 'P'][0]

    t2 = EGTransformation(hg2)
    hg3 = t2.deiterate([new_p_pred_id])

    final_clif = HypergraphToClif(hg3).translate()
    assert final_clif == original_clif
    _verify_graph_integrity(hg3)
