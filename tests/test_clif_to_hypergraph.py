"""
test_clif_to_hypergraph.py

This script contains a suite of pytest-based tests for the ClifToHypergraph translator.
It uses the existing clif_corpus to verify that the translation to the
EGHg (Existential Graph as a Hypergraph) model is correct and robust.
"""

import pytest
from clif_to_hypergraph import ClifToHypergraph
from eg_hypergraph import EGHg, Hyperedge
# Assuming clif_corpus.py is in the same directory or accessible via python path
# and that it provides a list of dictionaries named 'CORPUS'.
from tests.clif_corpus import CORPUS as clif_corpus

# --- Pytest-based Test Suite ---

# Use pytest's parametrize feature to create a test for each item in the corpus
# The 'ids' parameter will use the description for more readable test output.
@pytest.mark.parametrize("corpus_item", clif_corpus, ids=[item['description'] for item in clif_corpus])
def test_translate_corpus_item(corpus_item):
    """
    Tests that each CLIF string in the corpus can be translated into a
    hypergraph without raising an error.
    """
    translator = ClifToHypergraph()
    clif_text = corpus_item['clif']
    description = corpus_item['description']
    
    try:
        # We need to handle 'forall' and 'if' by converting them first.
        # This is a placeholder for a more robust pre-processing step.
        """
        if 'forall' in clif_text or 'if' in clif_text:
            clif_text = clif_text.replace("forall", "not exists not") # Simplistic substitution
            clif_text = clif_text.replace("if", "not and not") # Simplistic substitution
            pytest.skip(f"Skipping direct test for '{description}' due to forall/if. Requires pre-processing.")
        """

        hg = translator.translate(clif_text)
        
        # Basic sanity check: the graph should not be empty for a non-empty input.
        if clif_text.strip():
            assert len(hg.nodes) > 0 or len(hg.edges) > 0, f"Translation produced an empty graph for: {description}"
    except Exception as e:
        pytest.fail(f"Translation failed for '{description}':\n{clif_text}\n\nError: {e}")

# You can keep more specific, individual tests as well.
def test_specific_forall_implication():
    """
    Tests the specific forall/if case, translated to not/exists/and/not,
    to ensure its structure is precisely correct.
    """
    clif = "(not (exists (d) (and (Dog d) (not (exists (m) (and (Master m d) (Loves d m)))))))"
    translator = ClifToHypergraph()
    hg = translator.translate(clif)
    
    # --- Assertions ---
    assert len(hg.nodes) == 2, "Should create 2 variable nodes ('d', 'm')"
    assert len(hg.edges) == 5, "Should create 5 edges (2 cuts, 3 predicates)"

    # Find the key elements
    sa_items = hg.get_items_in_context(None)
    assert len(sa_items) == 1, "Sheet of Assertion should contain only the outer cut"
    outer_cut_id = sa_items[0]
    assert hg.edges[outer_cut_id].type == 'cut'

    outer_cut_items = {item for item in hg.get_items_in_context(outer_cut_id)}
    assert len(outer_cut_items) == 3, "Outer cut should contain node 'd', 'Dog' predicate, and inner cut"

    inner_cut_id = [i for i in outer_cut_items if isinstance(hg.edges.get(i), Hyperedge) and hg.edges[i].type == 'cut'][0]
    
    inner_cut_items = hg.get_items_in_context(inner_cut_id)
    assert len(inner_cut_items) == 3, "Inner cut should contain node 'm', 'Master' predicate, and 'Loves' predicate"

    # Check containment of predicates
    dog_pred = [e for e in hg.edges.values() if e.properties.get('name') == 'Dog'][0]
    master_pred = [e for e in hg.edges.values() if e.properties.get('name') == 'Master'][0]
    loves_pred = [e for e in hg.edges.values() if e.properties.get('name') == 'Loves'][0]
    
    assert hg.containment[dog_pred.id] == outer_cut_id
    assert hg.containment[master_pred.id] == inner_cut_id
    assert hg.containment[loves_pred.id] == inner_cut_id

# To run these tests, save this file (e.g., in your 'tests' subdirectory)
# and then run pytest from your project's root directory.
# Example:
# (EG-HG) % pytest
