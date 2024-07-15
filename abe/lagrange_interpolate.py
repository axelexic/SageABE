#
# tools for working with the lagrange basis
#
from sage.rings.polynomial.all import PolynomialRing

def lagrange_basis(field, xes, eval_at = None):
    """
    Given a set of evaluation points `xes`, computes the lagarange basis
    using those points.

    :param FiniteField field: Base field of the polynomial

    :param FiniteField list[field_element]: List of x coordinates from
        the field

    :param FiniteField eval_at: If eval_at is None, it returns an actual
        polynomial basis. On the other hand, if eval_at is non-Null, it
        evaluates the different bases at that point.
    """
    if eval_at is None:
        R = PolynomialRing(field, "H")
        H = R.gen()
    else:
        H = field(eval_at)

    basis = dict()

    for i in range(len(xes)):
        val = 1
        for j in range(len(xes)):
            if j == i: continue

            factor = (H - field(xes[j]))/field(xes[i] - xes[j])
            val = val * factor

        basis[xes[i]] = val

    return basis



if __name__ == '__main__':
    from sage.rings.finite_rings.all import GF

    def test_basis_gen():
        Fp = GF(50909)
        R = PolynomialRing(Fp, 'Y')
        Y = R.gen()

        fx = Y**3+ 13*(Y**2) + 11*Y + 4

        roots = dict()

        for i in range(100):
            x = Fp.random_element()
            while x in roots:
                x = Fp.random_element()
            roots[x] = fx(x)

        basis = lagrange_basis(Fp, list(roots.keys()))
        result = Fp(0)

        for r in roots.keys():
            result = result + roots[r]*basis[r]

        assert fx.list() == result.list()

    def test_value_gen():
        Fp = GF(50909)
        R = PolynomialRing(Fp, 'Y')
        Y = R.gen()

        fx = Y**3+ 13*(Y**2) + 11*Y + 4

        roots = dict()

        for i in range(50):
            x = Fp.random_element()
            while x in roots:
                x = Fp.random_element()
            roots[x] = fx(x)

        basis = lagrange_basis(Fp, list(roots.keys()), 0)
        result = Fp(0)

        for r in roots.keys():
            result = result + roots[r]*basis[r]

        assert result == fx(0)

    test_basis_gen()
    test_value_gen()