"""
test_roundtrip.py

This script performs a full round-trip test of the translation modules.
It verifies that a CLIF string, when translated to a hypergraph and then
back to CLIF, retains its logical structure.
"""

import pytest
from lark import Lark
from clif_to_hypergraph import ClifToHypergraph
from hypergraph_to_clif import HypergraphToClif
from tests.clif_corpus import CORPUS as clif_corpus

# We need a parser to compare the structure of the CLIF strings,
# not just the raw text. We can reuse the grammar from the translator.
clif_grammar = r"""
    ?start: sexpr
    ?sexpr: atom | list
    list: "(" sexpr* ")"
    ?atom: SYMBOL | NUMBER | STRING | EQUALS
    EQUALS: "="
    SYMBOL: /[a-zA-Z_][a-zA-Z0-9_]*/
    STRING: /"([^"]|\\")*"/
    %import common.NUMBER
    %import common.WS
    %ignore WS
"""
clif_parser = Lark(clif_grammar, start='start')


def _perform_roundtrip_test(corpus_item: dict):
    """
    Helper function to perform a full round-trip test on a single corpus item.
    """
    original_clif = corpus_item['clif']
    description = corpus_item['description']

    # Step 1: Translate from CLIF to Hypergraph
    clif_to_hg_translator = ClifToHypergraph()
    try:
        hg = clif_to_hg_translator.translate(original_clif)
    except Exception as e:
        pytest.fail(f"Step 1 (CLIF->HG) failed for '{description}':\n{original_clif}\nError: {e}")

    # Step 2: Translate from Hypergraph back to CLIF
    hg_to_clif_translator = HypergraphToClif(hg)
    try:
        roundtrip_clif = hg_to_clif_translator.translate()
    except Exception as e:
        pytest.fail(f"Step 2 (HG->CLIF) failed for '{description}':\n{original_clif}\nError: {e}")

    # Step 3: Compare the original and round-tripped CLIF strings by parsing them
    # and comparing their abstract syntax trees for logical equivalence.
    try:
        original_tree = clif_parser.parse(original_clif)
        roundtrip_tree = clif_parser.parse(roundtrip_clif)
        
        assert original_tree == roundtrip_tree, \
            f"Round-trip failed for '{description}'.\n" \
            f"Original:   {original_clif}\n" \
            f"Round-trip: {roundtrip_clif}"

    except Exception as e:
        pytest.fail(f"AST comparison failed for '{description}':\n" \
                    f"Original:   {original_clif}\n" \
                    f"Round-trip: {roundtrip_clif}\n" \
                    f"Error: {e}")

# --- Test Suite ---
# Each test function corresponds to an entry in the corpus for clarity.

def test_simple_ligature():
    """Probes a simple existential with a two-place conjunction."""
    item = next(i for i in clif_corpus if "Simple ligature" in i['description'])
    _perform_roundtrip_test(item)

def test_complex_ligature():
    """Probes a more complex existential with multiple variables and predicates."""
    item = next(i for i in clif_corpus if "Complex ligature" in i['description'])
    _perform_roundtrip_test(item)

def test_cycle_ligature():
    """Probes a cycle of three relations to test ligature handling."""
    item = next(i for i in clif_corpus if "cycle of three relations" in i['description'])
    _perform_roundtrip_test(item)

def test_simple_negation():
    """Probes a simple negation, equivalent to a universal quantifier."""
    item = next(i for i in clif_corpus if "Simple negation" in i['description'])
    _perform_roundtrip_test(item)

def test_de_morgan():
    """Probes the negation of a conjunction (De Morgan's laws)."""
    item = next(i for i in clif_corpus if "De Morgan's laws" in i['description'])
    _perform_roundtrip_test(item)

def test_double_negation():
    """Probes a double negation, which should resolve."""
    item = next(i for i in clif_corpus if "Double negation" in i['description'])
    _perform_roundtrip_test(item)

def test_standard_universal():
    """Probes a standard universal quantifier with implication."""
    item = next(i for i in clif_corpus if "standard universal" in i['description'])
    _perform_roundtrip_test(item)

def test_nested_quantifiers():
    """Probes a nested existential quantifier inside a universal one."""
    item = next(i for i in clif_corpus if "nested existential" in i['description'])
    _perform_roundtrip_test(item)

def test_universal_two_variables():
    """Probes a universal quantifier with two variables."""
    item = next(i for i in clif_corpus if "Universal quantifier with two variables" in i['description'])
    _perform_roundtrip_test(item)

def test_simple_function():
    """Probes a simple function expression with constants."""
    item = next(i for i in clif_corpus if "Simple function" in i['description'])
    _perform_roundtrip_test(item)

def test_function_in_existential():
    """Probes a function used within an existential context."""
    item = next(i for i in clif_corpus if "Function used within an existential" in i['description'])
    _perform_roundtrip_test(item)

def test_nested_functions():
    """Probes nested functions within a universal quantifier."""
    item = next(i for i in clif_corpus if "Nested functions" in i['description'])
    _perform_roundtrip_test(item)

def test_zero_arity_proposition():
    """Probes a simple, zero-arity proposition (a constant)."""
    item = next(i for i in clif_corpus if "zero-arity" in i['description'])
    _perform_roundtrip_test(item)

def test_disjunction_of_existentials():
    """Probes a disjunction of two separate existential statements."""
    item = next(i for i in clif_corpus if "Disjunction of two separate" in i['description'])
    _perform_roundtrip_test(item)

def test_existential_over_disjunction():
    """Probes an existential quantifier over a disjunction."""
    item = next(i for i in clif_corpus if "Existential quantifier over a disjunction" in i['description'])
    _perform_roundtrip_test(item)

def test_implication_with_conjunction():
    """Probes an implication with a conjunction in the antecedent."""
    item = next(i for i in clif_corpus if "Implication with a conjunction" in i['description'])
    _perform_roundtrip_test(item)

def test_all_cats_are_black():
    """Probes the common idiom for 'All X are Y'."""
    item = next(i for i in clif_corpus if "All cats are black" in i['description'])
    _perform_roundtrip_test(item)
