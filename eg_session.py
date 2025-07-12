"""
eg_session.py

This module provides the EGSession class, which manages the state and
history of an Existential Graph during a proof or "inning" of the
Endoporeutic Game.
"""

from typing import List, Any, Optional, Dict
import copy
from enum import Enum

from eg_hypergraph import EGHg, EdgeId, Hyperedge, Node
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
        
        # The game starts by placing the thesis inside a negation on the SA
        # This represents the Proposer's goal: to show that (not thesis) is a contradiction.
        initial_graph = EGHg()
        negation_cut = initial_graph.add_edge(Hyperedge(edge_type='cut', nodes=[]))
        
        # Use the transformation's copy logic to place the thesis inside the cut
        copier = EGTransformation(initial_graph)
        copier._copy_recursive(source_graph=thesis_graph, source_container_id=None, target_container=negation_cut)

        self._history: List[EGHg] = [initial_graph]
        self._history_index = 0
        
        self.player: Player = Player.PROPOSER
        self.status: GameStatus = GameStatus.IN_PROGRESS
        # The contested context is the initial negation cut
        self.contested_context: Optional[EdgeId] = negation_cut.id

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
        state of the contested graph. (This is a placeholder for a more complex implementation).
        """
        # A full implementation would inspect the contested context and return
        # a list of valid (rule, arguments) tuples.
        return []

    def take_turn(self, move: str, **kwargs: Any) -> GameStatus:
        """
        Represents a single turn in the game. The current player makes a move,
        which is a valid transformation. The game state is updated accordingly.
        """
        if self.status != GameStatus.IN_PROGRESS:
            print("Warning: The game has already concluded.")
            return self.status
        
        if self.apply_transformation(move, **kwargs):
            self.check_for_win_loss()

        return self.status

    def remove_negation(self):
        """
        A special game move that removes the outermost negation of the
        contested context, switches the player roles, and updates the
        contested context to the area that was just exposed.
        """
        if self.contested_context is None:
            raise ValueError("Cannot remove negation from the Sheet of Assertion.")
        
        new_hg = copy.deepcopy(self.current_graph)
        
        cut_to_remove = new_hg.edges[self.contested_context]
        parent_container_id = new_hg.containment[self.contested_context]
        parent_container = new_hg.edges.get(parent_container_id) if parent_container_id else None

        items_to_promote = list(cut_to_remove.contained_items)
        if parent_container:
            parent_container.contained_items.remove(self.contested_context)
        
        for item_id in items_to_promote:
            new_hg.containment[item_id] = parent_container_id
            if parent_container:
                parent_container.contained_items.append(item_id)
        
        del new_hg.containment[self.contested_context]
        del new_hg.edges[self.contested_context]

        self._history_index += 1
        self._history = self._history[:self._history_index]
        self._history.append(new_hg)

        self.player = Player.SKEPTIC if self.player == Player.PROPOSER else Player.PROPOSER
        # A simplification: assumes the new context is the first promoted item if it's a cut.
        self.contested_context = items_to_promote[0] if items_to_promote and items_to_promote[0] in new_hg.edges else None
        
        self.check_for_win_loss()

    def check_for_win_loss(self):
        """Checks the current graph for win/loss conditions."""
        if not self.current_graph.get_items_in_context(self.contested_context):
            if self.player == Player.PROPOSER:
                self.status = GameStatus.PROPOSER_WIN
            else:
                self.status = GameStatus.SKEPTIC_WIN
        
        # A full implementation would also check for the semantic mapping step.

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
