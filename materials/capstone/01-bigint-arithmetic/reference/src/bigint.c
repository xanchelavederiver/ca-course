/*
 * bigint.c — the signed bigint type: memory, conversion, comparison, addition,
 * subtraction, multiplication, division and shifts on top of limbs.h.
 */
#include "bigint.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------------------------------------------------------------- memory ---------- */

static void *xrealloc(void *p, size_t bytes)
{
    p = realloc(p, bytes ? bytes : 1);
    if (!p) {
        fprintf(stderr, "out of memory (%zu bytes)\n", bytes);
        abort();
    }
    return p;
}

void bi_init(bigint *x)
{
    x->d = NULL;
    x->n = x->cap = 0;
    x->neg = 0;
}

void bi_free(bigint *x)
{
    free(x->d);
    bi_init(x);
}

void bi_reserve(bigint *x, size_t limbs)
{
    if (x->cap >= limbs)
        return;
    size_t cap = x->cap * 2 > limbs ? x->cap * 2 : limbs;
    x->d = xrealloc(x->d, cap * sizeof *x->d);
    x->cap = cap;
}

void bi_normalize(bigint *x)
{
    x->n = ln_normlen(x->d, x->n);
    if (x->n == 0)
        x->neg = 0;
}

/* Replace r's limbs by the heap array d (of n limbs, cap limbs allocated). */
static void bi_adopt(bigint *r, limb_t *d, size_t n, size_t cap, int neg)
{
    free(r->d);
    r->d = d;
    r->n = n;
    r->cap = cap;
    r->neg = neg;
    bi_normalize(r);
}

void bi_set(bigint *r, const bigint *a)
{
    if (r == a)
        return;
    bi_reserve(r, a->n);
    ln_copy(r->d, a->d, a->n);
    r->n = a->n;
    r->neg = a->neg;
}

void bi_set_limbs(bigint *r, const limb_t *a, size_t n, int neg)
{
    bi_reserve(r, n);
    ln_copy(r->d, a, n);
    r->n = n;
    r->neg = neg;
    bi_normalize(r);
}

void bi_set_si(bigint *r, long long v)
{
    bi_reserve(r, 1);
    r->neg = v < 0;
    r->d[0] = v < 0 ? (limb_t)0 - (limb_t)v : (limb_t)v;
    r->n = 1;
    bi_normalize(r);
}

void bi_swap(bigint *a, bigint *b)
{
    bigint t = *a;
    *a = *b;
    *b = t;
}

/* ---------------------------------------------------------------- conversion ------ */

