from abe import  BNCurve
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
        self._priv_shares = dict()
        self._pub_shares = dict()

        for i in self._attributes:
            t = self._lagrange_field.random_element()
            T = t*self._curve.g0()
            self._priv_shares[i] = t
            self._pub_shares[i] = T

    def msk_params(self):
        self._pub_shares

    def generate_key(self, identity, d_threshold):
        if d_threshold - 1 >= len(identity) or d_threshold < 2:
            raise ValueError("Threshold values must be less than identities count and greater than 1")

        result = dict;
        x_var = self._poly.gen()
        poly = self._poly(self._lagrange_field.random_element());


        for i in range(d_threshold - 1):
            poly = x_var * poly + self._lagrange_field.random_element()

        poly = x_var*poly + self._y
        print(poly)


def main(args):
    fibe = FuzzyIBE(BN_CURVE_32, [1,2,3,4,5,6]);
    fibe.generate_key([3,5,2], 2)

if __name__=='__main__':
    main(sys.argv)