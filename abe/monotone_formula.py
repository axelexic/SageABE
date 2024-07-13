"""
Convert a monotone boolean formulae into a
    (a) a boolean parse tree
    (b) monotone span program
"""

import sage.logic.propcalc as prop
import sage.logic.logicparser as lp
from sage.rings.all import *
from enum import Enum
from sage.matrix.constructor import Matrix
from typing import Callable, Any

class NodeType(Enum):
    And =1
    Or = 2
    Not = 3
    Literal = 10

class TravOrder(Enum):
    Inorder = 1
    Preorder = 2
    Postorder = 3

class Formula:
    def __init__(self, ty : NodeType, name: str, left = None, right = None ) -> None:
        self._ty = ty
        self._name = name
        self._left = left
        self._right = right
        self._parent = None
        self._span = None
        self._content = None
        self._label = None

    def label(self):
        return self._label

    def set_label(self, label):
        self._label = label

    def unique_name(self):
        label = self.label()
        name = self.name()
        return f"{name}-{label}" if label else name

    def content(self):
        return self._content

    def set_content(self, new_content):
        old_content = self._content
        self._content = new_content
        return old_content

    def root(self):
        if self.parent() == None:
            return self
        else:
            return self.parent().root()

    def parent(self):
        return self._parent

    def set_parent(self, parent):
        old_parent = self._parent
        self._parent = parent
        return old_parent

    def span(self):
        return self._span

    def set_span(self, val):
        self._span = val

    def ty(self):
        return self._ty

    def left(self):
        return self._left

    def right(self):
        return self._right

    def name(self):
        return self._name

    def literals(self):
        if self.ty() == NodeType.Literal:
            return [self]
        elif self.ty() == NodeType.Not:
            return self.left().literals()
        else:
            lefts = self.left().literals()
            rights = self.right().literals()
            lefts.extend(rights)
            return lefts

    def sibling(self):
        parent = self.parent()
        if parent is None:
            return None
        l = parent.left()
        r = parent.right()
        if l == self:
            return r
        elif r == self:
            return l
        else:
            assert False, "Bug in code"

    def traverse(self, func : Callable[[Any], Any], order: TravOrder = TravOrder.Inorder, ):
        """
        Return the tree as a traversal list
        """

        if func == None:
            raise ValueError("Traverse must have a non-None callable")

        if self.ty == NodeType.Literal:
            func(self)
            return

        if order == TravOrder.Preorder:
            self.left().list_traverse(func,order)
            func(self)
            self.right().list_traverse(func, order)
        elif order == TravOrder.Inorder:
            func(self)
            self.left().list_traverse(func, order)
            self.right().list_traverse(func, order)
        elif order == TravOrder.Postorder:
            self.left().list_traverse(func, order)
            self.right().list_traverse(func, order)
            func(self)
        else:
            raise ValueError("Unknown traversal order")

    @staticmethod
    def relabel_duplicates(root_node):
        labels = root_node.literals()
        uniques = map(lambda x : x.name(), labels)
        indexes = dict(map(lambda x : (x, 0), uniques))

        for x in labels:
            assert isinstance(x, (LiteralNode))
            index = indexes[x.name()]
            indexes[x.name()] = index + 1
            x.set_label(index)


    @staticmethod
    def from_formula(formula_string: str, is_monotone=False):
        formula = prop.formula(formula_string)
        if not is_monotone:
            formula.convert_cnf()
        tree = formula.tree()
        tree = lp.apply_func(tree, formula.dist_not)
        formula = Formula.from_list(tree, is_monotone)

        if is_monotone:
            Formula.relabel_duplicates(formula)
            # formula.set_span([1])

        return formula

    @staticmethod
    def from_list(lst, is_monotone):
        if len(lst) == 3:
            if lst[0] == '&' and lst[1] == lst[2]:
                return LiteralNode(lst[1])
            elif lst[0] == '~' or lst[0] == '!'  or lst[0] == 'not':
                if is_monotone:
                    raise ValueError("Input formula is not monotone")
                if lst[1] == None and lst[2] == None:
                    raise ValueError("Negation of non-existent literal")
                entry = lst[1] or lst[2]
                rest = Formula.from_list(entry, is_monotone)
                node = NotNode(rest)
                rest.set_parent(node)
                return node

            elif lst[0] == '&' or lst[0] == 'and':
                if lst[1] == None or lst[2] == None:
                    raise ValueError("And of non-existent literal")

                left = Formula.from_list(lst[1], is_monotone)
                right = Formula.from_list(lst[2], is_monotone)
                node = AndNode(left, right)
                left.set_parent(node)
                right.set_parent(node)
                return node

            elif lst[0] == '|'  or lst[0] == 'or':
                if lst[1] == None or lst[2] == None:
                    raise ValueError("Or of non-existent literal")
                left = Formula.from_list(lst[1], is_monotone)
                right = Formula.from_list(lst[2], is_monotone)
                node = OrNode(left, right)
                left.set_parent(node)
                right.set_parent(node)
                return node

        elif len(lst) == 1:
            return LiteralNode(lst[0])
        else:
            raise ValueError("Invalid input formula")

