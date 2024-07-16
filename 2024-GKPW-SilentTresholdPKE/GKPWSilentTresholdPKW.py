#
# This file implements the ePrint 2024/263 version of
# "Threshold Encryption with Silent Setup" by
#       Garg, Kolonelos, Policharla, and Wang
# https://eprint.iacr.org/2024/263.pdf
#
#

from abe import BNCurve, lagrange_basis
from sage.rings.all import *;
from sage.rings.finite_rings.finite_field_base import FiniteField as FqInst
from sage.rings.finite_rings.finite_field_constructor import FiniteFieldFactory
from sage.schemes.all import *;
from sage.schemes.elliptic_curves.ell_point import EllipticCurvePoint
from hashlib import sha256

def random_non_zero(ff : FiniteFieldFactory) -> FqInst:
    while True:
        s = ff.random_element()
        if s != 0:
            return s


# def Li(i : int, crs : list[EllipticCurvePoint], at_tau : bool):
#     field = crs[0].curve().base_ring()
#     M = len(crs) - 1
#     xes = [i for i in range(M)]

#     if at_tau:
#         basis = lagrange_basis(field, xes, None)
#         coefficients = list(basis)
#         # CRS starts from t^1, t^2, etc., so


#     else:
#         basis = lagrange_basis(field, xes, 0)

class GKPWRegistrar:
    """
    This class acts as the registrar/curator of keys. The constructor
    acts as the setup algorithm.
    """
    def __init__(self, curve : BNCurve, max_users : int) -> None:
        """
        `curve` is the BNCurve pairings friendly curve and `max_users` is
        the maximum number of user's that can register in this system.
        """
        self._curve = curve
        self._max_users = max_users

        Fp = curve.scalar_field()
        tau = random_non_zero(Fp)
        tau_powers =  [
            tau ** i for i in range(1, max_users+2)
        ]

        crs0 = [ x * curve.g0() for x in tau_powers ]
        crs1 = [ x * curve.g1() for x in tau_powers ]

        self._crs = { 0 : crs0, 1: crs1 }

    def crs(self):
        return self._crs

    def curve(self):
        return self._curve

    def max_users(self):
        return self._max_users


class GKPWUser:
    """
    This is the end-user who manages its own keys
    """
    def __init__(self,
                 curve : BNCurve,
                 crs : dict[int, EllipticCurvePoint],
                 user_id : int) -> None:
        assert crs[0] and crs[1], "Invalid CRS data"
        assert len(crs[0]) == len(crs[1]), "Invalid CRS data"
        self._crs = crs
        self._user_id = user_id
        self._max_users = len(crs[0]) - 1
        self._curve = curve
        self._sk = None
        self._pk = None

    def pk(self):
        return self._pk

    def curve(self):
        return self._curve

    def max_users(self):
        return self._max_users

    def crs0(self):
        return self.crs[0]

    def crs1(self):
        return self.crs[1]

    def keygen(self):
        """
        This method corresponds to keygen method in the scheme
        """
        self._sk = random_non_zero(self.curve())
        self._pk = self._sk*self.curve().g0()
        return self._pk

    def hintGen(self):
        pass

class BLSSign:
    def __init__(self, curve : BNCurve) -> None:
        self.curve = curve
        self.secret = None
        self.public = None

    @staticmethod
    def from_pk(curve: BNCurve, vk: EllipticCurvePoint | list[EllipticCurvePoint]):
        this = BLSSign(curve=curve)

        if isinstance(vk, (list,)):
            this.public = 0*curve.g1()
            for vki in vk:
                this.public += vki
        else:
            this.public = vk

        return this

    def keygen(self) -> EllipticCurvePoint:
        """
        Generate a BLS private/public key-pair. The Public-Key is in the
        Group G2
        """
        self.secret = self.curve.scalar_field().random_element()
        self.public = self.secret * self.curve.g1()
        return self.public

    def sign(self, message : bytes | str) -> EllipticCurvePoint:
        """
        Sign a message. The signature is in group G1.
        """
        if self.secret == None:
            raise ValueError("Key does not contain a secret")
        hashed_point = self.curve.hash2g0(message)
        return self.secret*hashed_point

    def verify(self, message: bytes | str, sig : EllipticCurvePoint) -> bool:
        if self.verify == None:
            raise ValueError("Key does not contain a public key")

        hashed_point = self.curve.hash2g0(message)
        right_pairing = self.curve.pair(sig, self.curve.g1())
        left_pairing = self.curve.pair(hashed_point, self.public)
        return left_pairing == right_pairing

    @staticmethod
    def aggregate_sigs(curve : BNCurve,
                  message: bytes|str,
                  signatures : list[EllipticCurvePoint],
                  verification_keys: list[EllipticCurvePoint]) -> EllipticCurvePoint:
        """
        Trivial signature aggregation that's insecure to EU-CMA (**DONT
        USE IN REAL WORLD**). The Signatures are first verified and then
        aggregated.
        """

        aggr_sig = 0*curve.g0()

        for (sig,vk) in zip(signatures, verification_keys):
            pubkey = BLSSign.from_pk(curve, vk)
            if pubkey.verify(message, sig):
                aggr_sig = aggr_sig + sig
            else:
                raise ValueError("Signature verification failed. Signature cannot be aggregated")
        return aggr_sig

    @staticmethod
    def single_signature_test(curve : BNCurve):
        bls_signer = BLSSign(curve);
        pub_key = bls_signer.keygen();
        msg = b"This is a test of wit and not of brawns"
        sig = bls_signer.sign(msg)
        verif = bls_signer.verify(msg, sig)
        assert verif, "Signature verification failed"

    @staticmethod
    def multiple_signature_test(curve : BNCurve):
        count = 10
        sigs = list()
        verifs = list()
        msg = b"This is a test of wit and not of brawns"

        for i in range(count):
            bls_signer = BLSSign(curve)
            vk = bls_signer.keygen()
            sig = bls_signer.sign(msg)
            sigs.append(sig)
            verifs.append(vk)

        aggr_sig = BLSSign.aggregate_sigs(curve, msg, sigs, verifs)
        aggr_pk = BLSSign.from_pk(curve, verifs)

        assert aggr_pk.verify(msg, aggr_sig), "Signature verification failed"


class PKEFromSignature:
    """
    Tries to use raw BLS signatures as an encryption scheme.
    """
    def __init__(self, curve : BNCurve) -> None:
        self.curve = curve
        self.bls = BLSSign(curve=curve)

    def keygen(self):
        self.pk = self.bls.keygen()
        return self.pk

    def encrypt(self, public_key : EllipticCurvePoint, message: FqInst, tag : bytes):
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
        cryptor = PKEFromSignature(bn_curve)
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
        BLSSign.single_signature_test(BN_CURVE_32)
        BLSSign.multiple_signature_test(BN_CURVE_32)
        PKEFromSignature.run_sample_test(BN_CURVE_32)


    main()
