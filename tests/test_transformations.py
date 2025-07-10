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
    t = EGTransformation(hg)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    t.add_double_cut([cat_node.id, cat_predicate.id])
    assert hg.get_context_depth(cat_predicate.id) == 2
    _verify_graph_integrity(hg)

def test_add_empty_double_cut_in_nested_context():
    """Tests adding an empty double cut to a nested context."""
    hg = EGHg()
    t = EGTransformation(hg)
    existing_cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    t.add_double_cut(item_ids=[], container_id=existing_cut.id)
    items_in_existing_cut = hg.get_items_in_context(existing_cut.id)
    new_outer_cut_id = items_in_existing_cut[0]
    assert hg.edges[new_outer_cut_id].type == 'cut'
    assert hg.get_context_depth(new_outer_cut_id) == 1
    _verify_graph_integrity(hg)

def test_remove_double_cut():
    """Tests removing a double cut."""
    hg = EGHg()
    t = EGTransformation(hg)
    parent_container = hg.add_edge(Hyperedge('cut', nodes=[]))
    outer_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=parent_container)
    inner_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=outer_cut)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}), container=inner_cut)
    t.remove_double_cut(outer_cut.id)
    assert hg.get_context_depth(cat_node.id) == 1
    _verify_graph_integrity(hg)

def test_double_cut_reversibility():
    """Tests that add/remove double cut are inverses."""
    hg = EGHg()
    t = EGTransformation(hg)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    original_clif = HypergraphToClif(hg).translate()
    items_to_enclose = [cat_node.id, cat_predicate.id]
    t.add_double_cut(items_to_enclose)
    sa_items = hg.get_items_in_context(None)
    outer_cut_id = [i for i in sa_items if hg.edges.get(i) and hg.edges[i].type == 'cut'][0]
    t.remove_double_cut(outer_cut_id)
    final_clif = HypergraphToClif(hg).translate()
    assert final_clif == original_clif
    _verify_graph_integrity(hg)

def test_erase_in_positive_context():
    """Tests the Beta Rule: erasure of a subgraph from a positive context."""
    hg = EGHg()
    t = EGTransformation(hg)
    cat_node = hg.add_node(Node('variable', {'name': 'x'}))
    cat_predicate = hg.add_edge(Hyperedge('predicate', [cat_node.id], {'name': 'Cat'}))
    t.erase([cat_node.id, cat_predicate.id])
    assert not hg.nodes and not hg.edges
    _verify_graph_integrity(hg)

def test_erase_in_negative_context_fails():
    """Tests that erasure from a negative (oddly-enclosed) context fails."""
    hg = EGHg()
    t = EGTransformation(hg)
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    predicate = hg.add_edge(Hyperedge('predicate', [], {'name': 'P'}), container=cut)
    with pytest.raises(ValueError, match="Erasure is not permitted in a negative context"):
        t.erase([predicate.id])
    _verify_graph_integrity(hg)

def test_general_insert_in_negative_context():
    """Tests the Beta Rule: insertion of a complex subgraph into a negative context."""
    main_hg = EGHg()
    t = EGTransformation(main_hg)
    target_cut = main_hg.add_edge(Hyperedge('cut', nodes=[]))

    subgraph = EGHg()
    x_node_sub = subgraph.add_node(Node('variable', {'name': 'x'}))
    subgraph.add_edge(Hyperedge('predicate', [x_node_sub.id], {'name': 'Happy'}))

    t.insert(subgraph, target_cut.id)

    items_in_cut = main_hg.get_items_in_context(target_cut.id)
    assert len(items_in_cut) == 2
    _verify_graph_integrity(main_hg)

