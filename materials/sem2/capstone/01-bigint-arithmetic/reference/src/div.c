/*
 * div.c — division with remainder of limb arrays: Knuth, TAOCP vol. 2, sec. 4.3.1,
 * Algorithm D (the step names D1..D8 below are Knuth's).
 */
#include "limbs.h"

#include <stdio.h>
#include <stdlib.h>

unsigned long ln_div_addbacks, ln_div_qhat_max;

limb_t ln_div_2by1(limb_t hi, limb_t lo, limb_t d, limb_t *rem)
{
#if defined(__x86_64__)
    /* DIV r/m64 divides RDX:RAX by the operand; it faults if the quotient does not
     * fit 64 bits, which hi < d rules out. The generic 128-bit '/' would call the
     * much slower library routine __udivti3. */
    limb_t q, r;
    __asm__("divq %4" : "=a"(q), "=d"(r) : "a"(lo), "d"(hi), "rm"(d) : "cc");
    *rem = r;
    return q;
#else
    dlimb_t n = ((dlimb_t)hi << LIMB_BITS) | lo;
    *rem = (limb_t)(n % d);
    return (limb_t)(n / d);
#endif
}

static void *xmalloc(size_t bytes)
{
    void *p = malloc(bytes ? bytes : 1);
    if (!p) {
        fprintf(stderr, "out of memory (%zu bytes)\n", bytes);
        abort();
    }
    return p;
}

/* Division by a single limb: the "short division" of Knuth's exercise 4.3.1-16. */
static void divrem_1(limb_t *q, limb_t *r, const limb_t *a, size_t an, limb_t d)
{
    limb_t rem = 0;
    for (size_t i = an; i-- > 0;) {
        limb_t qi = ln_div_2by1(rem, a[i], d, &rem);
        if (q)
            q[i] = qi;
    }
    if (r)
        r[0] = rem;
}

void ln_divrem(limb_t *q, limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t n)
{
    if (n == 1) {
        divrem_1(q, r, a, an, b[0]);
        return;
    }
    size_t m = an - n;                       /* the quotient has m + 1 limbs */

    /* D1. Normalize: shift both so that the top bit of the divisor is set. Then the
     * two-limb estimate of D3 is at most 2 too large (Knuth, Theorem 4.3.1B). */
    unsigned s = (unsigned)__builtin_clzll(b[n - 1]);
    limb_t *un = xmalloc((an + 1 + n) * sizeof *un), *vn = un + an + 1;
    if (s) {
        ln_lshift(vn, b, n, s);
        un[an] = ln_lshift(un, a, an, s);
    } else {
        ln_copy(vn, b, n);
        ln_copy(un, a, an);
        un[an] = 0;
    }
    const limb_t v1 = vn[n - 1], v2 = vn[n - 2];

    /* D2..D7: one quotient limb per step, from the top. */
    for (size_t j = m + 1; j-- > 0;) {
        limb_t *u = un + j;                  /* the window u[0..n] */
        limb_t qhat, rhat;
        int rhat_big;                        /* rhat >= B: the D3 test cannot fail */

        /* D3. Estimate qhat = floor((u_n B + u_{n-1}) / v1), capped at B - 1. */
        if (u[n] >= v1) {                    /* only u[n] == v1 is possible */
            qhat = ~(limb_t)0;
            rhat = u[n - 1] + v1;            /* = u_n B + u_{n-1} - qhat v1 */
            rhat_big = rhat < v1;
            ln_div_qhat_max++;
        } else {
            qhat = ln_div_2by1(u[n], u[n - 1], v1, &rhat);
            rhat_big = 0;
        }
        /* ... and correct it with the next limb: while qhat v2 > rhat B + u_{n-2},
         * decrease qhat (at most twice). */
        while (!rhat_big && (dlimb_t)qhat * v2 > (((dlimb_t)rhat << LIMB_BITS) | u[n - 2])) {
            qhat--;
            rhat += v1;
            rhat_big = rhat < v1;
        }

        /* D4. Multiply and subtract: u[0..n] -= qhat * v. */
        limb_t top = u[n];
        limb_t borrow = ln_submul_1(u, vn, n, qhat);
        u[n] = top - borrow;

        /* D5/D6. If the result went negative, qhat was still one too large (this
         * happens with probability about 2/B): add v back once. */
        if (top < borrow) {
            qhat--;
            u[n] += ln_add_n(u, u, vn, n);
            ln_div_addbacks++;
        }
        if (q)
            q[j] = qhat;                     /* D7: next j */
    }

    /* D8. Unnormalize the remainder, which is in un[0..n). */
    if (r) {
        if (s)
            ln_rshift(r, un, n, s);
        else
            ln_copy(r, un, n);
    }
    free(un);
}
