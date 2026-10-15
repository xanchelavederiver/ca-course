/*
 * limbs.c — linear-time primitives on limb arrays: comparison, addition,
 * subtraction, multiplication by one limb, shifts. See limbs.h.
 */
#include "limbs.h"

#include <string.h>

#if defined(__x86_64__)
#include <x86intrin.h> /* _addcarry_u64 / _subborrow_u64: the ADC / SBB instructions */
#define HAVE_ADC 1
#endif

int ln_cmp(const limb_t *a, const limb_t *b, size_t n)
{
    while (n--) {
        if (a[n] != b[n])
            return a[n] > b[n] ? 1 : -1;
    }
    return 0;
}

size_t ln_normlen(const limb_t *a, size_t n)
{
    while (n && a[n - 1] == 0)
        n--;
    return n;
}

void ln_zero(limb_t *r, size_t n)
{
    if (n)
        memset(r, 0, n * sizeof *r);
}

void ln_copy(limb_t *r, const limb_t *a, size_t n)
{
    if (n && r != a)
        memmove(r, a, n * sizeof *r);
}

limb_t ln_add_n(limb_t *r, const limb_t *a, const limb_t *b, size_t n)
{
#ifdef HAVE_ADC
    unsigned char c = 0;
    for (size_t i = 0; i < n; i++) {
        unsigned long long t;
        c = _addcarry_u64(c, a[i], b[i], &t);
        r[i] = t;
    }
    return c;
#else
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        limb_t s = a[i] + c;
        c = s < c;
        s += b[i];
        c += s < b[i];
        r[i] = s;
    }
    return c;
#endif
}

limb_t ln_sub_n(limb_t *r, const limb_t *a, const limb_t *b, size_t n)
{
#ifdef HAVE_ADC
    unsigned char c = 0;
    for (size_t i = 0; i < n; i++) {
        unsigned long long t;
        c = _subborrow_u64(c, a[i], b[i], &t);
        r[i] = t;
    }
    return c;
#else
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        limb_t x = a[i], y = b[i] + c;
        c = (y < c) | (x < y);
        r[i] = x - y;
    }
    return c;
#endif
}

limb_t ln_add_1(limb_t *r, const limb_t *a, size_t n, limb_t b)
{
    size_t i = 0;
    for (; i < n && b; i++) {
        limb_t s = a[i] + b;
        b = s < b;
        r[i] = s;
    }
    ln_copy(r + i, a + i, n - i);
    return b;
}

limb_t ln_sub_1(limb_t *r, const limb_t *a, size_t n, limb_t b)
{
    size_t i = 0;
    for (; i < n && b; i++) {
        limb_t x = a[i];
        r[i] = x - b;
        b = x < b;
    }
    ln_copy(r + i, a + i, n - i);
    return b;
}

limb_t ln_add(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn)
{
    limb_t c = ln_add_n(r, a, b, bn);
    return ln_add_1(r + bn, a + bn, an - bn, c);
}

limb_t ln_sub(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn)
{
    limb_t c = ln_sub_n(r, a, b, bn);
    return ln_sub_1(r + bn, a + bn, an - bn, c);
}

limb_t ln_mul_1(limb_t *r, const limb_t *a, size_t n, limb_t b)
{
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        dlimb_t t = (dlimb_t)a[i] * b + c;
        r[i] = (limb_t)t;
        c = (limb_t)(t >> LIMB_BITS);
    }
    return c;
}

/* (B-1)^2 + 2(B-1) = B^2 - 1: the 128-bit accumulator never overflows. */
limb_t ln_addmul_1(limb_t *r, const limb_t *a, size_t n, limb_t b)
{
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        dlimb_t t = (dlimb_t)a[i] * b + r[i] + c;
        r[i] = (limb_t)t;
        c = (limb_t)(t >> LIMB_BITS);
    }
    return c;
}

limb_t ln_submul_1(limb_t *r, const limb_t *a, size_t n, limb_t b)
{
    limb_t c = 0;
    for (size_t i = 0; i < n; i++) {
        dlimb_t p = (dlimb_t)a[i] * b + c;
        limb_t lo = (limb_t)p, x = r[i];
        c = (limb_t)(p >> LIMB_BITS) + (x < lo);
        r[i] = x - lo;
    }
    return c;
}

limb_t ln_lshift(limb_t *r, const limb_t *a, size_t n, unsigned s)
{
    /* From the top down, so that r may coincide with a (or lie above it). */
    limb_t out = 0;
    if (n == 0)
        return 0;
    out = a[n - 1] >> (LIMB_BITS - s);
    for (size_t i = n - 1; i > 0; i--)
        r[i] = (a[i] << s) | (a[i - 1] >> (LIMB_BITS - s));
    r[0] = a[0] << s;
    return out;
}

limb_t ln_rshift(limb_t *r, const limb_t *a, size_t n, unsigned s)
{
    /* From the bottom up, so that r may coincide with a (or lie below it). */
    limb_t out;
    if (n == 0)
        return 0;
    out = a[0] << (LIMB_BITS - s);
    for (size_t i = 0; i + 1 < n; i++)
        r[i] = (a[i] >> s) | (a[i + 1] << (LIMB_BITS - s));
    r[n - 1] = a[n - 1] >> s;
    return out;
}
