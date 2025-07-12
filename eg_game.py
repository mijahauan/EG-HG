"""
eg_game.py

This module provides the EndoporeuticGame class, which serves as the main
controller for the application. It manages a library of graphs ("folios")
and controls the creation and lifecycle of proof sessions ("innings").
"""

from typing import Dict, Optional
import copy

from eg_hypergraph import EGHg
from eg_session import EGSession

class EndoporeuticGame:
    """
    Manages a collection of named graphs (a folio) and the sessions (innings)
    where proofs are constructed. This class is the main entry point for the
    application's backend logic.
    """
    def __init__(self):
        """
        Initializes the game controller with an empty folio.
        """
        self.folio: Dict[str, EGHg] = {}

    def add_to_folio(self, name: str, graph: EGHg):
        """
        Adds a named graph to the game's folio. This can be used to store
        domain models, theorems, or interesting starting positions.

        Args:
            name (str): The unique name to identify the graph in the folio.
            graph (EGHg): The graph object to store.
        """
        if name in self.folio:
            raise ValueError(f"A graph with the name '{name}' already exists in the folio.")
        self.folio[name] = copy.deepcopy(graph)

    def start_inning(self, thesis_graph: EGHg, domain_model_name: Optional[str] = None) -> EGSession:
        """
        Starts a new "inning" of the game (a new proof session).

        The session is initialized with a combination of a thesis graph and
        an optional domain model from the folio.

        Args:
            thesis_graph (EGHg): The graph representing the initial proposition
                or "thesis" of the proof.
            domain_model_name (Optional[str]): The name of a graph from the
                folio to use as the starting context or domain model.

        Returns:
            EGSession: A new session object ready for transformations.
        """
        domain_model = None
        if domain_model_name:
            if domain_model_name not in self.folio:
                raise ValueError(f"Domain model '{domain_model_name}' not found in folio.")
            # Retrieve a copy of the domain model so the original is not affected.
            domain_model = copy.deepcopy(self.folio[domain_model_name])
        
        # The session is initialized with the thesis and the chosen domain model.
        return EGSession(thesis_graph=thesis_graph, domain_model=domain_model)

    def bootstrap_domain(self, session: EGSession, new_model_name: str):
        """
        Extends a domain model based on the successful outcome of a game session.
        This is used for the "Draw and Extend" outcome.

        Args:
            session (EGSession): The completed session whose final state will be
                merged into the domain model.
            new_model_name (str): The name for the new, extended domain model.
        """
        # A full implementation would merge the session's final graph with
        # its initial domain model. For now, we just save the final state.
        final_graph_state = session.current_graph
        self.add_to_folio(new_model_name, final_graph_state)

