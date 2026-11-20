/*
 * pow.c — fast exponentiation (items 7 and 8 of the spec).
 *
 *   binary, left to right:  scan the bits of e from the top; x <- x^2, and x <- x a
 *                           where the bit is 1. The multiplier is always the same a
 *                           (footnote 3: right-to-left needs a second running square,
 *                           and a fixed small multiplier is cheaper still for small a);
 *   q-ary, q = 2^k:         write e in base q; x <- x^q (k squarings), then multiply by
 *                           the precomputed a^d for each nonzero digit d. About
 *                           log2(e) squarings + log2(e)/k multiplications + q - 2 for the
 *                           table, against log2(e)/2 multiplications of the binary method.
 *                           q is a power of two (footnote 4) so that the digits are just
 *                           k-bit fields of the binary representation.
 *
 * The same two algorithms run in three "domains": plain integers, residues mod an odd m
 * in Montgomery form, and residues mod an even m (reduced by division, since Montgomery
 * needs gcd(m, B) = 1).
 */
#include "bigint.h"

enum { DOM_PLAIN, DOM_MONT, DOM_DIV };

typedef struct {
    int kind;
    const bi_mont *mont;   /* DOM_MONT */
    const bigint *m;       /* DOM_DIV */
} domain;

static void dmul(const domain *D, bigint *r, const bigint *a, const bigint *b)
{
    switch (D->kind) {
    case DOM_MONT:
        bi_mont_mul(D->mont, r, a, b);
        break;
    case DOM_DIV:
        bi_mul(r, a, b);
        bi_mod(r, r, D->m);
        break;
    default:
        bi_mul(r, a, b);
    }
}

static void dsqr(const domain *D, bigint *r, const bigint *a)
{
    switch (D->kind) {
    case DOM_MONT:
        bi_mont_sqr(D->mont, r, a);
        break;
    case DOM_DIV:
        bi_sqr(r, a);
        bi_mod(r, r, D->m);
        break;
    default:
        bi_sqr(r, a);
    }
}

/* k bits of e starting at bit `pos` (bits beyond the top read as 0). */
static unsigned digit(const bigint *e, size_t pos, unsigned k)
{
    unsigned d = 0;
    for (unsigned i = 0; i < k; i++)
        d |= (unsigned)bi_testbit(e, pos + i) << i;
    return d;
}

/* r = a^e in domain D for e > 0 (a is already a domain element). */
static void pow_binary_ltr(const domain *D, bigint *r, const bigint *a, const bigint *e)
{
    bigint x;
    bi_init(&x);
    bi_set(&x, a);                          /* the top bit of e is 1 */
    for (size_t i = bi_bitlen(e) - 1; i-- > 0;) {
        dsqr(D, &x, &x);
        if (bi_testbit(e, i))
            dmul(D, &x, &x, a);
    }
    bi_swap(r, &x);
    bi_free(&x);
}

static void pow_qary(const domain *D, bigint *r, const bigint *a, const bigint *e, unsigned k)
{
    unsigned q = 1u << k;
    bigint tbl[256], x;                     /* tbl[d] = a^d, d = 1 .. q-1 */
    bi_init(&x);
    for (unsigned d = 1; d < q; d++) {
        bi_init(&tbl[d]);
        if (d == 1)
            bi_set(&tbl[1], a);
        else
            dmul(D, &tbl[d], &tbl[d - 1], a);
    }
    size_t digits = (bi_bitlen(e) + k - 1) / k;
    bi_set(&x, &tbl[digit(e, (digits - 1) * k, k)]);   /* the top digit is nonzero */
    for (size_t i = digits - 1; i-- > 0;) {
        for (unsigned s = 0; s < k; s++)
            dsqr(D, &x, &x);
        unsigned d = digit(e, i * k, k);
        if (d)
            dmul(D, &x, &x, &tbl[d]);
    }
    bi_swap(r, &x);
    bi_free(&x);
    for (unsigned d = 1; d < q; d++)
        bi_free(&tbl[d]);
}

/* log2 q for q in {2, 4, ..., 256}, else 0. */
static unsigned log2_q(unsigned q)
{
    for (unsigned k = 1; k <= 8; k++)
        if (q == 1u << k)
            return k;
    return 0;
}

/* Common driver: k == 0 means the binary method. */
static int pow_plain(bigint *r, const bigint *a, const bigint *e, unsigned k)
{
    if (e->neg)
        return -1;
    if (bi_is_zero(e)) {                    /* a^0 = 1, also for a = 0 */
        bi_set_si(r, 1);
        return 0;
    }
    domain D = {DOM_PLAIN, 0, 0};
    if (k)
        pow_qary(&D, r, a, e, k);
    else
        pow_binary_ltr(&D, r, a, e);
    return 0;
}

static int pow_mod(bigint *r, const bigint *a, const bigint *e, const bigint *m, unsigned k,
                   int *method)
{
    if (e->neg || bi_sign(m) <= 0)
        return -1;
    bi_mont ctx;
    int odd = m->d[0] & 1;
    if (method)
        *method = odd ? POW_MONTGOMERY : POW_DIVISION;
    if (bi_cmp_si(m, 1) == 0) {             /* everything is 0 mod 1 */
        bi_set_si(r, 0);
        return 0;
    }
    if (bi_is_zero(e)) {
        bi_set_si(r, 1);
        return 0;
    }
    bigint base;
    bi_init(&base);
    if (odd) {
        bi_mont_init(&ctx, m);
        domain D = {DOM_MONT, &ctx, 0};
        bi_mont_to(&ctx, &base, a);         /* a R mod m (a is reduced mod m first) */
        if (k)
            pow_qary(&D, r, &base, e, k);
        else
            pow_binary_ltr(&D, r, &base, e);
        bi_mont_from(&ctx, r, r);
        bi_mont_free(&ctx);
    } else {
        domain D = {DOM_DIV, 0, m};
        bi_mod(&base, a, m);
        if (k)
            pow_qary(&D, r, &base, e, k);
        else
            pow_binary_ltr(&D, r, &base, e);
    }
    bi_free(&base);
    return 0;
}

int bi_pow_binary(bigint *r, const bigint *a, const bigint *e) { return pow_plain(r, a, e, 0); }

int bi_pow_qary(bigint *r, const bigint *a, const bigint *e, unsigned q)
{
    unsigned k = log2_q(q);
    return k ? pow_plain(r, a, e, k) : -1;
}

int bi_powmod_binary(bigint *r, const bigint *a, const bigint *e, const bigint *m, int *method)
{
    return pow_mod(r, a, e, m, 0, method);
}

int bi_powmod_qary(bigint *r, const bigint *a, const bigint *e, const bigint *m, unsigned q,
                   int *method)
{
    unsigned k = log2_q(q);
    return k ? pow_mod(r, a, e, m, k, method) : -1;
}
