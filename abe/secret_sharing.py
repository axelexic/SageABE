#
# Implementation of different types of secret sharing schemes
#

from sage.rings.finite_rings.all import *
from sage.rings.polynomial.all import PolynomialRing
from sage.rings.finite_rings.finite_field_constructor import FiniteFieldFactory
from sage.rings.finite_rings.finite_field_base import FiniteField as FiniteFieldGeneric;
from abe import lagrange_basis, Formula, NodeType
from typing import TypeAlias, Any

UserId : TypeAlias = int | bytes

class SecretShare:
    """
    Basic interface to secret sharing scheme
    """
    def __init__(self, universe : set[UserId] | None, access_structure : Any) -> None:
        """
        Intialize (a.k.a setup) a secret sharing scheme for a given
        universe of participants. The access structure defines how the
        secrets are to be shared.
        """
        self._universe = universe
        self._access_structure = access_structure
        pass

    def universe(self):
        return self._universe

    def access_structure(self):
        return self._access_structure

    def create_share(self, identity : UserId) -> bytes:
        """
        Create shares of the `secret` for the given `identity.` The
        `identity` can be either an index or bytes to support hash of
        names.
        """
        raise NotImplemented

    def recombine(self, shares : dict[UserId, Any]) -> bytes:
        """
        Recombine shares
        """
        raise NotImplemented


class ShamirSecretSharing(SecretShare):
    """
    Shamir's t-out-of-n threshold secret sharing scheme
    """

    @staticmethod
    def random_field_element(ff : FiniteFieldFactory):
        deg = ff.degree()
        result = ff(0)

        if deg == 1:
            result = ff.random_element()
        else :
            gen = ff.gen()
            for _ in range(deg):
                result = result*gen + ff.base_ring().random_element()
        return result

    @staticmethod
    def serialize_field_element(ff):
        return ff.to_bytes()

    @staticmethod
    def deserialize_field_element(ff, data : bytes | int):
        if isinstance(data, (bytes,)):
            return ff.from_bytes(data)
        else:
            return ff(data)

    @staticmethod
    def random_poly(poly_ring : PolynomialRing, degree: int):
        field = poly_ring.base_ring()
        x = poly_ring.gen()
        result = poly_ring(0)

        if degree < 0:
            raise ValueError("Polynomials must have positive degree")

        if degree == 0:
            return ShamirSecretSharing.random_field_element(field)

        for _ in range(degree):
            result = result*x + ShamirSecretSharing.random_field_element(field)

        return result


    def __init__(self, field_secret : bytes | FiniteFieldGeneric, field : FiniteFieldFactory,  threshold: int) -> None:
        super().__init__(None, threshold)

        if threshold < 0:
            raise ValueError("No secret sharing with threshold less than 2 possible?")

        self._field = field
        self._degree = field.degree() # Extension field to cover GF(2^l) case
        self._poly_ring = PolynomialRing(self._field, "X")

        if isinstance(field_secret, (bytes)):
            self._secret = field.from_bytes(field_secret)
        else:
            self._secret = field_secret

        r_poly = None

        if threshold == 1:
            self._poly = self._poly_ring(self._secret)
        else:
            r_poly = ShamirSecretSharing.random_poly(self._poly_ring, threshold-2)
            self._poly = r_poly * self._poly_ring.gen() + self._poly_ring(self._secret)

    def secret(self):
        return self._secret

    def threshold(self):
        return self.access_structure()

    def poly(self):
        return self._poly

    def poly_eval(self, value):
        return self._poly(value)

    def field(self):
        return self._field

    def create_share(self, identity: UserId) -> bytes:
        x_cord = None
        if isinstance(identity, (bytes)):
            x_cord = self.field().from_bytes(identity)
        else:
            x_cord = self.field()(identity)

        if x_cord == 0:
            raise ValueError("Nah! Not today Satan")

        return self.poly_eval(x_cord).to_bytes()

    def recombine(self, shares: dict[UserId, Any]) -> bytes :
        unique_shares = list(map(
            lambda b : ShamirSecretSharing.deserialize_field_element(self.field(), b),
            set(shares)
        ))

        if len(unique_shares) < self.threshold():
            raise ValueError("Insufficient number of shares")

        bases = lagrange_basis(self.field(), unique_shares, self.field()(0))

        result = self.field()(0)

        for k,v in bases.items():
            s = None
            try:
                s = shares[k]
            except:
                entry = k.to_bytes()
                s = shares[entry]

            if isinstance(s, (bytes)):
                s = self.field().from_bytes(s)
            result += s*v

        return result.to_bytes()

    @staticmethod
    def run_test_cases(base_field : FiniteFieldFactory, th : int):
        secret = ShamirSecretSharing.random_field_element(base_field)
        secret = ShamirSecretSharing.serialize_field_element(secret)
        sss = ShamirSecretSharing(secret, base_field, th)
        shares = dict()

        for _ in range(2*th + 5):
            index = ShamirSecretSharing.random_field_element(base_field).to_bytes()
            share = sss.create_share(index)
            shares[index] = share

        rc = sss.recombine(shares=shares)
        assert secret == rc, "Share recombination failed"