static int hexval(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

int bi_from_hex(bigint *r, const char *s)
{
    int neg = 0;
    if (*s == '-' || *s == '+')
        neg = *s++ == '-';
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        s += 2;
    size_t len = strlen(s);
    if (len == 0)
        return -1;
    for (size_t i = 0; i < len; i++)
        if (hexval(s[i]) < 0)
            return -1;
    /* 16 hex digits per limb, starting from the least significant end. */
    size_t n = (len + 15) / 16;
    bi_reserve(r, n);
    for (size_t i = 0; i < n; i++) {
        limb_t v = 0;
        size_t end = len - 16 * i, start = end >= 16 ? end - 16 : 0;
        for (size_t k = start; k < end; k++)
            v = (v << 4) | (limb_t)hexval(s[k]);
        r->d[i] = v;
    }
    r->n = n;
    r->neg = neg;
    bi_normalize(r);
    return 0;
}

int bi_from_dec_ll(bigint *r, const char *s)
{
    char *end;
    long long v = strtoll(s, &end, 10);
    if (end == s || *end)
        return -1;
    bi_set_si(r, v);
    return 0;
}

char *bi_to_hex(const bigint *a)
{
    char *s = malloc(a->n * 16 + 4), *p = s;
    if (!s)
        abort();
    if (a->neg)
        *p++ = '-';
    *p++ = '0';
    *p++ = 'x';
    if (a->n == 0) {
        strcpy(p, "0");
        return s;
    }
    p += sprintf(p, "%llx", a->d[a->n - 1]);
    for (size_t i = a->n - 1; i-- > 0;)
        p += sprintf(p, "%016llx", a->d[i]);
    return s;
}

/* ---------------------------------------------------------------- queries --------- */

int bi_is_zero(const bigint *a) { return a->n == 0; }
int bi_sign(const bigint *a) { return a->n == 0 ? 0 : a->neg ? -1 : 1; }

int bi_cmpabs(const bigint *a, const bigint *b)
{
    if (a->n != b->n)
        return a->n > b->n ? 1 : -1;
    return ln_cmp(a->d, b->d, a->n);
}

int bi_cmp(const bigint *a, const bigint *b)
{
    if (a->neg != b->neg)
        return a->neg ? -1 : 1;
    int c = bi_cmpabs(a, b);
    return a->neg ? -c : c;
}

int bi_cmp_si(const bigint *a, long long v)
{
    bigint t;
    limb_t d;
    t.d = &d;
    t.cap = 1;
    t.neg = v < 0;
    d = v < 0 ? (limb_t)0 - (limb_t)v : (limb_t)v;
    t.n = d != 0;
    return bi_cmp(a, &t);
}

size_t bi_bitlen(const bigint *a)
{
    if (a->n == 0)
        return 0;
    return a->n * LIMB_BITS - (size_t)__builtin_clzll(a->d[a->n - 1]);
}

int bi_testbit(const bigint *a, size_t i)
{
    size_t w = i / LIMB_BITS;
    return w < a->n && ((a->d[w] >> (i % LIMB_BITS)) & 1);
}

/* ---------------------------------------------------------------- add / sub ------- */

void bi_neg(bigint *r, const bigint *a)
{
    bi_set(r, a);
    r->neg = r->n ? !r->neg : 0;
}

void bi_abs(bigint *r, const bigint *a)
{
    bi_set(r, a);
    r->neg = 0;
}

/* |r| = |a| + |b|, sign `neg`. r may be a or b: ln_add works in place. */
static void add_abs(bigint *r, const bigint *a, const bigint *b, int neg)
{
    if (a->n < b->n) {
        const bigint *t = a; a = b; b = t;
    }
    size_t an = a->n, bn = b->n;
    bi_reserve(r, an + 1);         /* may move r->d, which a or b may share */
    r->d[an] = ln_add(r->d, a->d, an, b->d, bn);
    r->n = an + 1;
    r->neg = neg;
    bi_normalize(r);
}

/* |r| = |a| - |b| for |a| >= |b|, sign `neg`. */
static void sub_abs(bigint *r, const bigint *a, const bigint *b, int neg)
{
    size_t an = a->n, bn = b->n;
    bi_reserve(r, an);
    ln_sub(r->d, a->d, an, b->d, bn);
    r->n = an;
    r->neg = neg;
    bi_normalize(r);
}

/* r = a + (-1)^bneg |b|: the common core of addition and subtraction. */
static void add_signed(bigint *r, const bigint *a, const bigint *b, int bneg)
{
    if (a->neg == bneg) {
        add_abs(r, a, b, bneg);
    } else if (bi_cmpabs(a, b) >= 0) {
        sub_abs(r, a, b, a->neg);
    } else {
        sub_abs(r, b, a, bneg);
    }
}

void bi_add(bigint *r, const bigint *a, const bigint *b) { add_signed(r, a, b, b->neg); }
void bi_sub(bigint *r, const bigint *a, const bigint *b) { add_signed(r, a, b, b->n ? !b->neg : 0); }

/* ---------------------------------------------------------------- multiplication -- */

enum { MUL_SCHOOL, MUL_KARATSUBA };

/* The product goes to a fresh array, so r may be a or b. */
static void mul_into(bigint *r, const bigint *a, const bigint *b, int method, size_t T)
{
    if (a->n == 0 || b->n == 0) {
        r->n = 0;
        r->neg = 0;
        return;
    }
    size_t n = a->n + b->n;
    limb_t *p = xrealloc(NULL, n * sizeof *p);
    if (method == MUL_SCHOOL)
        ln_mul_school(p, a->d, a->n, b->d, b->n);
    else
        ln_mul_karatsuba(p, a->d, a->n, b->d, b->n, T);
    bi_adopt(r, p, n, n, a->neg ^ b->neg);
}

static void sqr_into(bigint *r, const bigint *a, int method, size_t T)
{
    if (a->n == 0) {
        r->n = 0;
        r->neg = 0;
        return;
    }
    size_t n = 2 * a->n;
    limb_t *p = xrealloc(NULL, n * sizeof *p);
    if (method == MUL_SCHOOL)
        ln_sqr_school(p, a->d, a->n);
    else
        ln_sqr_karatsuba(p, a->d, a->n, T);
    bi_adopt(r, p, n, n, 0);
}

void bi_mul_school(bigint *r, const bigint *a, const bigint *b) { mul_into(r, a, b, MUL_SCHOOL, 0); }
void bi_mul_karatsuba(bigint *r, const bigint *a, const bigint *b, size_t T) { mul_into(r, a, b, MUL_KARATSUBA, T); }
void bi_mul(bigint *r, const bigint *a, const bigint *b) { mul_into(r, a, b, MUL_KARATSUBA, KARATSUBA_THRESHOLD); }
void bi_sqr_school(bigint *r, const bigint *a) { sqr_into(r, a, MUL_SCHOOL, 0); }
void bi_sqr_karatsuba(bigint *r, const bigint *a, size_t T) { sqr_into(r, a, MUL_KARATSUBA, T); }
void bi_sqr(bigint *r, const bigint *a) { sqr_into(r, a, MUL_KARATSUBA, KARATSUBA_SQR_THRESHOLD); }

/* ---------------------------------------------------------------- division -------- */

int bi_divmod(bigint *q, bigint *r, const bigint *a, const bigint *b)
{
    if (b->n == 0)
        return -1;
    int qneg = a->neg ^ b->neg, rneg = a->neg;
    if (bi_cmpabs(a, b) < 0) {               /* |a| < |b|: q = 0, r = a */
        if (r)
            bi_set(r, a);
        if (q) {
            q->n = 0;
            q->neg = 0;
        }
        return 0;
    }
    size_t an = a->n, bn = b->n, qn = an - bn + 1;
    limb_t *qd = xrealloc(NULL, qn * sizeof *qd);
    limb_t *rd = xrealloc(NULL, bn * sizeof *rd);
    ln_divrem(qd, rd, a->d, an, b->d, bn);
    /* Adopt after the division: q or r may be a or b. */
    if (q)
        bi_adopt(q, qd, qn, qn, qneg);
    else
        free(qd);
    if (r)
        bi_adopt(r, rd, bn, bn, rneg);
    else
        free(rd);
    return 0;
}

int bi_mod(bigint *r, const bigint *a, const bigint *m)
{
    if (m->n == 0)
        return -1;
    bigint am;                          /* |m|, sharing m's limbs (read-only) */
    am = *m;
    am.neg = 0;
    if (r == m) {                       /* r would overwrite the modulus */
        bigint t;
        bi_init(&t);
        bi_set(&t, m);
        t.neg = 0;
        bi_divmod(NULL, r, a, &t);
        if (r->neg)
            bi_add(r, r, &t);
        bi_free(&t);
        return 0;
    }
    bi_divmod(NULL, r, a, &am);
    if (r->neg)                         /* truncated remainder in (-|m|, 0): shift up */
        bi_add(r, r, &am);
    return 0;
}

/* ---------------------------------------------------------------- shifts ---------- */

void bi_shl(bigint *r, const bigint *a, size_t k)
{
    if (a->n == 0) {
        r->n = 0;
        r->neg = 0;
        return;
    }
    size_t w = k / LIMB_BITS, n = a->n + w + 1;
    unsigned s = (unsigned)(k % LIMB_BITS);
    limb_t *p = xrealloc(NULL, n * sizeof *p);
    ln_zero(p, w);
    if (s)
        p[n - 1] = ln_lshift(p + w, a->d, a->n, s);
    else {
        ln_copy(p + w, a->d, a->n);
        p[n - 1] = 0;
    }
    bi_adopt(r, p, n, n, a->neg);
}

void bi_shr(bigint *r, const bigint *a, size_t k)
{
    size_t w = k / LIMB_BITS;
    unsigned s = (unsigned)(k % LIMB_BITS);
    if (w >= a->n) {                    /* everything shifted out: 0, or -1 if a < 0 */
        if (a->neg)
            bi_set_si(r, -1);
        else {
            r->n = 0;
            r->neg = 0;
        }
        return;
    }
    /* floor(a / 2^k) for a < 0 is -ceil(|a| / 2^k): round the magnitude up if any
     * nonzero bit is shifted out. Look at the bits before overwriting r (r may be a). */
    int lost = 0;
    if (a->neg) {
        lost = ln_normlen(a->d, w) != 0 || (s && (a->d[w] << (LIMB_BITS - s)) != 0);
    }
    size_t n = a->n - w;
    limb_t *p = xrealloc(NULL, (n + 1) * sizeof *p);
    if (s)
        ln_rshift(p, a->d + w, n, s);
    else
        ln_copy(p, a->d + w, n);
    p[n] = 0;
    if (lost)
        ln_add_1(p, p, n + 1, 1);
    bi_adopt(r, p, n + 1, n + 1, a->neg);
}
