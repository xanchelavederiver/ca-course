/*
 * mont.c — Montgomery reduction and multiplication (item 6 of the spec, remark 3).
 *
 * For an odd modulus m of n limbs let R = B^n > m. REDC(t) = t R^{-1} mod m is computed
 * without division: adding a suitable multiple u m of the modulus makes the lowest
 * limb zero, n times over, after which the number is divisible by R (Montgomery 1985;
 * Crandall--Pomerance, Algorithm 9.2.5; Knuth, exercise 4.3.1-41). The quantities
 * that depend only on m (-m^{-1} mod B, R mod m, R^2 mod m) are computed once in the
 * context (remark 3).
 *
 * Montgomery form: x~ = x R mod m. Then REDC(x~ y~) = (x y)~, so a chain of modular
 * multiplications (exponentiation) needs one conversion at each end and none inside.
 */
#include "bigint.h"

#include <stdio.h>
#include <stdlib.h>

static limb_t *alloc_limbs(size_t n)
{
    limb_t *p = calloc(n ? n : 1, sizeof *p);
    if (!p) {
        fprintf(stderr, "out of memory (%zu limbs)\n", n);
        abort();
    }
    return p;
}

/* -m0^{-1} mod 2^64 for odd m0, by Newton's iteration x <- x (2 - m0 x): each step
 * doubles the number of correct low bits; x = m0 is already right mod 2^3. */
static limb_t neg_inverse(limb_t m0)
{
    limb_t x = m0;
    for (int i = 0; i < 5; i++)          /* 3 -> 6 -> 12 -> 24 -> 48 -> 96 bits */
        x *= 2 - m0 * x;
    return (limb_t)0 - x;
}

int bi_mont_init(bi_mont *c, const bigint *m)
{
    if (bi_sign(m) <= 0 || !(m->d[0] & 1))
        return -1;
    size_t n = m->n;
    c->n = n;
    c->m = alloc_limbs(n);
    ln_copy(c->m, m->d, n);
    c->minv = neg_inverse(m->d[0]);
    c->t = alloc_limbs(2 * n + 1);
    c->x = alloc_limbs(n);
    c->y = alloc_limbs(n);
    bi_init(&c->mod);
    bi_init(&c->r2);
    bi_init(&c->one);
    bi_set(&c->mod, m);
    /* R mod m and R^2 mod m by division (once per modulus). */
    bigint p;
    bi_init(&p);
    bi_set_si(&p, 1);
    bi_shl(&p, &p, n * LIMB_BITS);
    bi_mod(&c->one, &p, m);
    bi_shl(&p, &p, n * LIMB_BITS);
    bi_mod(&c->r2, &p, m);
    bi_free(&p);
    return 0;
}

void bi_mont_free(bi_mont *c)
{
    free(c->m);
    free(c->t);
    free(c->x);
    free(c->y);
    bi_free(&c->mod);
    bi_free(&c->r2);
    bi_free(&c->one);
}

size_t bi_mont_rbits(const bi_mont *c) { return c->n * LIMB_BITS; }

/*
 * REDC on the scratch array t[0..2n] (t[2n] = 0 on entry), value t < m R.
 * Step i adds u m B^i with u = t_i (-m^{-1}) mod B, which clears limb i. After n steps
 * t = (t + U m) with U < R, so t / R < (m R + R m) / R = 2m: one conditional
 * subtraction gives the result in [0, m). It is written to r (n limbs).
 */
static void redc_raw(const bi_mont *c, limb_t *r, limb_t *t)
{
    size_t n = c->n;
    for (size_t i = 0; i < n; i++) {
        limb_t u = t[i] * c->minv;
        limb_t carry = ln_addmul_1(t + i, c->m, n, u);   /* now t[i] == 0 */
        for (size_t k = i + n; carry && k <= 2 * n; k++) { /* propagate the carry */
            t[k] += carry;
            carry = t[k] < carry;
        }
    }
    if (t[2 * n] || ln_cmp(t + n, c->m, n) >= 0)
        ln_sub_n(r, t + n, c->m, n);
    else
        ln_copy(r, t + n, n);
}

/* Copy x (0 <= x < m, at most n limbs) zero-padded into the n-limb array p. */
static void pad(limb_t *p, const bigint *x, size_t n)
{
    ln_copy(p, x->d, x->n);
    ln_zero(p + x->n, n - x->n);
}

static void finish(const bi_mont *c, bigint *r)
{
    bi_set_limbs(r, c->x, c->n, 0);
}

void bi_mont_redc(const bi_mont *c, bigint *r, const bigint *t)
{
    size_t n = c->n;
    bigint red;
    bi_init(&red);
    /* REDC needs 0 <= t < m R, i.e. floor(t / R) < m; reduce other inputs mod m first
     * (same result mod m). With fewer than 2n limbs, floor(t / R) < B^(n-1) <= m. */
    const bigint *src = t;
    if (t->neg || t->n > 2 * n || (t->n == 2 * n && ln_cmp(t->d + n, c->m, n) >= 0)) {
        bi_mod(&red, t, &c->mod);
        src = &red;
    }
    ln_copy(c->t, src->d, src->n);
    ln_zero(c->t + src->n, 2 * n + 1 - src->n);
    redc_raw(c, c->x, c->t);
    finish(c, r);
    bi_free(&red);
}

void bi_mont_mul(const bi_mont *c, bigint *r, const bigint *a, const bigint *b)
{
    size_t n = c->n;
    pad(c->x, a, n);
    pad(c->y, b, n);
    ln_mul(c->t, c->x, n, c->y, n);            /* Karatsuba above its threshold */
    c->t[2 * n] = 0;
    redc_raw(c, c->x, c->t);
    finish(c, r);
}

void bi_mont_sqr(const bi_mont *c, bigint *r, const bigint *a)
{
    size_t n = c->n;
    pad(c->x, a, n);
    ln_sqr(c->t, c->x, n);
    c->t[2 * n] = 0;
    redc_raw(c, c->x, c->t);
    finish(c, r);
}

void bi_mont_to(const bi_mont *c, bigint *r, const bigint *a)
{
    bigint am;
    bi_init(&am);
    bi_mod(&am, a, &c->mod);
    bi_mont_mul(c, r, &am, &c->r2);           /* REDC(a R^2) = a R */
    bi_free(&am);
}

void bi_mont_from(const bi_mont *c, bigint *r, const bigint *a)
{
    bi_mont_redc(c, r, a);                     /* REDC(a~) = a */
}
