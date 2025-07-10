"""
test_session.py

This script tests the functionality of the EGSession class, ensuring that
it correctly manages state history, transformations, and undo/redo operations.
"""

import pytest
from eg_hypergraph import EGHg, Node, Hyperedge
from eg_session import EGSession

def test_session_initialization():
    """Tests that a session can be initialized with or without a graph."""
    # Test with no initial graph
    session1 = EGSession()
    assert isinstance(session1.current_graph, EGHg)
    assert not session1.current_graph.nodes and not session1.current_graph.edges

    # Test with an initial graph
    hg = EGHg()
    hg.add_node(Node('variable'))
    session2 = EGSession(initial_graph=hg)
    assert len(session2.current_graph.nodes) == 1

def test_apply_transformation_and_history():
    """Tests that applying a transformation correctly updates the history."""
    session = EGSession()
    assert len(session._history) == 1
    assert session._history_index == 0

    # Apply a transformation
    session.apply_transformation('add_double_cut', item_ids=[], container_id=None)

    # Check history
    assert len(session._history) == 2
    assert session._history_index == 1
    
    # The original graph should be empty, the new one should have the double cut.
    assert not session._history[0].edges
    assert len(session.current_graph.edges) == 2

def test_undo_redo():
    """Tests the undo and redo functionality."""
    session = EGSession()
    
    # State 0: Empty graph
    assert len(session.current_graph.edges) == 0

    # State 1: Add a double cut
    session.apply_transformation('add_double_cut', item_ids=[], container_id=None)
    assert len(session.current_graph.edges) == 2

    # State 2: Add another double cut inside the first one
    outer_cut_id = list(session.current_graph.edges.keys())[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=outer_cut_id)
    assert len(session.current_graph.edges) == 4
    
    # --- Test Undo ---
    session.undo()
    assert session._history_index == 1
    assert len(session.current_graph.edges) == 2 # Back to state 1

    session.undo()
    assert session._history_index == 0
    assert len(session.current_graph.edges) == 0 # Back to state 0

    # Cannot undo past the beginning
    session.undo()
    assert session._history_index == 0 

    # --- Test Redo ---
    session.redo()
    assert session._history_index == 1
    assert len(session.current_graph.edges) == 2 # Forward to state 1

    session.redo()
    assert session._history_index == 2
    assert len(session.current_graph.edges) == 4 # Forward to state 2

    # Cannot redo past the end
    session.redo()
    assert session._history_index == 2

def test_new_transformation_after_undo():
    """
    Tests that applying a new transformation after an undo correctly
    truncates the old future history.
    """
    session = EGSession()
    session.apply_transformation('add_double_cut', item_ids=[], container_id=None) # State 1
    
    # Get the ID of the outer cut in state 1
    outer_cut_id_s1 = list(session.current_graph.edges.keys())[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=outer_cut_id_s1) # State 2
    
    session.undo() # Back to state 1
    
    # Apply a different transformation from state 1
    # This should erase the old state 2 from the history.
    session.apply_transformation('erase', item_ids=[])
    
    assert len(session._history) == 3 # History should be [S0, S1, S_new_2]
    assert session._history_index == 2

    # Check that we can't redo to the old state 2
    session.redo()
    assert session._history_index == 2
