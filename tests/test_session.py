"""
test_session.py

This script tests the functionality of the EGSession class, ensuring that
it correctly manages state history, transformations, and undo/redo operations,
as well as the core game logic state.
"""

import pytest
from eg_hypergraph import EGHg, Node, Hyperedge
from eg_session import EGSession, Player, GameStatus

def test_session_initialization():
    """Tests that a session can be initialized with a thesis graph."""
    # Test with a minimal thesis graph
    session1 = EGSession(thesis_graph=EGHg())
    assert isinstance(session1.current_graph, EGHg)
    assert not session1.current_graph.nodes and not session1.current_graph.edges

    # Test with a more complex initial graph
    hg = EGHg()
    hg.add_node(Node('variable'))
    session2 = EGSession(thesis_graph=hg)
    assert len(session2.current_graph.nodes) == 1

def test_session_initialization_with_game_state():
    """Tests that a session initializes with the correct game state."""
    session = EGSession(thesis_graph=EGHg())
    assert session.player == Player.PROPOSER
    assert session.status == GameStatus.IN_PROGRESS
    assert session.contested_context is None

def test_apply_transformation_and_history():
    """Tests that applying a transformation correctly updates the history."""
    session = EGSession(thesis_graph=EGHg())
    assert len(session._history) == 1
    session.apply_transformation('add_double_cut', item_ids=[], container_id=None)
    assert len(session._history) == 2
    assert not session._history[0].edges
    assert len(session.current_graph.edges) == 2

def test_undo_redo():
    """Tests the undo and redo functionality."""
    session = EGSession(thesis_graph=EGHg())
    
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
    session = EGSession(thesis_graph=EGHg())
    session.apply_transformation('add_double_cut', item_ids=[], container_id=None) # State 1
    
    # Get the ID of the outer cut in state 1
    outer_cut_id_s1 = list(session.current_graph.edges.keys())[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=outer_cut_id_s1) # State 2
    
    session.undo() # Back to state 1
    
    # Apply a different transformation from state 1
    session.apply_transformation('erase', item_ids=[])
    
    assert len(session._history) == 3 # History should be [S0, S1, S_new_2]
    assert session._history_index == 2

    # Check that we can't redo to the old state 2
    session.redo()
    assert session._history_index == 2

def test_invalid_turn_does_not_update_history():
    """Tests that an invalid transformation does not change the state."""
    hg = EGHg()
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    predicate = hg.add_edge(Hyperedge('predicate', [], {'name': 'P'}), container=cut)
    
    session = EGSession(thesis_graph=hg)
    initial_graph = session.current_graph
    
    # This erase is invalid because the context is negative.
    # The apply_transformation method should return False and not update history.
    success = session.apply_transformation('erase', item_ids=[predicate.id])
    
    assert not success
    assert len(session._history) == 1
    # Because the transformation is immutable, the object should be different, but content the same
    assert session.current_graph.nodes == initial_graph.nodes
    assert session.current_graph.edges == initial_graph.edges
