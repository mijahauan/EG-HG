"""
eg_session.py

This module provides the EGSession class, which manages the state and
history of an Existential Graph during a proof or "inning" of the
Endoporeutic Game.
"""

from typing import List, Any, Optional, Dict
import copy
from enum import Enum

from eg_hypergraph import EGHg, EdgeId, Hyperedge
from eg_transformations import EGTransformation

class Player(Enum):
    """Represents the current player in the Endoporeutic Game."""
    PROPOSER = 1
    SKEPTIC = 2

class GameStatus(Enum):
    """Represents the current status of the game."""
    IN_PROGRESS = 1
    PROPOSER_WIN = 2
    SKEPTIC_WIN = 3
    DRAW_EXTEND = 4 # For when a thesis is consistent but not provable

class EGSession:
    """
    Manages a sequence of transformations on an Existential Graph, maintaining
    a history of states and the logic for the Endoporeutic Game.
    """
    def __init__(self, thesis_graph: EGHg, domain_model: Optional[EGHg] = None):
        """
        Initializes a new session (inning).

        Args:
            thesis_graph (EGHg): The graph representing the thesis of the proof.
            domain_model (Optional[EGHg]): The model against which the thesis
                is evaluated. If None, an empty model is used.
        """
        self.domain_model = domain_model or EGHg()
        
        # The initial state is the thesis scribed on the Sheet of Assertion.
        initial_graph = copy.deepcopy(thesis_graph)
        
        self._history: List[EGHg] = [initial_graph]
        self._history_index = 0
        
        self.player: Player = Player.PROPOSER
        self.status: GameStatus = GameStatus.IN_PROGRESS
        # The ID of the cut that is the current focus of the game.
        # None means the Sheet of Assertion is the contested area.
        self.contested_context: Optional[EdgeId] = None

    @property
    def current_graph(self) -> EGHg:
        """Returns the current graph state in the session."""
        return self._history[self._history_index]

    def apply_transformation(self, rule_name: str, **kwargs: Any) -> bool:
        """
        Applies a transformation rule to the current graph state and records
        the new state in the history. Returns True if successful.
        """
        transformer = EGTransformation(self.current_graph)
        transform_method = getattr(transformer, rule_name, None)
        if not callable(transform_method):
            raise AttributeError(f"'{rule_name}' is not a valid transformation rule.")

        try:
            new_graph = transform_method(**kwargs)
            self._history_index += 1
            self._history = self._history[:self._history_index]
            self._history.append(new_graph)
            return True
        except ValueError as e:
            print(f"Transformation failed: {e}")
            return False

    def get_legal_moves(self) -> List[Dict[str, Any]]:
        """
        Determines the set of legal moves for the current player based on the
        state of the contested graph. This is the core of the game's intelligence.
        (This is a placeholder for a more complex implementation).
        """
        # A full implementation would inspect the contested context and return
        # a list of valid (rule, arguments) tuples.
        # For example, if the contested graph is `(not G)` and player is Proposer,
        # the only move is to remove the negation.
        return []

    def take_turn(self, move: str, **kwargs: Any) -> GameStatus:
        """
        Represents a single turn in the game. The current player makes a move,
        which is a valid transformation. The game state is updated accordingly.
        """
        if self.status != GameStatus.IN_PROGRESS:
            print("Warning: The game has already concluded.")
            return self.status

        # In a full implementation, we would first check if the proposed move
        # is in the list returned by get_legal_moves().
        
        if self.apply_transformation(move, **kwargs):
            # A full implementation would update the player and contested context
            # based on the move made (e.g., removing a negation switches roles).
            pass

        # A full implementation would check for win/loss conditions here.
        return self.status

    def undo(self):
        """Reverts to the previous state in the history."""
        if self._history_index > 0:
            self._history_index -= 1
        else:
            print("Warning: Cannot undo. Already at the beginning of history.")

    def redo(self):
        """Advances to the next state in the history after an undo."""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
        else:
            print("Warning: Cannot redo. Already at the end of history.")

