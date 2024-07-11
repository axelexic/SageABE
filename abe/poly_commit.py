#
# Computes different polynomial commitments
#

from abe import BNCurve
from sage.rings.all import *;
from sage.schemes.all import *;
from hashlib import sha256

class PolyCommit:
    def __init__(self):
        """
        Create a polynomial commitment for poly p(x)
        """
        pass


    def commit_poly(self, polynomial : PolynomialRing):
        """
        Given a polynomial p(x) generate its commitment value
        """
        raise NotImplemented

    def eval_with_proof(self, x_val : FiniteField):
        """
        Given a value `x_val` open the value of p(x_val) and generate a
        proof that is the right vlaue
        """
        raise NotImplemented

    def verify(self, commitment, x_val, y_val, proof):
        """
        Given a value `x_val` and the claim that `y_val = p(x_val)`,
        then verify that the claim is correct using the proof
        """
        raise NotImplemented

class CoefficientCommitment(PolyCommit):
    """
    Commit to the coefficient of the polynomial directly
    """
    def __init__(self, group : BNCurve, poly : PolynomialRing):
        super().__init__()
        self._curve = group
        self._poly = poly

    def poly(self):
        return self._poly

    def group_gen(self):
        (x,y,z) = self._curve.g0()
        return self._curve.curve()([x,y,z])

    def scalar_field(self):
        return self._curve.scalar_field()

    def commit_poly(self):
        coefs = list(self.poly())
        g = self.group_gen()
        F = self.scalar_field()
        return [F(i)*g for i in coefs]

    def eval_with_proof(self, x_val : FiniteField):
        val = self.poly()(x_val)
        # Just returning the value is enough
        return val

    def verify(self, commitment, x_val, y_val, proof):
        g = self.group_gen()
        F = self.scalar_field()
        x = F(x_val)
        # This is the value of g^(p(x))
        found = F(y_val)*g
        # Point at infinity
        expected = self._curve.curve()([0,1,0]);

        for (i,c) in enumerate(commitment):
            factor =  (x**i)*c
            expected = expected + factor

        # expected is the value calculated from commited coefficients

        return expected == found

    @staticmethod
    def run_sample_test(curve: BNCurve, poly : PolynomialRing):
        cc = CoefficientCommitment(curve, poly)
        commit = cc.commit_poly()
        x_val = cc.scalar_field().random_element()
        y_val = cc.eval_with_proof(x_val)
        verif = cc.verify(commit, x_val, y_val, None)

        assert verif, "Polynomial commitment failed"


class KZGCommit(PolyCommit):
    """
    Generate KZG commitment using M CRS coefficient
    """
    def __init__(self, group : BNCurve, M: int, poly : PolynomialRing):
        super().__init__()
        self._curve = group
        self._poly = poly
        trapdoor = group.scalar_field().random_element()
        g0 = self._curve.g0()
        g1 = self._curve.g1()
        powers = [(trapdoor**i) for i in range(M)]
        self._crs_0 = [p*g0 for p in powers]
        self._crs_1 = [p*g1 for p in powers]

    def crs_0(self):
        return self._crs_0

    def crs_1(self):
        return self._crs_1

    def poly(self):
        return self._poly

    def scalar_field(self):
        return self._curve.scalar_field()

    @staticmethod
    def do_commit_on_crs(crs, poly):
        commitment = None
        for (i,coef) in enumerate(poly):
            entry = coef*crs[i]
            if commitment:
                commitment = commitment + entry
            else:
                commitment = entry

        return commitment


    def commit_poly(self):
        return KZGCommit.do_commit_on_crs(self.crs_0(), self.poly())

    def eval_with_proof(self, x_val : FiniteField):
        X = self.poly().variables()[0]
        val = self.poly()(x_val)
        poly_y = (self.poly() - val)
        factor = (X - x_val)
        assert (poly_y % factor) == 0, "Bug in code"
        poly_g = poly_y // factor
        proof = KZGCommit.do_commit_on_crs(self.crs_0(), poly_g)
        return (val, proof)

    def verify(self, commitment, x_val, y_val, proof):
        # Compute (X-x_val) commitment on G2 group
        linear_commit = KZGCommit.do_commit_on_crs(self.crs_1(), [-x_val, 1])
        poly_minus_val = commitment - y_val*self.crs_0()[0]
        lhs = self._curve.pair(proof, linear_commit)
        rhs = self._curve.pair(poly_minus_val, self.crs_1()[0])

        return lhs == rhs

    @staticmethod
    def run_sample_test(curve: BNCurve, poly: PolynomialRing):
        cc = KZGCommit(curve, 24, poly)
        commit = cc.commit_poly()
        x_val = cc.scalar_field().random_element()
        y_val, proof = cc.eval_with_proof(x_val)
        verif = cc.verify(commit, x_val, y_val, proof)

        assert verif, "KZG commitment verification failed"


if __name__ == '__main__':
    # from .bn_curve_gen import BNCurve
    # Generated using curve_32()
    BASE_FIELD_PRIME=4675038223
    CURVE_ORDER=4674969529
    CURVE_B=29
    CURVE_Y=1270807500

    BN_CURVE_32 = BNCurve(BASE_FIELD_PRIME, CURVE_ORDER, CURVE_B, CURVE_Y)


    def main():
        Fx = PolynomialRing(BN_CURVE_32.scalar_field(), "W")
        w = Fx.gen()
        poly = 1
        for _ in range(10):
            v = Fx.random_element()
            if v == 0:
                continue
            poly = poly*v

        KZGCommit.run_sample_test(BN_CURVE_32, poly)
        CoefficientCommitment.run_sample_test(BN_CURVE_32, poly)

    main()


