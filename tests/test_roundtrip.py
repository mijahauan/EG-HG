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

# --- Pytest-based Round-trip Test ---

@pytest.mark.parametrize("corpus_item", clif_corpus, ids=[item['description'] for item in clif_corpus])
def test_roundtrip_translation(corpus_item):
    """
    Tests that a CLIF string can be translated to a hypergraph and back
    to a logically equivalent CLIF string.
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

