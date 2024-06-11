from abe import BNCurve, lagrange_basis
from sage.rings.all import *;
from sage.schemes.all import *;
import sys

# Generated using curve_32()
BASE_FIELD_PRIME=4675038223
CURVE_ORDER=4674969529
CURVE_B=29
CURVE_Y=1270807500

BN_CURVE_32 = BNCurve(BASE_FIELD_PRIME, CURVE_ORDER, CURVE_B, CURVE_Y)

class FuzzyIBE:
    def __init__(self, pf_curve : BNCurve, attributes) -> None:
        self._curve = pf_curve
        self._attributes = attributes
        self._lagrange_field = pf_curve.scalar_field()
        self._poly = PolynomialRing(self._lagrange_field, name="W")
        self._y = self._lagrange_field.random_element()
        self._y_pub = self._curve.pair(1, self._y)
        self._lagrange_basis = lagrange_basis(self._curve.scalar_field(), attributes, 0)

        self._priv_shares = dict()
        self._pub_shares = dict()

        self._pub_shares["Y"] = self._y_pub;

        for i in self._attributes:
            t = self._lagrange_field.random_element()
            T = t*self.g0()
            self._priv_shares[i] = t
            self._pub_shares[i] = T

    def g0(self):
        return self._curve.g0()

    def g1(self):
        return self._curve.g1()

    def msk_params(self):
        return self._pub_shares

    def generate_key(self, identity, d_threshold):
        if d_threshold - 1 >= len(identity) or d_threshold < 1:
            raise ValueError("Threshold values must be less than identities count and greater than 1")

        x_var = self._poly.gen()
        poly = 0

        for i in range(d_threshold - 1):
            poly = x_var * poly + self._lagrange_field.random_element()

        poly = x_var*poly + self._y
        user_shares = dict()

        for ident in identity:
            val = poly(ident)
            t = self._priv_shares[ident]
            r = val / t
            user_shares[ident] = r*self.g1()

        return user_shares

    def encrypt(self, pubkey, attributes, message):
        s = self._curve.scalar_field().random_element()
        M = self._curve.extension_field()(message)
        Y = pubkey["Y"]
        Eprime = M*(Y**s)
        # print(f"Eprime := {Y**s}")
        Eshares = dict()

        for attrs in attributes:
            Yi = s*pubkey[attrs]
            Eshares[attrs] = Yi

        return (attributes, Eprime, Eshares)

    def decrypt(self, ct, sk):
        (ct_attrs, Eprime, Eshares) = ct
        common_attrs = self._curve.extension_field()(1)

        for k in sk.keys():
            if k in ct_attrs:
                lbasis = self._lagrange_basis[k]
                pair = self._curve.pair(sk[k], Eshares[k])
                common_attrs = common_attrs*(pair**lbasis)

        # print(f"Blinding: {common_attrs}")
        m = Eprime / common_attrs
        return m


def main(args):
    fibe = FuzzyIBE(BN_CURVE_32, [1,2,3,4,5,6])
    pubkey = fibe.msk_params()
    sk = fibe.generate_key([3,5,2,6], 2)
    ct = fibe.encrypt(pubkey, [3,5,2,6], 39)
    # print(ct)
    m = fibe.decrypt(ct, sk)
    # print(m)

if __name__=='__main__':
    main(sys.argv)