"""
eg_game.py

This module provides the EndoporeuticGame class, which serves as the main
controller for the application. It manages a library of graphs ("folios")
and controls the creation and lifecycle of proof sessions ("innings").
"""

from typing import Dict, Optional

from eg_hypergraph import EGHg
from eg_session import EGSession

class EndoporeuticGame:
    """
    Manages a collection of named graphs (a folio) and the sessions (innings)
    where proofs are constructed.
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
        self.folio[name] = graph

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
        initial_graph = EGHg()

        # If a domain model is specified, copy it to the new graph first.
        if domain_model_name:
            if domain_model_name not in self.folio:
                raise ValueError(f"Domain model '{domain_model_name}' not found in folio.")
            # We would perform a deep copy here to start the session
            # For now, we'll assume the initial graph is just the thesis.
            # A full implementation would merge the domain model and thesis.
            initial_graph = self.folio[domain_model_name]


        # For now, we will just start with the thesis graph.
        # A more advanced implementation would merge the thesis with the domain model.
        initial_graph = thesis_graph
        
        return EGSession(initial_graph=initial_graph)

