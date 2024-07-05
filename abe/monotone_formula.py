"""
Convert a monotone boolean formulae into a
    (a) a boolean parse tree
    (b) monotone span program
"""

import sage.logic.propcalc as prop
import sage.logic.logicparser as lp
from enum import Enum

class NodeType(Enum):
    And =1
    Or = 2
    Not = 3
    Literal = 10

class Node:
    def __init__(self, ty : NodeType, name: str, left = None, right = None ) -> None:
        self._ty = ty
        self._name = name
        self._left = left
        self._right = right
        self._parent = None

    def parent(self):
        return self._parent

    def set_parent(self, parent):
        old_parent = self._parent
        self._parent = parent
        return old_parent

    def ty(self):
        return self._ty

    def left(self):
        return self._left

    def right(self):
        return self._right

    def name(self):
        return self._name


    @staticmethod
    def from_formula(formula_string: str, is_monotone=False):
        formula = prop.formula(formula_string)
        if not is_monotone:
            formula.convert_cnf()
        tree = formula.tree()
        tree = lp.apply_func(tree, formula.dist_not)
        return Node.from_list(tree, is_monotone)

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
                rest = Node.from_list(entry, is_monotone)
                node = NotNode(rest)
                rest.set_parent(node)
                return node

            elif lst[0] == '&' or lst[0] == 'and':
                if lst[1] == None or lst[2] == None:
                    raise ValueError("And of non-existent literal")

                left = Node.from_list(lst[1], is_monotone)
                right = Node.from_list(lst[2], is_monotone)
                node = AndNode(left, right)
                left.set_parent(node)
                right.set_parent(node)
                return node

            elif lst[0] == '|'  or lst[0] == 'or':
                if lst[1] == None or lst[2] == None:
                    raise ValueError("Or of non-existent literal")
                left = Node.from_list(lst[1], is_monotone)
                right = Node.from_list(lst[2], is_monotone)
                node = OrNode(left, right)
                left.set_parent(node)
                right.set_parent(node)
                return node

        elif len(lst) == 1:
            return LiteralNode(lst[0])
        else:
            raise ValueError("Invalid input formula")

class AndNode(Node):
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

class OrNode(Node):
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

class NotNode(Node):
    def __init__(self, value) -> None:
        super().__init__(NodeType.Not, "~", value, None);

    def __repr__(self) -> str:
        left = None
        if self.left().ty() == NodeType.Literal:
            left = f"{self.left()}"
        else:
            left = f"({self.left()})"

        return f"~{left}"

class LiteralNode(Node):
    RESERVED = ['&', 'and', '|' , "or", "not" , "~"]

    def __init__(self, name: str) -> None:
        if name in LiteralNode.RESERVED:
            raise ValueError(f"Invalid name of literal: {name}")
        super().__init__(NodeType.Literal, name, None, None)

    def __repr__(self) -> str:
        return f"{self.name()}"

if __name__ == '__main__':
    def main():
        f = "a&((b|c)^a->c)<->b"
        tree = Node.from_formula(f)
        print(f"{tree}")

        try:
            f = "(a & b) | (b & ~c)"
            tree = Node.from_formula(f, is_monotone=True)
            print("Monotonicity check failed");
        except ValueError:
            pass

        g = "(a & b) | (b & c) | (c & a)"
        tree = Node.from_formula(g, is_monotone=True)
        print(f"{tree}")
    main()