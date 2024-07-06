#!/usr/bin/env sage

#
# Generate an optimal prime order pairings friendly curve. Taken from:
# https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/pfcpo.pdf
#

from sage.rings.all import *
from sage.rings.finite_rings.all import GF
from sage.schemes.all import EllipticCurve
from sage.arith.misc import kronecker_symbol
from sage.schemes.elliptic_curves.ell_point import EllipticCurvePoint_field
from hashlib import sha256

def find_min_x(m, func):
    x = 2**(m//4)
    while True:
        val = func(-1*x)
        bit_len = val.bit_length()
        if bit_len == m:
            return x
        elif bit_len > m:
            x = 3*x//4
        else:
            x = 3*x//2

class BNCurve:
    def __init__(self, p, n, B, y) -> None:
        # print(f"p = {p}, n = {n}, B = {B}, y = {y}")
        p = Integer(p)
        n = Integer(n)
        B = Integer(B)
        y = Integer(y)
        assert p.is_prime()
        assert n.is_prime()
        assert B != 0

        self._Fp = GF(p)
        self._Fp2 = self._Fp.extension(2, name="L")
        self._Fp12  = self._Fp2.extension(6, name='T')
        self._order = n
        self._curve = EllipticCurve(
            self._Fp, [0, B]
        )
        self._curve2 = self._curve.change_ring(self._Fp2)
        self._curve12 = self._curve2.change_ring(self._Fp12)

        self._g0 = self._curve12([1, y,1])

        assert self._g0.order() == n

        # Find the other component of the curve
        g1,g2 = self._curve12.gens()
        assert g1.order() % self._order == 0
        assert g2.order() % self._order == 0

        g1_small = (g1.order() // n)*g1
        g2_small = (g2.order() // n)*g2

        assert g1_small.order()  == n
        assert g2_small.order()  == n

        if g1_small.weil_pairing(self._g0, n) == 1:
            self._g1 = g2_small
        else:
            self._g1 = g1_small

        self._gt = self._g0.weil_pairing(self._g1, self._order)

    def curve(self):
        return self._curve

    def curve2(self):
        return self._curve2

    def curve12(self):
        return self._curve12

    def generators(self):
        return (self.g0(), self.g1(), self.gt())

    def order(self):
        return self._order

    def g0(self):
        return self._g0

    def g1(self):
        return self._g1

    def gt(self):
        return self._gt

    def base_field(self):
        return self._Fp

    def extension_field(self):
        return self._Fp12

    def scalar_field(self):
        return GF(self._order)

    def pair(self, m, n):
        if isinstance(m, (EllipticCurvePoint_field)):
            P = m
        else:
            P = m * self._g0

        if isinstance(n, (EllipticCurvePoint_field)):
            Q = n
        else:
            Q = n * self._g1

        return P.weil_pairing(Q, self._order)

    def _hash_input_encode(self, polyval):
        if isinstance(polyval, (str)):
            val = polyval.encode('utf-8')
        elif isinstance(polyval, (bytes)):
            val = polyval
        elif isinstance(polyval, (int, Integer)):
            len = (polyval.bit_length() + 7)//8
            val = polyval.to_bytes(len)
        else:
            raise ValueError(f"hashing data of type {type(polyval)} not supported")

        h = sha256(val).digest()

        return int.from_bytes(h)

    def hash2g0(self, polyval):
        val = self._hash_input_encode(polyval)
        while True:
            p = self.scalar_field()(val)*self.g0()
            if p == self.curve()([0, 1, 0]):
                val = self._hash_input_encode(val)
            else:
                return p

    def hash2g1(self, polyval):
        val = self._hash_input_encode(polyval)
        while True:
            p = self.scalar_field()(val)*self.g1()
            if p == self.curve12()([0, 1, 0]):
                val = self._hash_input_encode(val)
            else:
                return p

    def __repr__(self) -> str:
        return f"{{Curve: {self._curve12}, generators: {self.generators()} }}"


def bn_curve_gen(curve_order_in_bits) -> BNCurve:
    Z = ZZ['H']
    var_x = Z.gen()
    poly_p = 36*(var_x**4) + 36*(var_x**3) + 24*(var_x**2) + 6*var_x + 1

    x = find_min_x(curve_order_in_bits, poly_p)

    p = None
    n = None
    b = 0

    while True:
        t = 6*(x**2) + 1
        p = poly_p(-1*x)
        n = p + 1 - t

        if p.is_prime() and n.is_prime():
            break

        p = poly_p(x)
        n = p + 1 - t

        if p.is_prime() and n.is_prime():
            break

        if p.bit_length() > curve_order_in_bits + 4:
            raise ValueError("Could not find suitable parameters")
        else:
            x = x + 1


    Fp = GF(p)

    while True:
        while True:
            b = b + 1
            if kronecker_symbol(b+1, p) == 1:
                break
        B = Fp(b+1)
        E = EllipticCurve(Fp, [0, b])
        y = B.sqrt(extend=False)
        G = E([1,y,1])
        if n*G == E([0,1,0]):
            return BNCurve(p, n, b, y)


CURVE32 = None

def curve_32() -> BNCurve:
    global CURVE32

    if CURVE32 is None:
        CURVE32 = bn_curve_gen(32)

    return CURVE32


if __name__=='__main__':
    def test_hash():
        c = curve_32()
        g1 = c.hash2g0("this is a test")
        g2 = c.hash2g0(b"this is a test")
        g3 = c.hash2g0(int.from_bytes(b"this is a test"))
        assert g1 == g2
        assert g1 == g3

        h1 = c.hash2g1("this is a test")
        h2 = c.hash2g1(b"this is a test")
        h3 = c.hash2g1(int.from_bytes(b"this is a test"))
        assert h1 == h2
        assert h3 == h1

    def main():
        test_hash()

    main()