/*
 * mul.c — multiplication and squaring of limb arrays:
 *   schoolbook ("в столбик")      O(n^2)
 *   Karatsuba                     O(n^log2(3)) = O(n^1.585), schoolbook below a threshold
 *   squaring (remark 1)           schoolbook squaring computes each cross product a_i a_j
 *                                 once (about n^2/2 limb products instead of n^2);
 *                                 Karatsuba squaring needs 3 squarings, not 3 products.
 */
#include "limbs.h"

#include <stdio.h>
#include <stdlib.h>

/* ---------------------------------------------------------------- schoolbook ------ */

void ln_mul_school(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn)
{
    /* Row by row: r = a * b[0], then r[j..] += a * b[j]. The longer operand runs in
     * the inner loop, which is the one that matters for speed. */
    if (an < bn) {
        const limb_t *t = a; a = b; b = t;
        size_t tn = an; an = bn; bn = tn;
    }
    r[an] = ln_mul_1(r, a, an, b[0]);
    for (size_t j = 1; j < bn; j++)
        r[an + j] = ln_addmul_1(r + j, a, an, b[j]);
}

void ln_sqr_school(limb_t *r, const limb_t *a, size_t n)
{
    /* 1. Cross products: sum_{i<j} a_i a_j B^(i+j). Row i adds a_i * a[i+1..n) at
     *    position 2i+1; its carry lands in r[i+n], which no earlier row has touched. */
    ln_zero(r, 2 * n);
    for (size_t i = 0; i + 1 < n; i++)
        r[i + n] = ln_addmul_1(r + 2 * i + 1, a + i + 1, n - i - 1, a[i]);
    /* 2. Double them (the sum is < a^2 / 2, so no bit is lost). */
    ln_lshift(r, r, 2 * n, 1);
    /* 3. Add the squares a_i^2 B^(2i) of the diagonal. */
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        dlimb_t p = (dlimb_t)a[i] * a[i];
        dlimb_t s = (dlimb_t)r[2 * i] + (limb_t)p + c;
        r[2 * i] = (limb_t)s;
        s = (dlimb_t)r[2 * i + 1] + (limb_t)(p >> LIMB_BITS) + (limb_t)(s >> LIMB_BITS);
        r[2 * i + 1] = (limb_t)s;
        c = (limb_t)(s >> LIMB_BITS);
    }
}

/* ---------------------------------------------------------------- Karatsuba ------- */

/*
 * Split a = a0 + a1 B^h with h = floor(n/2) low limbs and m = n - h >= h high limbs.
 * The "subtractive" variant (it avoids the extra carry limb of (a0+a1)(b0+b1)):
 *
 *   a b = z0 + (z0 + z2 - (a1 - a0)(b1 - b0)) B^h + z2 B^2h,   z0 = a0 b0, z2 = a1 b1.
 *
 * Three half-size products instead of four. The middle term is >= 0 and fits 2m + 1
 * limbs; |a1 - a0| and |b1 - b0| are computed with their signs.
 */

/* d (m limbs) = |x - y|, x of m limbs, y of h <= m limbs; returns 1 if x < y. */
static int absdiff(limb_t *d, const limb_t *x, size_t m, const limb_t *y, size_t h)
{
    int x_less = ln_normlen(x + h, m - h) == 0 && ln_cmp(x, y, h) < 0;
    if (x_less) {
        ln_sub_n(d, y, x, h);
        ln_zero(d + h, m - h);
    } else {
        ln_sub(d, x, m, y, h);
    }
    return x_less;
}

/* Scratch limbs needed by kara_n / kara_sqr_n for operands of n limbs. */
static size_t kara_scratch(size_t n, size_t threshold)
{
    size_t total = 0;
    while (n >= threshold && n >= 2) {
        size_t m = n - n / 2;
        total += 6 * m + 1;
        n = m;
    }
    return total;
}

