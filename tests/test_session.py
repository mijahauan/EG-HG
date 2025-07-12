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
    # The initial graph should be the thesis wrapped in a cut
    assert len(session1.current_graph.edges) == 1
    assert list(session1.current_graph.edges.values())[0].type == 'cut'


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
    # The contested context should be the initial cut containing the thesis
    assert session.contested_context is not None
    assert session.contested_context in session.current_graph.edges

def test_apply_transformation_and_history():
    """Tests that applying a transformation correctly updates the history."""
    session = EGSession(thesis_graph=EGHg())
    assert len(session._history) == 1
    
    # The initial state is (not ()). Let's add a double cut inside.
    initial_cut_id = list(session.current_graph.edges.keys())[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=initial_cut_id)

    # Check history
    assert len(session._history) == 2
    assert session._history_index == 1
    
    # The original graph should have one cut, the new one should have three.
    assert len(session._history[0].edges) == 1
    assert len(session.current_graph.edges) == 3

def test_undo_redo():
    """Tests the undo and redo functionality."""
    session = EGSession(thesis_graph=EGHg())
    
    # State 0: (not ())
    assert len(session.current_graph.edges) == 1

    # State 1: Add a double cut
    initial_cut_id = session.contested_context
    session.apply_transformation('add_double_cut', item_ids=[], container_id=initial_cut_id)
    assert len(session.current_graph.edges) == 3

    # State 2: Add another double cut
    items_in_cut = session.current_graph.get_items_in_context(initial_cut_id)
    outer_cut_id = items_in_cut[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=outer_cut_id)
    assert len(session.current_graph.edges) == 5
    
    # --- Test Undo ---
    session.undo()
    assert session._history_index == 1
    assert len(session.current_graph.edges) == 3 # Back to state 1

    session.undo()
    assert session._history_index == 0
    assert len(session.current_graph.edges) == 1 # Back to state 0

    # Cannot undo past the beginning
    session.undo()
    assert session._history_index == 0 

    # --- Test Redo ---
    session.redo()
    assert session._history_index == 1
    assert len(session.current_graph.edges) == 3 # Forward to state 1

    session.redo()
    assert session._history_index == 2
    assert len(session.current_graph.edges) == 5 # Forward to state 2

    # Cannot redo past the end
    session.redo()
    assert session._history_index == 2

def test_new_transformation_after_undo():
    """
    Tests that applying a new transformation after an undo correctly
    truncates the old future history.
    """
    session = EGSession(thesis_graph=EGHg())
    initial_cut_id = session.contested_context
    session.apply_transformation('add_double_cut', item_ids=[], container_id=initial_cut_id) # State 1
    
    items_in_cut = session.current_graph.get_items_in_context(initial_cut_id)
    outer_cut_id_s1 = items_in_cut[0]
    session.apply_transformation('add_double_cut', item_ids=[], container_id=outer_cut_id_s1) # State 2
    
    session.undo() # Back to state 1
    
    # Apply a different transformation from state 1
    session.apply_transformation('erase', item_ids=[])
    
    assert len(session._history) == 3 # History should be [S0, S1, S_new_2]
    assert session._history_index == 2

    # Check that we can't redo to the old state 2
    session.redo()
    assert session._history_index == 2

def test_take_turn_updates_history():
    """Tests that a successful turn updates the graph history."""
    session = EGSession(thesis_graph=EGHg())
    initial_graph_id = id(session.current_graph)
    
    session.take_turn('add_double_cut', item_ids=[], container_id=session.contested_context)
    
    assert len(session._history) == 2
    assert id(session.current_graph) != initial_graph_id
    assert len(session.current_graph.edges) == 3

def test_invalid_turn_does_not_update_history():
    """Tests that an invalid transformation does not change the state."""
    hg = EGHg()
    cut = hg.add_edge(Hyperedge('cut', nodes=[]))
    predicate = hg.add_edge(Hyperedge('predicate', [], {'name': 'P'}), container=cut)
    
    session = EGSession(thesis_graph=hg)
    initial_graph = session.current_graph
    
    # This erase is invalid because the context is negative.
    success = session.apply_transformation('erase', item_ids=[predicate.id])
    
    assert not success
    assert len(session._history) == 1
    assert session.current_graph is initial_graph
