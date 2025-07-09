"""
clif_to_hypergraph.py

This module provides the translator for converting a CLIF (Common Logic
Interchange Format) string into an EGHg (Existential Graph as a Hypergraph) model.

The translation process relies on:
1.  A Lark-based parser to transform the CLIF s-expression string into a syntax tree.
2.  A translator class that walks the syntax tree recursively.
3.  A scope manager to handle variable bindings from 'exists' and 'forall' quantifiers.
4.  A builder that constructs the EGHg by adding nodes and hyperedges into the
    correct nested contexts (cuts).
"""

import uuid
from typing import Dict, Any, Set, List, Optional, Tuple

# We will use the Lark parser for creating an AST from the CLIF s-expression.
# This dependency would need to be installed: pip install lark
from lark import Lark, Tree, Token

# Import the hypergraph data structures from the module we just defined.
from eg_hypergraph import EGHg, Node, Hyperedge, NodeId

# A more explicit grammar to distinguish lists from atoms.
# It now includes a specific terminal for the equals sign.
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
    Translates a CLIF string into an instance of the EGHg model.
    """
    def __init__(self):
        self.parser = Lark(clif_grammar, start='start')
        self.eg = EGHg()
        # Scope stack: A list of dictionaries. Each dict maps a var name (str) to a NodeId.
        self.scopes: List[Dict[str, NodeId]] = [{}]

    def translate(self, clif_string: str) -> EGHg:
        """
        The main public method to perform the translation.
        """
        clean_clif = clif_string.strip()
        if not clean_clif:
            return self.eg
        
        tree = self.parser.parse(clean_clif)
        self._visit(tree, container=None)
        return self.eg

    def _get_variable_node(self, name: str) -> NodeId:
        """Finds a variable's NodeId by searching up the scope stack."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Variable '{name}' not found in any active scope.")

    def _get_atom_value(self, tree_or_token) -> Optional[str]:
        """
        Recursively drills down a tree to find a single token value.
        Returns None if the path branches or ends without a token. This makes
        the logic robust to the parser's tree simplifications.
        """
        if isinstance(tree_or_token, Token):
            if tree_or_token.type == 'STRING':
                return tree_or_token.value[1:-1]
            return tree_or_token.value

        if isinstance(tree_or_token, Tree):
            if len(tree_or_token.children) == 1:
                return self._get_atom_value(tree_or_token.children[0])

        return None

    def _get_rule_name(self, tree: Tree) -> Optional[str]:
        """
        Robustly gets the rule name from a Tree, handling cases where tree.data is a Token.
        """
        if not isinstance(tree, Tree):
            return None
        
        data = tree.data
        if isinstance(data, Token):
            return data.value
        elif isinstance(data, str):
            return data
        return None

    def _visit(self, tree: Tree, container: Optional[Hyperedge]):
        """
        Recursively visits nodes of the parsed AST and builds the hypergraph.
        """
        if not isinstance(tree, Tree):
            return

        rule_type = self._get_rule_name(tree)
        
        if rule_type in ('start', 'sexpr'):
            if tree.children:
                self._visit(tree.children[0], container)
        
        elif rule_type == 'list':
            self._visit_list(tree, container)

        elif rule_type == 'atom':
            print(f"Warning: Standalone atom found: {tree.children[0].value}")
            pass

    def _visit_term(self, term_sexpr: Tree, container: Optional[Hyperedge]) -> NodeId:
        """
        Processes a term, which can be a variable, a constant, or a functional term.
        Returns the NodeId representing the term.
        """
        # Case 1: The term is a simple atom (variable or constant).
        term_name = self._get_atom_value(term_sexpr)
        if term_name:
            try:
                return self._get_variable_node(term_name)
            except NameError:
                for node_id, node in self.eg.nodes.items():
                    if node.type == 'constant' and node.properties.get('name') == term_name and self.eg.containment.get(node_id) == (container.id if container else None):
                        return node_id
                const_node = Node(node_type='constant', props={'name': term_name})
                self.eg.add_node(const_node, container)
                return const_node.id

        # Case 2: The term is a functional term (a list).
        list_node = None
        rule_name = self._get_rule_name(term_sexpr)
        if rule_name == 'sexpr' and term_sexpr.children:
            list_node = term_sexpr.children[0]
        elif rule_name == 'list':
            list_node = term_sexpr

        if list_node and self._get_rule_name(list_node) == 'list':
            if not list_node.children:
                raise ValueError("Functional term cannot be an empty list.")
            
            function_name = self._get_atom_value(list_node.children[0])
            arg_sexprs = list_node.children[1:]

            output_node = Node(node_type='variable', props={'source_function': function_name})
            self.eg.add_node(output_node, container)

            arg_nodes = {self._visit_term(arg, container) for arg in arg_sexprs}

            function_edge = Hyperedge(
                edge_type='function',
                nodes=arg_nodes.union({output_node.id}),
                props={'name': function_name, 'arg_count': len(arg_nodes)}
            )
            self.eg.add_edge(function_edge, container)
            
            return output_node.id

        raise ValueError(f"Invalid term structure: {term_sexpr}")

    def _visit_list(self, list_tree: Tree, container: Optional[Hyperedge]):
        """ Handles a list expression like (operator ...args). """
        if not list_tree.children:
            return

        operator_node = list_tree.children[0]
        operator = self._get_atom_value(operator_node)
        
        if operator is None:
            raise ValueError(f"Invalid operator in expression: {operator_node}.")
        
        args = list_tree.children[1:]

        if operator == 'and':
            for arg in args:
                self._visit(arg, container)

        elif operator == 'not':
            if len(args) != 1: raise ValueError("'not' expects one argument")
            cut_edge = Hyperedge(edge_type='cut', nodes=set())
            self.eg.add_edge(cut_edge, container)
            self._visit(args[0], cut_edge)

        elif operator == 'exists':
            if len(args) != 2: raise ValueError("'exists' expects two arguments")
            
            vars_list_node, body_sexpr = args[0], args[1]
            
            var_sexprs = None
            node_rule = self._get_rule_name(vars_list_node)
            if node_rule == 'sexpr' and vars_list_node.children:
                list_node = vars_list_node.children[0]
                if self._get_rule_name(list_node) == 'list':
                    var_sexprs = list_node.children
            elif node_rule == 'list':
                var_sexprs = vars_list_node.children
            
            if var_sexprs is None: raise ValueError(f"Invalid variable list for 'exists': {vars_list_node}")

            var_names = [self._get_atom_value(node) for node in var_sexprs]
            new_scope = {name: self.eg.add_node(Node(node_type='variable', props={'name': name}), container).id for name in var_names if name}
            self.scopes.append(new_scope)
            self._visit(body_sexpr, container)
            self.scopes.pop()
        
        elif operator == 'or':
            outer_cut = Hyperedge(edge_type='cut', nodes=set(), props={'clif_construct': 'or'})
            self.eg.add_edge(outer_cut, container)
            for arg in args:
                inner_cut = Hyperedge(edge_type='cut', nodes=set())
                self.eg.add_edge(inner_cut, outer_cut)
                self._visit(arg, inner_cut)

        elif operator == '=':
            if len(args) != 2: raise ValueError("'=' expects two arguments")
            left_node_id = self._visit_term(args[0], container)
            right_node_id = self._visit_term(args[1], container)
            equals_edge = Hyperedge(edge_type='predicate', nodes={left_node_id, right_node_id}, props={'name': 'equals'})
            self.eg.add_edge(equals_edge, container)
            
        elif operator == 'if':
            # (if P Q) is equivalent to (not (and P (not Q)))
            if len(args) != 2: raise ValueError("'if' expects two arguments")
            p_sexpr, q_sexpr = args[0], args[1]
            
            # Create the outer 'not' cut
            outer_cut = Hyperedge(edge_type='cut', nodes=set(), props={'clif_construct': 'if'})
            self.eg.add_edge(outer_cut, container)
            
            # Visit P inside the outer cut
            self._visit(p_sexpr, outer_cut)
            
            # Create the inner 'not' cut for Q
            inner_cut = Hyperedge(edge_type='cut', nodes=set())
            self.eg.add_edge(inner_cut, outer_cut)
            
            # Visit Q inside the inner cut
            self._visit(q_sexpr, inner_cut)

        elif operator == 'forall':
            # (forall (vars) body) is equivalent to (not (exists (vars) (not body)))
            if len(args) != 2: raise ValueError("'forall' expects two arguments")
            
            vars_list_node, body_sexpr = args[0], args[1]

            # Create the outer 'not' cut
            outer_cut = Hyperedge(edge_type='cut', nodes=set(), props={'clif_construct': 'forall'})
            self.eg.add_edge(outer_cut, container)
            
            # Handle the inner '(exists (vars) (not body))'
            var_sexprs = None
            node_rule = self._get_rule_name(vars_list_node)
            if node_rule == 'sexpr' and vars_list_node.children:
                list_node = vars_list_node.children[0]
                if self._get_rule_name(list_node) == 'list':
                    var_sexprs = list_node.children
            elif node_rule == 'list':
                var_sexprs = vars_list_node.children
            
            if var_sexprs is None: raise ValueError(f"Invalid variable list for 'forall': {vars_list_node}")

            var_names = [self._get_atom_value(node) for node in var_sexprs]
            
            # Create variable nodes inside the outer cut (where the existential quantifier lives)
            new_scope = {name: self.eg.add_node(Node(node_type='variable', props={'name': name}), outer_cut).id for name in var_names if name}
            self.scopes.append(new_scope)
            
            # Create the inner 'not' cut for the body
            inner_cut = Hyperedge(edge_type='cut', nodes=set())
            self.eg.add_edge(inner_cut, outer_cut)
            
            # Visit the body inside the inner cut
            self._visit(body_sexpr, inner_cut)
            
            self.scopes.pop()

        else: # It's an atomic sentence
            self._visit_atom_predicate(operator, args, container)

    def _visit_atom_predicate(self, predicate_name: str, term_sexprs: List[Tree], container: Optional[Hyperedge]):
        """Handles an atomic predicate with its terms."""
        term_nodes = {self._visit_term(sexpr, container) for sexpr in term_sexprs}
        predicate_edge = Hyperedge(edge_type='predicate', nodes=term_nodes, props={'name': predicate_name})
        self.eg.add_edge(predicate_edge, container)