static void kara_n(limb_t *r, const limb_t *a, const limb_t *b, size_t n, size_t T, limb_t *ws)
{
    if (n < T || n < 2) {
        ln_mul_school(r, a, n, b, n);
        return;
    }
    size_t h = n / 2, m = n - h;
    limb_t *da = ws, *db = ws + m, *dd = ws + 2 * m, *t = ws + 4 * m, *next = ws + 6 * m + 1;

    int sa = absdiff(da, a + h, m, a, h);     /* |a1 - a0|, sign */
    int sb = absdiff(db, b + h, m, b, h);     /* |b1 - b0|, sign */
    kara_n(dd, da, db, m, T, next);           /* |(a1 - a0)(b1 - b0)|, 2m limbs */
    kara_n(r, a, b, h, T, next);              /* z0 -> r[0, 2h)  */
    kara_n(r + 2 * h, a + h, b + h, m, T, next); /* z2 -> r[2h, 2n) */

    t[2 * m] = ln_add(t, r + 2 * h, 2 * m, r, 2 * h); /* t = z0 + z2 */
    if (sa == sb)                             /* (a1-a0)(b1-b0) >= 0: subtract it */
        ln_sub(t, t, 2 * m + 1, dd, 2 * m);
    else
        ln_add(t, t, 2 * m + 1, dd, 2 * m);
    ln_add(r + h, r + h, 2 * n - h, t, 2 * m + 1); /* no carry out: r = a*b < B^2n */
}

static void kara_sqr_n(limb_t *r, const limb_t *a, size_t n, size_t T, limb_t *ws)
{
    if (n < T || n < 2) {
        ln_sqr_school(r, a, n);
        return;
    }
    size_t h = n / 2, m = n - h;
    limb_t *da = ws, *dd = ws + 2 * m, *t = ws + 4 * m, *next = ws + 6 * m + 1;

    absdiff(da, a + h, m, a, h);
    kara_sqr_n(dd, da, m, T, next);           /* (a1 - a0)^2 >= 0 */
    kara_sqr_n(r, a, h, T, next);
    kara_sqr_n(r + 2 * h, a + h, m, T, next);
    t[2 * m] = ln_add(t, r + 2 * h, 2 * m, r, 2 * h);
    ln_sub(t, t, 2 * m + 1, dd, 2 * m);
    ln_add(r + h, r + h, 2 * n - h, t, 2 * m + 1);
}

static limb_t *xmalloc_limbs(size_t n)
{
    limb_t *p = malloc((n ? n : 1) * sizeof *p);
    if (!p) {
        fprintf(stderr, "out of memory (%zu limbs)\n", n);
        abort();
    }
    return p;
}

void ln_mul_karatsuba(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn,
                      size_t T)
{
    if (T < 2)
        T = 2;
    if (an < bn) {
        const limb_t *t = a; a = b; b = t;
        size_t tn = an; an = bn; bn = tn;
    }
    if (bn < T) {                              /* the shorter operand is small */
        ln_mul_school(r, a, an, b, bn);
        return;
    }
    limb_t *ws = xmalloc_limbs(kara_scratch(bn, T) + 2 * bn);
    limb_t *tmp = ws + kara_scratch(bn, T);
    if (an == bn) {
        kara_n(r, a, b, bn, T, ws);
    } else {
        /* Unbalanced: cut a into bn-limb pieces, multiply each by b (balanced
         * Karatsuba), and add the partial products at their offsets. */
        ln_zero(r, an + bn);
        size_t off = 0;
        for (; off + bn <= an; off += bn) {
            kara_n(tmp, a + off, b, bn, T, ws);
            ln_add(r + off, r + off, an + bn - off, tmp, 2 * bn);
        }
        if (off < an) {                        /* the last, shorter piece */
            size_t rest = an - off;
            ln_mul_karatsuba(tmp, b, bn, a + off, rest, T);
            ln_add(r + off, r + off, an + bn - off, tmp, bn + rest);
        }
    }
    free(ws);
}

void ln_sqr_karatsuba(limb_t *r, const limb_t *a, size_t n, size_t T)
{
    if (T < 2)
        T = 2;
    if (n < T) {
        ln_sqr_school(r, a, n);
        return;
    }
    limb_t *ws = xmalloc_limbs(kara_scratch(n, T));
    kara_sqr_n(r, a, n, T, ws);
    free(ws);
}

void ln_mul(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn)
{
    ln_mul_karatsuba(r, a, an, b, bn, KARATSUBA_THRESHOLD);
}

void ln_sqr(limb_t *r, const limb_t *a, size_t n)
{
    ln_sqr_karatsuba(r, a, n, KARATSUBA_SQR_THRESHOLD);
}
