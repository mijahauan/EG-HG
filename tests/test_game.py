"""
test_game.py

This script tests the functionality of the EndoporeuticGame class, ensuring
that it correctly manages folios and the creation of new sessions (innings).
"""

import pytest
from eg_hypergraph import EGHg, Node
from eg_game import EndoporeuticGame
from eg_session import EGSession

def test_game_initialization():
    """Tests that the game controller initializes with an empty folio."""
    game = EndoporeuticGame()
    assert isinstance(game.folio, dict)
    assert not game.folio

def test_add_to_folio():
    """Tests adding a named graph to the folio."""
    game = EndoporeuticGame()
    domain_model = EGHg()
    domain_model.add_node(Node('constant', {'name': 'Socrates'}))
    
    game.add_to_folio("Greek Philosophy", domain_model)
    
    assert "Greek Philosophy" in game.folio
    assert len(game.folio["Greek Philosophy"].nodes) == 1

def test_add_duplicate_name_to_folio_fails():
    """Tests that adding a graph with a duplicate name raises an error."""
    game = EndoporeuticGame()
    game.add_to_folio("My Model", EGHg())
    
    with pytest.raises(ValueError, match="already exists in the folio"):
        game.add_to_folio("My Model", EGHg())

def test_start_inning_with_thesis():
    """Tests starting a new session (inning) with just a thesis graph."""
    game = EndoporeuticGame()
    thesis = EGHg()
    thesis.add_node(Node('variable', {'name': 'x'}))
    
    session = game.start_inning(thesis_graph=thesis)
    
    assert isinstance(session, EGSession)
    assert len(session.current_graph.nodes) == 1
    assert not session.domain_model.nodes # Domain model should be empty

def test_start_inning_with_domain_model():
    """
    Tests starting a new inning with a domain model from the folio.
    """
    game = EndoporeuticGame()
    
    # Create and store a domain model
    domain_model = EGHg()
    domain_model.add_node(Node('constant', {'name': 'Socrates'}))
    game.add_to_folio("Greek Philosophy", domain_model)
    
    # Create a thesis graph
    thesis = EGHg()
    thesis.add_node(Node('variable', {'name': 'x'}))

    # Start the inning
    session = game.start_inning(thesis_graph=thesis, domain_model_name="Greek Philosophy")
    
    # The session should contain both the thesis and the domain model
    assert len(session.current_graph.nodes) == 1
    assert len(session.domain_model.nodes) == 1
    assert 'Socrates' in [n.properties.get('name') for n in session.domain_model.nodes.values()]


def test_start_inning_with_nonexistent_domain_model_fails():
    """
    Tests that starting an inning with a non-existent domain model
    raises an error.
    """
    game = EndoporeuticGame()
    thesis = EGHg()
    
    with pytest.raises(ValueError, match="not found in folio"):
        game.start_inning(thesis_graph=thesis, domain_model_name="Atlantis")

