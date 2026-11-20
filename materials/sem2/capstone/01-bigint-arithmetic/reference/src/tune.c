/*
 * tune.c — `bigint-tune`: measures where Karatsuba starts to pay off and prints the
 * times of the main operations at a few sizes.
 *
 * Threshold: for each length n it times the schoolbook product and ONE level of
 * Karatsuba (threshold n: split once, schoolbook below). The threshold is the smallest
 * n from which one level wins at every larger length measured; KARATSUBA_THRESHOLD
 * and KARATSUBA_SQR_THRESHOLD in limbs.h hold the values measured on the reference
 * machine (see README.md).
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "bigint.h"

static double now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static unsigned long long rng_state = 0x9E3779B97F4A7C15ULL;
static limb_t rnd(void)                  /* xorshift64* */
{
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return rng_state * 0x2545F4914F6CDD1DULL;
}

static void fill(limb_t *a, size_t n)
{
    for (size_t i = 0; i < n; i++)
        a[i] = rnd();
}

/* Seconds per call of f, measured over >= 20 ms, best of 5. */
#define TIME(expr, out)                                             \
    do {                                                            \
        double best_ = 1e30;                                        \
        long reps_ = 1;                                             \
        for (;;) {                                                  \
            double t0_ = now();                                     \
            for (long i_ = 0; i_ < reps_; i_++) { expr; }           \
            if (now() - t0_ > 0.02) break;                          \
            reps_ *= 2;                                             \
        }                                                           \
        for (int k_ = 0; k_ < 5; k_++) {                            \
            double t0_ = now();                                     \
            for (long i_ = 0; i_ < reps_; i_++) { expr; }           \
            double t_ = (now() - t0_) / reps_;                      \
            if (t_ < best_) best_ = t_;                             \
        }                                                           \
        (out) = best_;                                              \
    } while (0)

static void thresholds(void)
{
    enum { NMAX = 160 };
    static limb_t a[NMAX], b[NMAX], r[2 * NMAX];
    int mul_from = -1, sqr_from = -1;
    printf("%6s %12s %12s %8s   %12s %12s %8s\n", "limbs", "school, us", "kara1, us", "ratio",
           "sqr_sch, us", "sqr_kara1", "ratio");
    for (size_t n = 8; n <= NMAX; n += (n < 64 ? 4 : 16)) {
        fill(a, n);
        fill(b, n);
        double ts, tk, qs, qk;
        TIME(ln_mul_school(r, a, n, b, n), ts);
        TIME(ln_mul_karatsuba(r, a, n, b, n, n), tk);
        TIME(ln_sqr_school(r, a, n), qs);
        TIME(ln_sqr_karatsuba(r, a, n, n), qk);
        printf("%6zu %12.3f %12.3f %8.3f   %12.3f %12.3f %8.3f\n", n, ts * 1e6, tk * 1e6, tk / ts,
               qs * 1e6, qk * 1e6, qk / qs);
        if (tk < ts) { if (mul_from < 0) mul_from = (int)n; } else mul_from = -1;
        if (qk < qs) { if (sqr_from < 0) sqr_from = (int)n; } else sqr_from = -1;
    }
    printf("\nsuggested KARATSUBA_THRESHOLD     = %d (compiled: %d)\n", mul_from, KARATSUBA_THRESHOLD);
    printf("suggested KARATSUBA_SQR_THRESHOLD = %d (compiled: %d)\n\n", sqr_from,
           KARATSUBA_SQR_THRESHOLD);
}

static void random_big(bigint *x, size_t bits)
{
    size_t n = (bits + 63) / 64;
    bi_reserve(x, n);
    fill(x->d, n);
    if (bits % 64)
        x->d[n - 1] &= ((limb_t)1 << (bits % 64)) - 1;
    x->d[n - 1] |= (limb_t)1 << ((bits - 1) % 64);   /* exactly `bits` bits */
    x->n = n;
    x->neg = 0;
}

static void operations(void)
{
    static const size_t sizes[] = {256, 512, 1024, 2048, 4096, 16384};
    bigint a, b, m, e, c, q, r;
    bigint *all[] = {&a, &b, &m, &e, &c, &q, &r};
    for (size_t i = 0; i < 7; i++)
        bi_init(all[i]);
    printf("%6s %10s %10s %10s %10s %10s %10s %10s %12s %12s\n", "bits", "add", "mul_sch",
           "mul_kara", "sqr", "div 2n/n", "mont_mul", "gcd", "xgcd", "powmod q=16");
    for (size_t s = 0; s < sizeof sizes / sizeof *sizes; s++) {
        size_t bits = sizes[s];
        random_big(&a, bits);
        random_big(&b, bits);
        random_big(&m, bits);
        m.d[0] |= 1;
        random_big(&e, bits);
        bigint a2;
        bi_init(&a2);
        random_big(&a2, 2 * bits);
        bi_mont ctx;
        bi_mont_init(&ctx, &m);
        bigint am, bm;
        bi_init(&am);
        bi_init(&bm);
        bi_mont_to(&ctx, &am, &a);
        bi_mont_to(&ctx, &bm, &b);
        double t_add, t_ms, t_mk, t_sq, t_div, t_mm, t_gcd, t_xgcd, t_pow;
        TIME(bi_add(&c, &a, &b), t_add);
        TIME(bi_mul_school(&c, &a, &b), t_ms);
        TIME(bi_mul(&c, &a, &b), t_mk);
        TIME(bi_sqr(&c, &a), t_sq);
        TIME(bi_divmod(&q, &r, &a2, &b), t_div);
        TIME(bi_mont_mul(&ctx, &c, &am, &bm), t_mm);
        if (bits <= 4096) {
            TIME(bi_gcd(&c, &a, &b), t_gcd);
            TIME(bi_xgcd(&c, &q, &r, &a, &b), t_xgcd);
            TIME(bi_powmod_qary(&c, &a, &e, &m, 16, NULL), t_pow);
        } else {
            t_gcd = t_xgcd = t_pow = 0;
        }
        printf("%6zu %10.3f %10.3f %10.3f %10.3f %10.3f %10.3f %10.1f %12.1f %12.1f  (us)\n", bits,
               t_add * 1e6, t_ms * 1e6, t_mk * 1e6, t_sq * 1e6, t_div * 1e6, t_mm * 1e6,
               t_gcd * 1e6, t_xgcd * 1e6, t_pow * 1e6);
        bi_free(&a2);
        bi_free(&am);
        bi_free(&bm);
        bi_mont_free(&ctx);
    }
    for (size_t i = 0; i < 7; i++)
        bi_free(all[i]);
}

int main(int argc, char **argv)
{
    int ops_only = argc > 1 && argv[1][0] == 'o';
    if (!ops_only)
        thresholds();
    operations();
    return 0;
}
