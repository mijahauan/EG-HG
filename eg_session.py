"""
eg_session.py

This module provides the EGSession class, which manages the state and
history of an Existential Graph during a proof or "inning" of the
Endoporeutic Game.
"""

from typing import List, Any, Optional
import copy

from eg_hypergraph import EGHg
from eg_transformations import EGTransformation

class EGSession:
    """
    Manages a sequence of transformations on an Existential Graph, maintaining
    a history of states for undo/redo functionality.
    """
    def __init__(self, initial_graph: Optional[EGHg] = None):
        """
        Initializes a new session.

        Args:
            initial_graph (Optional[EGHg]): The starting graph for the session.
                If None, starts with a blank Sheet of Assertion.
        """
        if initial_graph is None:
            initial_graph = EGHg()
        
        # The history of graph states. The current state is always the last one.
        self._history: List[EGHg] = [copy.deepcopy(initial_graph)]
        # A pointer to the current position in the history for undo/redo.
        self._history_index = 0

    @property
    def current_graph(self) -> EGHg:
        """Returns the current graph state in the session."""
        return self._history[self._history_index]

    def apply_transformation(self, rule_name: str, **kwargs: Any):
        """
        Applies a transformation rule to the current graph state and records
        the new state in the history.

        This method acts as a high-level controller that dispatches to the
        appropriate method in the EGTransformation class.

        Args:
            rule_name (str): The name of the transformation rule to apply
                (e.g., 'add_double_cut', 'erase').
            **kwargs: The arguments required by the specific transformation rule.
        """
        # Create a transformation controller for the current graph state.
        transformer = EGTransformation(self.current_graph)
        
        # Get the transformation method from the controller by name.
        transform_method = getattr(transformer, rule_name, None)
        if not callable(transform_method):
            raise AttributeError(f"'{rule_name}' is not a valid transformation rule.")

        # Apply the transformation to get the new graph state.
        new_graph = transform_method(**kwargs)

        # If the transformation was successful, update the history.
        # Any future states from a previous 'undo' are cleared.
        self._history_index += 1
        self._history = self._history[:self._history_index]
        self._history.append(new_graph)

    def undo(self):
        """
        Reverts to the previous state in the history.
        """
        if self._history_index > 0:
            self._history_index -= 1
        else:
            print("Warning: Cannot undo. Already at the beginning of history.")

    def redo(self):
        """
        Advances to the next state in the history after an undo.
        """
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
        else:
            print("Warning: Cannot redo. Already at the end of history.")