def test_insert_in_positive_context_fails():
    """Tests that insertion into a positive (evenly-enclosed) context fails."""
    hg = EGHg()
    t = EGTransformation(hg)
    subgraph = EGHg()
    subgraph.add_node(Node('variable'))
    
    with pytest.raises(ValueError, match="Insertion is only permitted in negative contexts"):
        t.insert(subgraph, target_container_id=None)
    
    outer_cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    inner_cut = hg.add_edge(Hyperedge('cut', nodes=[]), container=outer_cut)
    with pytest.raises(ValueError, match="Insertion is not permitted in a positive context"):
        t.insert(subgraph, target_container_id=inner_cut.id)
    _verify_graph_integrity(hg)
    
def test_iteration():
    """Tests the Beta Rule: iteration into a deeper context."""
    hg = EGHg()
    t = EGTransformation(hg)
    x_node = hg.add_node(Node('variable', {'name': 'x'}))
    p_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}))
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    q_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'Q'}), container=cut)
    
    # Iterate just the predicate (P). The node (x) is a ligature and should be reused.
    t.iterate([p_pred.id], target_container_id=cut.id)
    
    items_in_cut = hg.get_items_in_context(cut.id)
    assert len(items_in_cut) == 2 # (Q x) and the new copy of (P x)
    
    clif_translator = HypergraphToClif(hg)
    generated_clif = clif_translator.translate()
    
    assert generated_clif == "(exists (x) (and (P x) (not (and (Q x) (P x)))))"
    
    _verify_graph_integrity(hg)

def test_iteration_fails_if_not_nested():
    """Tests that iteration fails if the target is not the same or deeper."""
    hg = EGHg()
    t = EGTransformation(hg)
    cut1 = hg.add_edge(Hyperedge('cut', nodes=[]))
    cut2 = hg.add_edge(Hyperedge('cut', nodes=[]))
    p_pred = hg.add_edge(Hyperedge('predicate', [], {'name': 'P'}), container=cut1)
    
    with pytest.raises(ValueError, match="Iteration is only permitted into the same or a deeper context"):
        t.iterate([p_pred.id], target_container_id=cut2.id)

    with pytest.raises(ValueError, match="Iteration is only permitted into the same or a deeper context"):
        t.iterate([p_pred.id], target_container_id=None)
        
    _verify_graph_integrity(hg)

def test_deiteration():
    """Tests the Beta Rule: deiteration of a redundant graph."""
    hg = EGHg()
    t = EGTransformation(hg)
    x_node = hg.add_node(Node('variable', {'name': 'x'}))
    p_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}))
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'Q'}), container=cut)
    # Manually add the iterated copy of (P x)
    iterated_p = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}), container=cut)
    
    # De-iterate the redundant copy.
    t.deiterate([iterated_p.id])
    
    items_in_cut = hg.get_items_in_context(cut.id)
    assert len(items_in_cut) == 1 # Only (Q x) should remain
    
    _verify_graph_integrity(hg)

def test_deiteration_fails_if_no_match():
    """Tests that deiteration fails if no matching graph exists in an ancestor context."""
    hg = EGHg()
    t = EGTransformation(hg)
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    p_pred = hg.add_edge(Hyperedge('predicate', [], {'name': 'P'}), container=cut)

    with pytest.raises(ValueError, match="De-iteration is not valid: no identical graph found in an enclosing context."):
        t.deiterate([p_pred.id])
    _verify_graph_integrity(hg)

def test_iteration_reversibility():
    """Tests that iterate/deiterate are inverses."""
    hg = EGHg()
    t = EGTransformation(hg)
    x_node = hg.add_node(Node('variable', {'name': 'x'}))
    p_pred = hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'P'}))
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    hg.add_edge(Hyperedge('predicate', [x_node.id], {'name': 'Q'}), container=cut)
    
    original_clif = HypergraphToClif(hg).translate()

    t.iterate([p_pred.id], target_container_id=cut.id)
    
    # Find the newly iterated copy
    items_in_cut = hg.get_items_in_context(cut.id)
    new_p_pred_id = [i for i in items_in_cut if hg.edges[i].properties['name'] == 'P'][0]

    t.deiterate([new_p_pred_id])

    final_clif = HypergraphToClif(hg).translate()
    assert final_clif == original_clif
    _verify_graph_integrity(hg)