class BenalohLeichterCrypto1988(SecretShare):
    """
    Scheme by Benaloh and Leichter from Crypto 1988
    https://link.springer.com/chapter/10.1007/0-387-34799-2_3

    This scheme can support any monotone threshold circuit, however,
    it's implemented only for monotone boolean formula. Basic idea of
    the scheme is that at each binary operator node in the binary tree
    (i.e., non-leaf nodes), the scheme uses uses 1 out of 2, or 2 out of
    2 Shamir Secret Sharing to achieve arbitrary monotone access
    structures. The 1 out of 2 threshold shares are for OR gates, while
    the 2 out of 2 is for AND gate. One can easily extend this code to
    allow higher treshold gates.
    """

    @staticmethod
    def do_secret_share(node : Formula, secret: bytes | FiniteFieldGeneric, index :int, field : FiniteFieldFactory):
        """
        Given a boolean formula tree, recursively creates the shares in
        the tree. Since the same literal in the formula can appear at
        multiple places, for example in the formula `(a & b) | (b & c) |
        (a & c)` the literal "a" appears in two different places.
        However, the two different occurrences of "a" have different
        positions in the tree, and each occurrence of "a" requires a
        unique value.

        In order to support multiple occurrence of the same literal,
        each node in the tree is also given a unique numeric identifier
        called `label` and each label gets its own share of the secret.
        When doing reconstruction, one should only send out those label
        values that are needed, not all labels. (This is a major
        weakness of this scheme as users make lots of mistakes with
        this.)
        """
        if index < 1:
            raise ValueError("Node index must be non-zero")

        if node.ty() == NodeType.Not:
            raise ValueError("Only non-monotone formulae are supported")

        shares = None

        if node.ty() == NodeType.And:
            shares = ShamirSecretSharing(secret, field, 2)
        else:
            shares = ShamirSecretSharing(secret, field, 1)

        node.set_content(shares)
        node.set_label(index)

        if node.ty() == NodeType.Literal:
            return

        left_index = 2*index
        right_index = 2*index + 1

        left_secret = shares.create_share(left_index)
        right_secret = shares.create_share(right_index)

        BenalohLeichterCrypto1988.do_secret_share(node.left(), left_secret, left_index, field)

        BenalohLeichterCrypto1988.do_secret_share(node.right(), right_secret, right_index, field)


    def __init__(self, field_secret : bytes, access_structure: str | Formula, field : FiniteFieldFactory) -> None:
        """
        :param bytes field_secreet: The secret that should be shared

        :param str   access_structure: A monotone boolean formula that
            should be treated as the access structure.

        :param FiniteFieldFactory field: The field over which the secret
            sharing should work. For production systems, it should be at
            least the size of the security parameter.
        """
        if isinstance(access_structure, str):
            access_structure = Formula.from_formula(access_structure, is_monotone=True)

        universe = set(map(
            lambda v : v.name(),
            access_structure.literals()
        ))

        super().__init__(universe, access_structure)
        BenalohLeichterCrypto1988.do_secret_share(
            node=self.access_structure(),
            secret=field_secret,
            index=1,
            field=field
        )

    def create_share(self, identity : UserId):
        """
        Given an identity, which should be a literal in the boolean
        formula, it reutrns all the shares of all secrets corresponding
        to different labels. To see which labels are assigned to which
        nodes in the access structure, look at the string representation
        of this object.

        :param str identity: Literal whose shares are being request.
            Returns a dictionary of secret shares for each label.
        """
        universe = self.universe()
        if not isinstance(identity, (str)):
            raise ValueError("Shares can only be created for literals in the boolean formula")

        if not identity in universe:
            raise ValueError(f"Identity {identity} not a valid literal")

        literals = self.access_structure().literals()
        shares = dict()

        for literal in literals:
            if literal.name() == identity:
                entry = literal.content()
                label = literal.label()
                shares[label] = entry.secret().to_bytes()
        return shares

    def __repr__(self) -> str:
        return f"{self.access_structure()}"

    def recombine(self, shares: dict[UserId, dict[UserId, Any]]) -> bytes:
        """
        Tries to reconstruct the secret where the shares for each
        literal is given in a dictionary. Each value of the dictionary
        contains a list of labels corresponding to that literal.

        :param dict share: A ditionary whose keys are literals in the
            boolean formula, and whose value is again a dictionary. The
            value dictionary keys are the labels and key-shares
            corresponding to that label.

        """
        literals = self.access_structure().literals()
        working_set = dict()
        parents = set()

        for l in literals:
            if not l.name() in shares:
                continue
            share = shares[l.name()]
            key_share = share.get(l.label())

            if key_share:
                working_set[l.label()] = (l, key_share)
                parents.add(l.parent())

        #
        # The recombine logic works are follows: Given the list of
        # literals and labels by the caller, we first collect all _the
        # parents_ of those literals in a set called `parents`. Also, we
        # keep a dictionary of { label : key-share } KVP called the
        # `working_set`. The `working-set` is essentially the set of
        # key-shares of the secret that's available to the algorithm at
        # any given point.
        #
        # Then we traverse through all the `parents` and see if any
        # parent has it's children in the working set that can help it
        # create its own key-share. For an OR gate, this mean having at
        # least one child in the `working_set`; for an AND gate, both
        # the children must be in the `working_set.`
        #
        # If a parent is able to generate it's secret from its children,
        # it then puts its own parent in the parent list, and puts
        # itself into the `working_set.` This process continues until we
        # either reach the root node, in which case we return the
        # recombined secret, or there's no possibility of recombing
        # anything (i.e., the formula is unsatisfiable) and we raise an
        # error.
        #
        # The following while loop is doing exactly what's described
        # above.
        #

        while True:
            has_update = False

            for p in parents:
                left = p.left()
                right = p.right()
                left_shamir = working_set.get(left.label())
                right_shamir = working_set.get(right.label())

                entry = dict()
                shamir = p.content()

                if p.ty() == NodeType.Or and (left_shamir or right_shamir ):
                    has_update = True
                    (node, key_share) = left_shamir if left_shamir else right_shamir

                    entry[node.label()] = key_share
                    del working_set[node.label()]

                elif p.ty() == NodeType.And and left_shamir and right_shamir:
                    has_update = True
                    (left_node, left_key_share) = left_shamir
                    (right_node, right_key_share) = right_shamir
                    entry = {
                        left_node.label() : left_key_share,
                        right_node.label() : right_key_share
                    }
                    del working_set[left_node.label()]
                    del working_set[right_node.label()]
                else:
                    continue

                recombined = shamir.recombine(entry)
                expected = shamir.secret().to_bytes()
                assert expected == recombined, f"recombined shares {recombined} don't match expected share {shamir.secret()}"

                grand_parent = p.parent()

                if grand_parent == None:
                    return recombined
                else:
                    working_set[p.label()] = (p, recombined)
                    parents.add(grand_parent)
                    parents.remove(p)


            if not has_update:
                # If none of the nodes could be traversed upwards, then the tree is not satisfiable
                break

        raise ValueError("This secret share is not satisfiable")


    @staticmethod
    def run_test_cases(base_field : FiniteFieldFactory,
                       formula: str,
                       sat_nodes : list[str]):

        secret = ShamirSecretSharing.random_field_element(base_field)
        secret = ShamirSecretSharing.serialize_field_element(secret)

        bl = BenalohLeichterCrypto1988(secret, formula, base_field)

        shares = dict()

        for u in sat_nodes:
            shares[u] = bl.create_share(u)

        recon = None

        try:
            recon = bl.recombine(shares)
        except:
            pass

        return secret == recon


if __name__ == '__main__':
    def test_shamir_secret_sharing():
        ff = FiniteField(101**41)
        ShamirSecretSharing.run_test_cases(ff, 1)
        ShamirSecretSharing.run_test_cases(ff, 2)
        ShamirSecretSharing.run_test_cases(ff, 5)

    def test_benolah_secret_sharing():
        ff = FiniteField(101**41)
        formula = "(a & b) | ( b & c) | (a & c)"
        should_pass = BenalohLeichterCrypto1988.run_test_cases(ff, formula, ["b", "c"])

        assert should_pass, "Failed to successfully reconstruct secrets"

        should_pass = BenalohLeichterCrypto1988.run_test_cases(ff, formula, ["a", "c"])

        assert should_pass, "Failed to successfully reconstruct secrets"

        should_pass = BenalohLeichterCrypto1988.run_test_cases(ff, formula, ["a", "b"])

        assert should_pass, "Failed to successfully reconstruct secrets"

        for x in ["a", "b", "c"]:
            should_fail = BenalohLeichterCrypto1988.run_test_cases(ff, formula, [x])
            assert not should_fail, "Test case that should have failed, passed"

    def main():
        test_shamir_secret_sharing()
        test_benolah_secret_sharing()

    main()