class AndNode(Formula):
    def __init__(self, left, right) -> None:
        super().__init__(NodeType.And, "&", left, right);

    def __repr__(self) -> str:
        left = None
        right = None
        if self.left().ty() == NodeType.Literal:
            left = f"{self.left()}"
        else:
            left = f"({self.left()})"

        if self.right().ty() == NodeType.Literal:
            right = f"{self.right()}"
        else:
            right = f"({self.right()})"

        return f"{left} & {right}"

    def set_span(self, val):
        super().set_span(val)
        left = list(val)
        right = [0]*len(val)
        left.append(1)
        right.append(-1)
        self._left.set_span(left)
        self._right.set_span(right)

class OrNode(Formula):
    def __init__(self, left, right) -> None:
        super().__init__(NodeType.Or, "|", left, right);

    def __repr__(self) -> str:
        left = None
        right = None
        if self.left().ty() == NodeType.Literal:
            left = f"{self.left()}"
        else:
            left = f"({self.left()})"

        if self.right().ty() == NodeType.Literal:
            right = f"{self.right()}"
        else:
            right = f"({self.right()})"

        return f"{left} | {right}"

    def set_span(self, val):
        super().set_span(val)
        self._left.set_span(val)
        self._right.set_span(val)

class NotNode(Formula):
    def __init__(self, value) -> None:
        super().__init__(NodeType.Not, "~", value, None);

    def __repr__(self) -> str:
        left = None
        if self.left().ty() == NodeType.Literal:
            left = f"{self.left()}"
        else:
            left = f"({self.left()})"

        return f"~{left}"

    def set_span(self, val):
        raise ValueError("Attempt to span for not gate")

class LiteralNode(Formula):
    RESERVED = ['&', 'and', '|' , "or", "not" , "~"]

    def __init__(self, name: str) -> None:
        if name in LiteralNode.RESERVED:
            raise ValueError(f"Invalid name of literal: {name}")
        super().__init__(NodeType.Literal, name, None, None)
        self._label = 0

    def __repr__(self) -> str:
        if self.span():
            return f"{self.unique_name()}/{self.span()}"
        else:
            return f"{self.unique_name()}"


class MSP:
    def __init__(self, formula: str, ring = ZZ):
        node = Formula.from_formula(formula, True)
        attribues = node.literals()
        max_column = 0
        matrix_rows = list()
        pi = dict()
        row_count = 0

        for a in attribues:
            if len(a.span()) > max_column:
                max_column = len(a.span())

        for a in attribues:
            delta = max_column - len(a.span())
            span = list(a.span())
            if delta > 0:
                span.extend([0]*delta)
            matrix_rows.append(span)
            pi[a.unique_name()] = row_count
            row_count = row_count + 1

        self._node = node
        self._pi_inv = pi
        self._matrix = Matrix(ring, matrix_rows)

    def matrix(self):
        return self._matrix

    def node(self):
        return self._node

    def pi(self, index):
        for (lit,val) in enumerate(self._pi_inv):
            if val == index:
                return lit
        raise ValueError("Index not found")

    def pi_inverse(self, literal):
        return self._pi_inv[literal]


if __name__ == '__main__':
    def main():
        f = "a&((b|c)^a->c)<->b"
        tree = Formula.from_formula(f)
        print(f"{tree}")
        Formula.relabel_duplicates(tree)
        print(f"{tree}")

        try:
            f = "(a & b) | (b & ~c)"
            tree = Formula.from_formula(f, is_monotone=True)
            print("Monotonicity check failed");
        except ValueError:
            pass

        g = "(a & b) | (b & c) | (c & a)"
        tree = Formula.from_formula(g, is_monotone=True)
        print(f"{tree}")
        Formula.relabel_duplicates(tree)
        print(tree)

        mat = MSP(g, GF(17))
        print(mat.matrix())

    main()