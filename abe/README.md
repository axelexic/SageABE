# Introduction

This package contains some utility functions for use in ABE schemes.
Different files contain different functions. Contents of each files are listed below. (Please update this readme if you add something new this package.)

## Barreto-Naehrig Curve Gen

Given the number of bits of the characteristic field, the function [`bn_curve_gen`](./bn_curve_gen.py) generates a random [Barreto-Naehrig Curve](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/pfcpo.pdf) with roughly those number of bits. These are prime-order non-supersingular curves with embedding degree 12. Among non-supersingular curves, these are Type-3 asymmetric curves where there's no known _efficiently computable_ isomorphism between the two Elliptic Curve Groups.

While there are several standardized BN Curves, they are all in large characteristics. The rationale for generating new BN curves is so that we can directly compute the discrete log in these curves for understanding the security reduction of the ABE scheme.

**FOR REAL WORLD DEPLOYMENT USE LARGE ORDER CURVES**

### Security Reduction Friendly Characteristics

In many ABE schemes (especially with selective security), one tries to break the BDDH assumption of other $k$-Lin type assumption by directly constructing an instance of the protocol using algebraic objects. In order to better understand how well these reductions work, it's sometime useful to construct an Adversary in code and give it an instance of the problem where it can easily solve the discrete-log problem. This is the primary reason for these curves. Again, don't use small order curves where ECDLP is easy for real-world deployments.

## Lagrange Basis

[lagrange_interpolate](./lagrange_interpolate.py) file contains a
function for computing the lagrangian basis of polynomial given a set of
$x$ coordinates.

The method in this file is used by secret sharing schemes, especially
Shamir Secret sharing where its used to reconstruct the polynomial.

## Polynomial Commitments

[poly_commit](./poly_commit.py) contains different polynomial commitment
schemes, namely, Coefficient based commitment (which is not succinct) as
well as KZG Commitment

## Secret Sharing

[secret_sharing](./secret_sharing.py) implements different SecretSharing shemes, in particular:

- **Shamir Secret Sharing**: Implements Shamir's secret sharing scheme
  in both prime field as well as extension fields.

- **Benaloh Leichter Crypto 1988 Scheme**: This scheme uses the monotone
  boolean formula to support monotone access structure. While the
  original Benaloh/Leichter scheme supports threshold gates, this
  implementation only support monotone boolean formula (i.e., only
  binary AND and OR gates). The syntax of the boolean function is based
  on SageMath's
  [https://doc.sagemath.org/html/en/reference/logic/sage/logic/boolformula.html](Boolean
  Formula) module.

