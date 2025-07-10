"""
clif_to_hypergraph.py

This module provides the translator for converting a CLIF (Common Logic
Interchange Format) string into an EGHg (Existential Graph as a Hypergraph) model.
This version ensures insertion order is preserved for all elements.

The translation process involves several key steps:
1.  **Parsing**: A Lark-based parser transforms the raw CLIF string into an
    Abstract Syntax Tree (AST), which is easier to work with.
2.  **Recursive Traversal**: The translator class walks this AST recursively,
    processing each logical construct (e.g., 'and', 'not', 'exists').
3.  **Scope Management**: A stack of scopes is maintained to correctly handle
    variable bindings introduced by quantifiers like 'exists' and 'forall'.
4.  **Structure Building**: As the tree is traversed, corresponding nodes and
    hyperedges are created and added to the EGHg object, ensuring they are
    placed in the correct nested contexts (cuts).
"""

import uuid
from typing import Dict, Any, List, Optional

from lark import Lark, Tree, Token
from eg_hypergraph import EGHg, Node, Hyperedge, NodeId

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

class ClifToHypergraph:
    """
    Translates a CLIF string into an instance of the EGHg model by walking
    the parsed s-expression tree.
    """
    def __init__(self):
        """Initializes the translator with a parser and an empty graph."""
        self.parser = Lark(clif_grammar, start='start')
        self.eg = EGHg()
        self.scopes: List[Dict[str, NodeId]] = [{}]

    def translate(self, clif_string: str) -> EGHg:
        """
        The main public method to perform the translation.

        Args:
            clif_string (str): A string containing a valid CLIF expression.

        Returns:
            EGHg: The resulting hypergraph model.
        """
        clean_clif = clif_string.strip()
        if not clean_clif: return self.eg
        tree = self.parser.parse(clean_clif)
        self._visit(tree, container=None)
        return self.eg

    def _get_variable_node(self, name: str) -> NodeId:
        """Finds a variable's NodeId by searching up the scope stack."""
        for scope in reversed(self.scopes):
            if name in scope: return scope[name]
        raise NameError(f"Variable '{name}' not found in any active scope.")

    def _get_atom_value(self, tree_or_token) -> Optional[str]:
        """Recursively drills down a tree to find a single token value."""
        if isinstance(tree_or_token, Token):
            return tree_or_token.value[1:-1] if tree_or_token.type == 'STRING' else tree_or_token.value
        if isinstance(tree_or_token, Tree) and len(tree_or_token.children) == 1:
            return self._get_atom_value(tree_or_token.children[0])
        return None

    def _get_rule_name(self, tree: Tree) -> Optional[str]:
        """Robustly gets the grammar rule name from a Lark Tree."""
        if not isinstance(tree, Tree): return None
        data = tree.data
        return data.value if isinstance(data, Token) else data if isinstance(data, str) else None

    def _visit(self, tree: Tree, container: Optional[Hyperedge]):
        """Dispatches to the correct handler based on the AST node type."""
        if not isinstance(tree, Tree): return
        rule_type = self._get_rule_name(tree)
        if rule_type in ('start', 'sexpr') and tree.children:
            self._visit(tree.children[0], container)
        elif rule_type == 'list':
            self._visit_list(tree, container)
        elif rule_type == 'atom':
            print(f"Warning: Standalone atom found: {tree.children[0].value}")

    def _visit_term(self, term_sexpr: Tree, container: Optional[Hyperedge]) -> NodeId:
        """
        Processes a term, which can be a simple atom (variable/constant) or a
        complex functional term. Returns the NodeId representing the term.
        """
        # Case 1: The term is a simple atom.
        term_name = self._get_atom_value(term_sexpr)
        if term_name:
            try:
                return self._get_variable_node(term_name)
            except NameError:
                # Reuse existing constant node if one with the same name exists
                # in the current context.
                for node_id, node in self.eg.nodes.items():
                    if node.type == 'constant' and node.properties.get('name') == term_name and self.eg.containment.get(node_id) == (container.id if container else None):
                        return node_id
                return self.eg.add_node(Node(node_type='constant', props={'name': term_name}), container).id

        # Case 2: The term is a functional term, e.g., (FatherOf Cain).
        list_node = None
        rule_name = self._get_rule_name(term_sexpr)
        if rule_name == 'sexpr' and term_sexpr.children:
            list_node = term_sexpr.children[0]
        elif rule_name == 'list':
            list_node = term_sexpr

        if list_node and self._get_rule_name(list_node) == 'list':
            if not list_node.children: raise ValueError("Functional term cannot be empty.")
            function_name = self._get_atom_value(list_node.children[0])
            arg_sexprs = list_node.children[1:]
            # Create a new node to represent the output of the function.
            output_node = self.eg.add_node(Node(node_type='variable', props={'source_function': function_name}), container)
            # Recursively process arguments.
            arg_nodes = [self._visit_term(arg, container) for arg in arg_sexprs]
            # Create the function hyperedge. Convention: output node is first.
            self.eg.add_edge(Hyperedge(edge_type='function', nodes=[output_node.id] + arg_nodes, props={'name': function_name}), container)
            return output_node.id

        raise ValueError(f"Invalid term structure: {term_sexpr}")

    def _visit_list(self, list_tree: Tree, container: Optional[Hyperedge]):
        """Handles a list expression like (operator ...args)."""
        if not list_tree.children: return
        operator = self._get_atom_value(list_tree.children[0])
        if operator is None: raise ValueError(f"Invalid operator: {list_tree.children[0]}.")
        args = list_tree.children[1:]

        if operator == 'and':
            for arg in args: self._visit(arg, container)
        elif operator == 'not':
            if len(args) != 1: raise ValueError("'not' expects one argument")
            cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[]), container)
            self._visit(args[0], cut)
        elif operator in ('exists', 'forall'):
            self._handle_quantifier(operator, args, container)
        elif operator == 'or':
            outer_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[], props={'clif_construct': 'or'}), container)
            for arg in args:
                inner_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[]), outer_cut)
                self._visit(arg, inner_cut)
        elif operator == '=':
            if len(args) != 2: raise ValueError("'=' expects two arguments")
            nodes = [self._visit_term(arg, container) for arg in args]
            self.eg.add_edge(Hyperedge(edge_type='predicate', nodes=nodes, props={'name': 'equals'}), container)
        elif operator == 'if':
            if len(args) != 2: raise ValueError("'if' expects two arguments")
            p_sexpr, q_sexpr = args[0], args[1]
            outer_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[], props={'clif_construct': 'if'}), container)
            self._visit(p_sexpr, outer_cut)
            inner_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[]), outer_cut)
            self._visit(q_sexpr, inner_cut)
        else:
            self._visit_atom_predicate(operator, args, container)

    def _get_var_sexprs(self, vars_list_node: Tree, operator: str) -> List[Tree]:
        """Helper to robustly extract the list of variable s-expressions from a quantifier."""
        var_sexprs = None
        node_rule = self._get_rule_name(vars_list_node)
        if node_rule == 'sexpr' and vars_list_node.children:
            list_node = vars_list_node.children[0]
            if self._get_rule_name(list_node) == 'list': var_sexprs = list_node.children
        elif node_rule == 'list': var_sexprs = vars_list_node.children
        if var_sexprs is None: raise ValueError(f"Invalid variable list for '{operator}': {vars_list_node}")
        return var_sexprs

    def _handle_quantifier(self, operator: str, args: List[Tree], container: Optional[Hyperedge]):
        """Handles 'exists' and 'forall' quantifiers."""
        if len(args) != 2: raise ValueError(f"'{operator}' expects two arguments")
        vars_list_node, body_sexpr = args[0], args[1]
        var_sexprs = self._get_var_sexprs(vars_list_node, operator)
        var_names = [self._get_atom_value(node) for node in var_sexprs]
        
        if operator == 'exists':
            new_scope = {name: self.eg.add_node(Node(node_type='variable', props={'name': name}), container).id for name in var_names if name}
            self.scopes.append(new_scope)
            self._visit(body_sexpr, container)
            self.scopes.pop()
        else:  # forall
            outer_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[], props={'clif_construct': 'forall'}), container)
            new_scope = {name: self.eg.add_node(Node(node_type='variable', props={'name': name}), outer_cut).id for name in var_names if name}
            self.scopes.append(new_scope)
            inner_cut = self.eg.add_edge(Hyperedge(edge_type='cut', nodes=[]), outer_cut)
            self._visit(body_sexpr, inner_cut)
            self.scopes.pop()

    def _visit_atom_predicate(self, name: str, args: List[Tree], container: Optional[Hyperedge]):
        """Handles a regular atomic predicate with its arguments."""
        nodes = [self._visit_term(arg, container) for arg in args]
        self.eg.add_edge(Hyperedge(edge_type='predicate', nodes=nodes, props={'name': name}), container)
