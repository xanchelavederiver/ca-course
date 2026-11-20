/*
 * limbs.h — the low layer: arithmetic on natural numbers stored as little-endian
 * arrays of 64-bit "digits" (limbs), in the spirit of GMP's mpn layer.
 *
 * A number with n limbs is a[0] + a[1]*B + ... + a[n-1]*B^(n-1), B = 2^64.
 * Functions take explicit lengths and never allocate unless stated; the signed,
 * self-managing bigint type of bigint.h is built on top of them.
 *
 * Products of two limbs are computed in a 128-bit type (unsigned __int128, a GCC/Clang
 * extension that compiles to a single MUL on x86-64). Carry chains use the ADC/SBB
 * instructions through the _addcarry_u64/_subborrow_u64 intrinsics (remark 2).
 */
#ifndef LIMBS_H
#define LIMBS_H

#include <stddef.h>

typedef unsigned long long limb_t;
typedef unsigned __int128 dlimb_t;
#define LIMB_BITS 64

/* Karatsuba thresholds in limbs (measured with `build/bigint-tune`, see README):
 * operands shorter than this are multiplied (squared) by the schoolbook method. */
#ifndef KARATSUBA_THRESHOLD
#define KARATSUBA_THRESHOLD 24
#endif
#ifndef KARATSUBA_SQR_THRESHOLD
#define KARATSUBA_SQR_THRESHOLD 48
#endif

/* Comparison, length. */
int    ln_cmp(const limb_t *a, const limb_t *b, size_t n);        /* -1, 0, 1 */
size_t ln_normlen(const limb_t *a, size_t n);                     /* n without leading zero limbs */
void   ln_zero(limb_t *r, size_t n);
void   ln_copy(limb_t *r, const limb_t *a, size_t n);             /* memmove semantics */

/* Addition and subtraction; r may coincide with a or b. Return the carry / borrow. */
limb_t ln_add_n(limb_t *r, const limb_t *a, const limb_t *b, size_t n);
limb_t ln_sub_n(limb_t *r, const limb_t *a, const limb_t *b, size_t n);
limb_t ln_add(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn); /* an >= bn */
limb_t ln_sub(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn); /* an >= bn */
limb_t ln_add_1(limb_t *r, const limb_t *a, size_t n, limb_t b);
limb_t ln_sub_1(limb_t *r, const limb_t *a, size_t n, limb_t b);

/* r = a * b (one limb), r += a * b, r -= a * b; return the high limb / borrow. */
limb_t ln_mul_1(limb_t *r, const limb_t *a, size_t n, limb_t b);
limb_t ln_addmul_1(limb_t *r, const limb_t *a, size_t n, limb_t b);
limb_t ln_submul_1(limb_t *r, const limb_t *a, size_t n, limb_t b);

/* Shifts by 0 < s < 64 bits; return the bits shifted out (in the low / high end). */
limb_t ln_lshift(limb_t *r, const limb_t *a, size_t n, unsigned s);
limb_t ln_rshift(limb_t *r, const limb_t *a, size_t n, unsigned s);

/* Multiplication. r has an + bn (2n) limbs and must not overlap the operands.
 * `threshold` is the Karatsuba cut-off in limbs (>= 2); ln_mul/ln_sqr use the tuned
 * defaults. Lengths must be >= 1. */
void ln_mul_school(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn);
void ln_sqr_school(limb_t *r, const limb_t *a, size_t n);
void ln_mul_karatsuba(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn,
                      size_t threshold);
void ln_sqr_karatsuba(limb_t *r, const limb_t *a, size_t n, size_t threshold);
void ln_mul(limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn);
void ln_sqr(limb_t *r, const limb_t *a, size_t n);

/* Division with remainder (Knuth, TAOCP vol. 2, 4.3.1, Algorithm D).
 * a has an >= bn limbs, b has bn limbs with b[bn-1] != 0; q gets an - bn + 1 limbs,
 * r gets bn limbs (either may be NULL). Neither may overlap a or b. */
void ln_divrem(limb_t *q, limb_t *r, const limb_t *a, size_t an, const limb_t *b, size_t bn);

/* Statistics of Algorithm D since the last reset (for tests and for "extra"):
 * how often the quotient digit estimate was one too large and step D6 ("add back")
 * ran, and how often the estimate started at B - 1 (u_j+n == v_n-1). */
extern unsigned long ln_div_addbacks, ln_div_qhat_max;

/* 128-by-64-bit division: returns floor((hi*B + lo) / d), *rem = remainder; hi < d. */
limb_t ln_div_2by1(limb_t hi, limb_t lo, limb_t d, limb_t *rem);

#endif
