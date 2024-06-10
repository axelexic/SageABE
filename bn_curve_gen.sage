#!/usr/bin/env sage

#
# Generate an optimal prime order pairings friendly curve. Taken from:
# https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/pfcpo.pdf
#

from sage.all import *

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

class BNCurveData:
    def __init__(self, p, n, B, y) -> None:
        self._Fp = GF(p)
        F = self._Fp['H']; H = F.gen();
        self._Fp2 = self._Fp.extension(modulus = H**2 + 1, name="L")
        self._Fp12  = self._Fp2.extension(6, 'T')
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

    def curve(self):
        return self._curve

    def generators(self):
        return (self._g0, self._g1)

    def order(self):
        return self._order

    def g0(self):
        return self._g0

    def g1(self):
        return self._g1

    def base_field(self):
        return self._Fp

    def extension_field(self):
        return self._Fp12

    def pair(self, m, n):
        P = m * self._g0
        Q = n * self._g1
        return P.weil_pair(Q, self._order)

    def __repr__(self) -> str:
        return f"{{Curve: {self._curve}, generators: {self.generators()} }}"


def bn_curve_gen(curve_order_in_bits) -> BNCurveData:
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
            return BNCurveData(p, n, b, y)

print (bn_curve_gen(32))