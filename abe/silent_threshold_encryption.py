from abe import BNCurve, lagrange_basis
from sage.rings.all import *;
from sage.schemes.all import *;
from hashlib import sha256
from sage.schemes.elliptic_curves.ell_point import EllipticCurvePoint

import sys

from bn_curve_gen import BNCurve;



class BLSSign:
    def __init__(self, curve : BNCurve) -> None:
        self.curve = curve
        self.secret = None
        self.public = None

    def keygen(self):
        self.secret = self.curve.scalar_field().random_element()
        self.public = self.secret * self.curve.g1()
        return self.public

    def sign(self, message : bytes | str):
        if self.secret == None:
            raise ValueError("Key does not contain a secret")
        hashed_point = self.curve.hash2g0(message)
        return self.secret*hashed_point

    def verify(self, message: bytes | str, sig : EllipticCurvePoint):
        if self.verify == None:
            raise ValueError("Key does not contain a public key")
        hashed_point = self.curve.hash2g0(message)
        left_pairing = self.curve.pair(hashed_point, self.public)
        right_pairing = self.curve.pair(sig, self.curve.g1())

        return left_pairing == right_pairing

    @staticmethod
    def run_sample_test():
        bls_signer = BLSSign();
        pub_key = bls_signer.keygen();
        msg = b"This is a test of wit and not of brawns"
        sig = bls_signer.sign(msg)
        verif = bls_signer.verify(msg, sig)
        assert verif, "Signature verification failed"


class GLPW2024:
    def __init__(self, curve : BNCurve) -> None:
        self.curve = curve
        self.bls = BLSSign(curve=curve)

    def keygen(self):
        self.pk = self.bls.keygen()
        return self.pk

    def encrypt(self, public_key : EllipticCurvePoint, message: FiniteField, tag : bytes):
        r = self.curve.scalar_field().random_element()
        h = self.curve.hash2g0(tag)
        pair = self.curve.pair(r*h, public_key)
        c1 = r*self.curve.g1()
        c2 = message*pair
        return (c1, c2)

    def decrypt(self, ct, tag : bytes):
        h = self.curve.hash2g0(tag)
        factor = self.curve.pair(h, ct[0])**self.bls.secret
        m = ct[1]/ factor
        return m

    @staticmethod
    def run_sample_test(bn_curve : BNCurve):
        tag = b"Admin"
        cryptor = GLPW2024(bn_curve)
        pk = cryptor.keygen()
        r = cryptor.curve.scalar_field().random_element()
        message = cryptor.curve.gt()**r
        ct = cryptor.encrypt(pk, message, tag)
        m = cryptor.decrypt(ct, tag=tag)
        assert m == message, "Failed to decrypt correctly"


if __name__ == '__main__':
    # Generated using curve_32()
    BASE_FIELD_PRIME=4675038223
    CURVE_ORDER=4674969529
    CURVE_B=29
    CURVE_Y=1270807500

    BN_CURVE_32 = BNCurve(BASE_FIELD_PRIME, CURVE_ORDER, CURVE_B, CURVE_Y)


    def main():
        GLPW2024.run_sample_test(BN_CURVE_32)
        BLSSign.run_sample_test(BN_CURVE_32)

    main()
