/*
 * gcd.c — the Euclidean algorithm and the extended Euclidean algorithm (item 4 of the
 * spec): gcd(a, b), Bezout coefficients and modular inverses.
 *
 * Each step is a full division with remainder (Algorithm D). Lehmer's or the binary
 * algorithm would be faster; the spec asks for Euclid.
 */
#include "bigint.h"

void bi_gcd(bigint *g, const bigint *a, const bigint *b)
{
    bigint x, y, r;
    bi_init(&x);
    bi_init(&y);
    bi_init(&r);
    bi_abs(&x, a);
    bi_abs(&y, b);
    while (!bi_is_zero(&y)) {       /* (x, y) <- (y, x mod y) */
        bi_divmod(NULL, &r, &x, &y);
        bi_swap(&x, &y);
        bi_swap(&y, &r);
    }
    bi_swap(g, &x);
    bi_free(&x);
    bi_free(&y);
    bi_free(&r);
}

/*
 * Invariants: r0 = s0 |a| + t0 |b|, r1 = s1 |a| + t1 |b|. At the end r0 = gcd and
 * a (sign(a) s0) + b (sign(b) t0) = gcd. The coefficients satisfy |s| <= |b| / g,
 * |t| <= |a| / g (Knuth, exercise 4.5.2-14), so they stay as short as the inputs.
 */
void bi_xgcd(bigint *g, bigint *x, bigint *y, const bigint *a, const bigint *b)
{
    bigint r0, r1, s0, s1, t0, t1, q, r, tmp;
    bigint *all[] = {&r0, &r1, &s0, &s1, &t0, &t1, &q, &r, &tmp};
    for (size_t i = 0; i < sizeof all / sizeof *all; i++)
        bi_init(all[i]);
    int aneg = a->neg, bneg = b->neg;
    bi_abs(&r0, a);
    bi_abs(&r1, b);
    bi_set_si(&s0, 1);
    bi_set_si(&t1, 1);
    while (!bi_is_zero(&r1)) {
        bi_divmod(&q, &r, &r0, &r1);          /* r0 = q r1 + r */
        bi_swap(&r0, &r1);
        bi_swap(&r1, &r);                     /* (r0, r1) <- (r1, r) */
        bi_mul(&tmp, &q, &s1);
        bi_sub(&tmp, &s0, &tmp);
        bi_swap(&s0, &s1);
        bi_swap(&s1, &tmp);                   /* (s0, s1) <- (s1, s0 - q s1) */
        bi_mul(&tmp, &q, &t1);
        bi_sub(&tmp, &t0, &tmp);
        bi_swap(&t0, &t1);
        bi_swap(&t1, &tmp);                   /* (t0, t1) <- (t1, t0 - q t1) */
    }
    if (aneg)
        bi_neg(&s0, &s0);
    if (bneg)
        bi_neg(&t0, &t0);
    bi_swap(g, &r0);
    if (x)
        bi_swap(x, &s0);
    if (y)
        bi_swap(y, &t0);
    for (size_t i = 0; i < sizeof all / sizeof *all; i++)
        bi_free(all[i]);
}

int bi_invmod(bigint *r, const bigint *a, const bigint *m)
{
    if (bi_sign(m) <= 0)
        return -1;
    bigint am, g, x;
    bi_init(&am);
    bi_init(&g);
    bi_init(&x);
    bi_mod(&am, a, m);
    bi_xgcd(&g, &x, NULL, &am, m);            /* am x + m y = g */
    int ok = bi_cmp_si(&g, 1) == 0 || bi_cmp_si(m, 1) == 0;
    if (ok)
        bi_mod(r, &x, m);
    bi_free(&am);
    bi_free(&g);
    bi_free(&x);
    return ok;
}
