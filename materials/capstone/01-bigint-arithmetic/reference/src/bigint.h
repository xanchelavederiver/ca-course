/*
 * bigint.h — signed integers of arbitrary length (sign and magnitude).
 *
 * A bigint owns a heap array of 64-bit limbs (limbs.h): value = (-1)^neg * sum d[i] B^i,
 * B = 2^64. It is kept normalized: n is the number of significant limbs (d[n-1] != 0),
 * zero has n == 0 and neg == 0. Every operation writes its result into a destination
 * that has been bi_init'ed and may be one of the operands (r = a + r is fine).
 *
 * The length is limited only by memory; the course spec asks for at least 16384 bits.
 *
 * Conventions for signed operands (documented in README.md):
 *   bi_divmod  truncates: q = trunc(a / b), r = a - q b has the sign of a (as C's / %);
 *   bi_mod     is the mathematical residue: 0 <= r < |m|;
 *   bi_shr     is the arithmetic shift: floor(a / 2^k) (as Python's >>, -1 >> 1 == -1);
 *   bi_shl     is a * 2^k;
 *   bi_gcd     is >= 0; bi_xgcd returns x, y with a x + b y = gcd(a, b).
 */
#ifndef BIGINT_H
#define BIGINT_H

#include <stddef.h>

#include "limbs.h"

typedef struct {
    limb_t *d;
    size_t n, cap;
    int neg;
} bigint;

/* ----- memory, assignment, conversion -------------------------------------------- */
void bi_init(bigint *x);
void bi_free(bigint *x);
void bi_reserve(bigint *x, size_t limbs);          /* capacity >= limbs */
void bi_normalize(bigint *x);
void bi_set(bigint *r, const bigint *a);
void bi_set_si(bigint *r, long long v);
void bi_set_limbs(bigint *r, const limb_t *a, size_t n, int neg);
void bi_swap(bigint *a, bigint *b);
int  bi_from_hex(bigint *r, const char *s);        /* "-0x1f", "0x0", "ff"; 0 ok, -1 bad */
int  bi_from_dec_ll(bigint *r, const char *s);     /* a decimal long long */
char *bi_to_hex(const bigint *a);                  /* malloc'ed "-0x1f" / "0x0" */

/* ----- queries ------------------------------------------------------------------- */
int    bi_is_zero(const bigint *a);
int    bi_sign(const bigint *a);                   /* -1, 0, 1 */
int    bi_cmp(const bigint *a, const bigint *b);
int    bi_cmpabs(const bigint *a, const bigint *b);
int    bi_cmp_si(const bigint *a, long long v);
size_t bi_bitlen(const bigint *a);                 /* of |a|; 0 for 0 */
int    bi_testbit(const bigint *a, size_t i);      /* bit i of |a| */

/* ----- arithmetic ------------------------------------------------------------------ */
void bi_neg(bigint *r, const bigint *a);
void bi_abs(bigint *r, const bigint *a);
void bi_add(bigint *r, const bigint *a, const bigint *b);
void bi_sub(bigint *r, const bigint *a, const bigint *b);
void bi_mul_school(bigint *r, const bigint *a, const bigint *b);
void bi_mul_karatsuba(bigint *r, const bigint *a, const bigint *b, size_t threshold);
void bi_mul(bigint *r, const bigint *a, const bigint *b);  /* Karatsuba, tuned threshold */
void bi_sqr_school(bigint *r, const bigint *a);
void bi_sqr_karatsuba(bigint *r, const bigint *a, size_t threshold);
void bi_sqr(bigint *r, const bigint *a);                   /* tuned threshold */
int  bi_divmod(bigint *q, bigint *r, const bigint *a, const bigint *b); /* -1 if b == 0 */
int  bi_mod(bigint *r, const bigint *a, const bigint *m);              /* -1 if m == 0 */
void bi_shl(bigint *r, const bigint *a, size_t k);
void bi_shr(bigint *r, const bigint *a, size_t k);

/* ----- Euclid (gcd.c) --------------------------------------------------------------- */
void bi_gcd(bigint *g, const bigint *a, const bigint *b);
void bi_xgcd(bigint *g, bigint *x, bigint *y, const bigint *a, const bigint *b);
int  bi_invmod(bigint *r, const bigint *a, const bigint *m); /* 1 ok, 0 no inverse, -1 m <= 0 */

/* ----- Montgomery arithmetic (mont.c) ------------------------------------------------ */
/* The precomputed context of remark 3, for an odd modulus m > 0 of n limbs; R = B^n.
 * Elements "in Montgomery form" are x R mod m, stored as bigints in [0, m). */
typedef struct {
    size_t n;          /* limbs of m */
    limb_t *m;         /* the modulus, n limbs */
    limb_t minv;       /* -m^{-1} mod B */
    bigint mod;        /* m as a bigint */
    bigint r2;         /* R^2 mod m: converts into Montgomery form */
    bigint one;        /* R mod m: 1 in Montgomery form */
    limb_t *t;         /* scratch, 2n + 1 limbs */
    limb_t *x, *y;     /* scratch, n limbs each (zero-padded operands) */
} bi_mont;

int  bi_mont_init(bi_mont *c, const bigint *m);    /* 0 ok; -1 if m is even or m <= 0 */
void bi_mont_free(bi_mont *c);
size_t bi_mont_rbits(const bi_mont *c);            /* log2 R = 64 n */
void bi_mont_redc(const bi_mont *c, bigint *r, const bigint *t); /* t R^{-1} mod m, 0 <= t */
void bi_mont_mul(const bi_mont *c, bigint *r, const bigint *a, const bigint *b); /* a b R^-1 */
void bi_mont_sqr(const bi_mont *c, bigint *r, const bigint *a);
void bi_mont_to(const bi_mont *c, bigint *r, const bigint *a);   /* a R mod m, any a */
void bi_mont_from(const bi_mont *c, bigint *r, const bigint *a); /* a R^{-1} mod m */

/* ----- exponentiation (pow.c); e >= 0, q a power of two in [2, 256] ------------------- */
int bi_pow_binary(bigint *r, const bigint *a, const bigint *e);
int bi_pow_qary(bigint *r, const bigint *a, const bigint *e, unsigned q);
/* Modular: m > 0. Odd m use Montgomery multiplication; even m fall back to reduction by
 * division (Montgomery needs gcd(m, B) = 1); *method (may be NULL) tells which. */
enum { POW_MONTGOMERY = 1, POW_DIVISION = 2 };
int bi_powmod_binary(bigint *r, const bigint *a, const bigint *e, const bigint *m, int *method);
int bi_powmod_qary(bigint *r, const bigint *a, const bigint *e, const bigint *m, unsigned q,
                   int *method);

#endif
