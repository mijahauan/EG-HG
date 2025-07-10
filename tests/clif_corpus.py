# new file: EG-CL/tests/clif_corpus.py

"""
A corpus of CLIF expressions for round-trip testing.
Each entry is a dictionary containing:
- 'clif': The CLIF string.
- 'description': A brief explanation of what the expression tests.
"""

CORPUS = [
    {
        'clif': "(exists (x) (and (Cat x) (Black x)))",
        'description': "Simple ligature representing 'A cat is black'."
    },
    {
        'clif': "(exists (x y) (and (Farmer x) (Donkey y) (Owns x y) (Beats x y)))",
        'description': "Complex ligature for 'A farmer owns a donkey and he beats it.' (from Peirce)."
    },
    {
        'clif': "(exists (x y z) (and (R x y) (S y z) (T z x)))",
        'description': "A cycle of three relations to test ligature handling."
    },
    {
        'clif': "(not (exists (x) (Unicorn x)))",
        'description': "Simple negation, equivalent to a universal quantifier."
    },
    {
        'clif': "(not (and (P) (Q)))",
        'description': "Negation of a conjunction (De Morgan's laws)."
    },
    {
        'clif': "(not (exists (x) (not (Person x))))",
        'description': "Double negation, which should resolve."
    },
    {
        'clif': "(forall (x) (if (Man x) (Mortal x)))",
        'description': "A standard universal quantifier with implication."
    },
    {
        'clif': "(forall (x) (if (Person x) (exists (y) (and (Woman y) (IsMotherOf y x)))))",
        'description': "Complex formula with nested existential quantifier inside a universal one."
    },
    {
        'clif': "(forall (x y) (if (and (Person x) (Loves x y)) (Person y)))",
        'description': "Universal quantifier with two variables."
    },
    {
        'clif': "(= (FatherOf Cain) Adam)",
        'description': "Simple function expression with constants."
    },
    {
        'clif': "(exists (x) (and (Person x) (= (FatherOf x) Zeus)))",
        'description': "Function used within an existential context."
    },
    {
        'clif': "(forall (x) (if (Person x) (= (MotherOf (FatherOf x)) (PaternalGrandmotherOf x))))",
        'description': "Nested functions within a universal quantifier."
    },
    {
        'clif': "(TuringWasAComputerScientist)",
        'description': "A simple, zero-arity proposition (constant)."
    },
    # --- New, more complex test cases ---
    {
        'clif': "(or (exists (x) (Cat x)) (exists (y) (Dog y)))",
        'description': "Disjunction of two separate existential statements."
    },
    {
        'clif': "(exists (x) (or (Cat x) (Dog x)))",
        'description': "Existential quantifier over a disjunction."
    },
    {
        'clif': "(forall (x) (if (and (Man x) (Rich x)) (Happy x)))",
        'description': "Implication with a conjunction in the antecedent."
    },
    {
        'clif': "(not (exists (x) (and (Cat x) (not (Black x)))))",
        'description': "Equivalent to 'All cats are black'."
    }
]
