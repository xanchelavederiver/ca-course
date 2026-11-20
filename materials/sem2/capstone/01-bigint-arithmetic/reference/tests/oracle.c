/*
 * oracle.c — `bigint-oracle SEED ROUNDS`: randomized differential test of the library
 * against GNU GMP (the oracle; only this test program links it).
 *
 * Operands have random signs and lengths that concentrate on the interesting places:
 * 0..4 limbs, the Karatsuba thresholds T +- 2 and 2T +- 2, and long operands up to 300
 * limbs (> 16384 bits). Half are drawn with mpz_rrandomb (long runs of 0 and 1 bits:
 * limbs 0 and B - 1, which exercise carries and the corrections of Algorithm D).
 *
 * Prints "checks=... failures=... addbacks=... qhat_max=..." and exits 1 on any failure.
 */
#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bigint.h"

static gmp_randstate_t rs;
static unsigned long checks, failures;

static unsigned long urand(unsigned long n) { return gmp_urandomm_ui(rs, n); }

static void to_mpz(mpz_t z, const bigint *x)
{
    mpz_import(z, x->n, -1, sizeof(limb_t), 0, 0, x->d);
    if (x->neg)
        mpz_neg(z, z);
}

static void from_mpz(bigint *x, const mpz_t z)
{
    size_t n = (mpz_sizeinbase(z, 2) + 63) / 64, cnt = 0;
    bi_reserve(x, n + 1);
    mpz_export(x->d, &cnt, -1, sizeof(limb_t), 0, 0, z);
    x->n = cnt;
    x->neg = mpz_sgn(z) < 0;
    bi_normalize(x);
}

/* A random length in limbs, concentrated around the special places. */
static size_t rand_limbs(size_t maxn)
{
    size_t n;
    switch (urand(6)) {
    case 0: n = urand(5); break;
    case 1: n = KARATSUBA_THRESHOLD - 2 + urand(5); break;
    case 2: n = 2 * KARATSUBA_THRESHOLD - 2 + urand(5); break;
    case 3: n = KARATSUBA_SQR_THRESHOLD - 2 + urand(5); break;
    case 4: n = 1 + urand(300); break;
    default: n = 1 + urand(40);
    }
    return n > maxn ? maxn : n;
}

static void rand_mpz(mpz_t z, size_t limbs, int allow_neg)
{
    if (limbs == 0) {
        mpz_set_ui(z, 0);
        return;
    }
    if (urand(2))
        mpz_rrandomb(z, rs, limbs * 64 - urand(64));
    else
        mpz_urandomb(z, rs, limbs * 64);
    if (allow_neg && urand(2))
        mpz_neg(z, z);
}

static void report(const char *what, const mpz_t want, const bigint *got, const mpz_t a,
                   const mpz_t b)
{
    failures++;
    if (failures > 5)
        return;
    mpz_t g;
    mpz_init(g);
    to_mpz(g, got);
    gmp_fprintf(stderr, "FAIL %s\n  a = %#Zx\n  b = %#Zx\n  want %#Zx\n  got  %#Zx\n", what, a,
                b, want, g);
    mpz_clear(g);
}

static void expect(const char *what, const mpz_t want, const bigint *got, const mpz_t a,
                   const mpz_t b)
{
    mpz_t g;
    mpz_init(g);
    to_mpz(g, got);
    checks++;
    if (mpz_cmp(g, want) != 0)
        report(what, want, got, a, b);
    mpz_clear(g);
}

static void round_once(void)
{
    mpz_t A, B, M, E, W, W2, T1;
    bigint a, b, m, e, c, d, f;
    mpz_inits(A, B, M, E, W, W2, T1, NULL);
    bi_init(&a); bi_init(&b); bi_init(&m); bi_init(&e); bi_init(&c); bi_init(&d); bi_init(&f);

    rand_mpz(A, rand_limbs(300), 1);
    rand_mpz(B, rand_limbs(300), 1);
    from_mpz(&a, A);
    from_mpz(&b, B);

    /* add / sub, also in place */
    bi_add(&c, &a, &b); mpz_add(W, A, B); expect("add", W, &c, A, B);
    bi_sub(&c, &a, &b); mpz_sub(W, A, B); expect("sub", W, &c, A, B);
    bi_set(&c, &a); bi_add(&c, &c, &c); mpz_add(W, A, A); expect("add in place", W, &c, A, A);
    bi_set(&c, &b); bi_sub(&c, &a, &c); mpz_sub(W, A, B); expect("sub in place", W, &c, A, B);

    /* multiplication and squaring */
    static const size_t TS[] = {2, 3, 4, 5, 8, 16, KARATSUBA_THRESHOLD};
    mpz_mul(W, A, B);
    bi_mul_school(&c, &a, &b); expect("mul_school", W, &c, A, B);
    bi_mul_karatsuba(&c, &a, &b, TS[urand(7)]); expect("mul_karatsuba", W, &c, A, B);
    bi_mul(&c, &a, &b); expect("mul", W, &c, A, B);
    mpz_mul(W, A, A);
    bi_sqr_school(&c, &a); expect("sqr_school", W, &c, A, A);
    bi_sqr_karatsuba(&c, &a, TS[urand(7)]); expect("sqr_karatsuba", W, &c, A, A);
    bi_sqr(&c, &a); expect("sqr", W, &c, A, A);

    /* division: truncated divmod, and the residue in [0, |b|) */
    if (mpz_sgn(B)) {
        bi_divmod(&c, &d, &a, &b);
        mpz_tdiv_qr(W, W2, A, B);
        expect("divmod q", W, &c, A, B);
        expect("divmod r", W2, &d, A, B);
        bi_mod(&c, &a, &b);
        mpz_abs(T1, B);
        mpz_mod(W, A, T1);
        expect("mod", W, &c, A, B);
        /* a = q b + r with a crafted to be a multiple of b plus a small remainder */
        mpz_mul(T1, B, A);
        mpz_add_ui(T1, T1, urand(3));
        from_mpz(&f, T1);
        bi_divmod(&c, &d, &f, &b);
        mpz_tdiv_qr(W, W2, T1, B);
        expect("divmod q (a b + small)", W, &c, T1, B);
        expect("divmod r (a b + small)", W2, &d, T1, B);
    }

    /* Euclid */
    bi_gcd(&c, &a, &b); mpz_gcd(W, A, B); expect("gcd", W, &c, A, B);
    bi_xgcd(&c, &d, &f, &a, &b);
    expect("xgcd g", W, &c, A, B);
    {
        mpz_t X, Y;
        mpz_inits(X, Y, NULL);
        to_mpz(X, &d);
        to_mpz(Y, &f);
        mpz_mul(X, X, A);
        mpz_addmul(X, Y, B);                     /* a x + b y */
        checks++;
        if (mpz_cmp(X, W) != 0) {
            failures++;
            gmp_fprintf(stderr, "FAIL xgcd identity a=%#Zx b=%#Zx\n", A, B);
        }
        mpz_clears(X, Y, NULL);
    }
    if (mpz_sgn(B)) {
        mpz_abs(M, B);
        from_mpz(&m, M);
        int ok = bi_invmod(&c, &a, &m);
        int want = mpz_invert(W, A, M) != 0 || mpz_cmp_ui(M, 1) == 0;
        if (mpz_cmp_ui(M, 1) == 0)
            mpz_set_ui(W, 0);
        checks++;
        if (ok != want) {
            failures++;
            gmp_fprintf(stderr, "FAIL invmod existence a=%#Zx m=%#Zx\n", A, M);
        } else if (ok) {
            expect("invmod", W, &c, A, M);
        }
    }

    /* shifts: a 2^k and floor(a / 2^k) */
    static const size_t KS[] = {0, 1, 63, 64, 65, 127, 128, 129, 1000};
    size_t k = urand(2) ? KS[urand(9)] : urand(300);
    bi_shl(&c, &a, k); mpz_mul_2exp(W, A, k); expect("shl", W, &c, A, A);
    bi_shr(&c, &a, k); mpz_fdiv_q_2exp(W, A, k); expect("shr", W, &c, A, A);

    /* Montgomery: odd m > 0 */
    rand_mpz(M, 1 + rand_limbs(80), 0);
    mpz_setbit(M, 0);
    from_mpz(&m, M);
    bi_mont ctx;
    if (bi_mont_init(&ctx, &m) != 0) {
        failures++;
        fprintf(stderr, "FAIL mont_init on an odd modulus\n");
    } else {
        size_t rb = bi_mont_rbits(&ctx);
        /* redc: c 2^rb == t (mod m), 0 <= c < m, for 0 <= t < m^2 */
        mpz_mul(T1, M, M);
        mpz_urandomm(T1, rs, T1);
        from_mpz(&f, T1);
        bi_mont_redc(&ctx, &c, &f);
        to_mpz(W, &c);
        mpz_mul_2exp(W2, W, rb);
        checks++;
        if (mpz_sgn(W) < 0 || mpz_cmp(W, M) >= 0 || !mpz_congruent_p(W2, T1, M)) {
            failures++;
            gmp_fprintf(stderr, "FAIL mont_redc t=%#Zx m=%#Zx\n", T1, M);
        }
        /* mont_mul through the Montgomery form gives a b mod m */
        bi_mont_to(&ctx, &d, &a);
        bi_mont_to(&ctx, &f, &b);
        bi_mont_mul(&ctx, &c, &d, &f);
        bi_mont_from(&ctx, &c, &c);
        mpz_mul(W, A, B);
        mpz_mod(W, W, M);
        expect("mont_mul", W, &c, A, B);
        bi_mont_sqr(&ctx, &c, &d);
        bi_mont_from(&ctx, &c, &c);
        mpz_mul(W, A, A);
        mpz_mod(W, W, M);
        expect("mont_sqr", W, &c, A, M);
        bi_mont_free(&ctx);
    }

    /* modular exponentiation: odd and even m, m = 1, e = 0 */
    static const unsigned QS[] = {2, 4, 8, 16, 32, 256};
    rand_mpz(M, 1 + urand(24), 0);
    if (urand(8) == 0)
        mpz_set_ui(M, 1 + urand(3));
    if (mpz_sgn(M) == 0)
        mpz_set_ui(M, 1);
    rand_mpz(E, urand(8), 0);
    from_mpz(&m, M);
    from_mpz(&e, E);
    mpz_powm(W, A, E, M);
    int method;
    bi_powmod_binary(&c, &a, &e, &m, &method); expect("powmod_binary", W, &c, A, M);
    bi_powmod_qary(&c, &a, &e, &m, QS[urand(6)], &method); expect("powmod_qary", W, &c, A, M);

    /* plain exponentiation, small exponents */
    unsigned long ee = urand(12);
    rand_mpz(T1, urand(4), 1);
    from_mpz(&f, T1);
    bi_set_si(&e, (long long)ee);
    mpz_pow_ui(W, T1, ee);
    bi_pow_binary(&c, &f, &e); expect("pow_binary", W, &c, T1, T1);
    bi_pow_qary(&c, &f, &e, QS[urand(6)]); expect("pow_qary", W, &c, T1, T1);

    mpz_clears(A, B, M, E, W, W2, T1, NULL);
    bi_free(&a); bi_free(&b); bi_free(&m); bi_free(&e); bi_free(&c); bi_free(&d); bi_free(&f);
}

/* Fixed corner cases that random operands hit rarely. */
static void corners(void)
{
    static const char *vals[] = {
        "0x0", "0x1", "-0x1", "0xffffffffffffffff", "-0xffffffffffffffff", "0x10000000000000000",
        "0xffffffffffffffffffffffffffffffff", "0x8000000000000000", "-0x8000000000000000",
        "0x80000000000000000000000000000000ffffffffffffffff",
    };
    size_t nv = sizeof vals / sizeof *vals;
    mpz_t A, B, W, W2;
    bigint a, b, q, r;
    mpz_inits(A, B, W, W2, NULL);
    bi_init(&a); bi_init(&b); bi_init(&q); bi_init(&r);
    for (size_t i = 0; i < nv; i++) {
        for (size_t j = 0; j < nv; j++) {
            bi_from_hex(&a, vals[i]);
            bi_from_hex(&b, vals[j]);
            to_mpz(A, &a);
            to_mpz(B, &b);
            bi_add(&q, &a, &b); mpz_add(W, A, B); expect("corner add", W, &q, A, B);
            bi_sub(&q, &a, &b); mpz_sub(W, A, B); expect("corner sub", W, &q, A, B);
            bi_mul(&q, &a, &b); mpz_mul(W, A, B); expect("corner mul", W, &q, A, B);
            if (mpz_sgn(B)) {
                bi_divmod(&q, &r, &a, &b);
                mpz_tdiv_qr(W, W2, A, B);
                expect("corner q", W, &q, A, B);
                expect("corner r", W2, &r, A, B);
            }
        }
    }
    mpz_clears(A, B, W, W2, NULL);
    bi_free(&a); bi_free(&b); bi_free(&q); bi_free(&r);
}

int main(int argc, char **argv)
{
    unsigned long seed = argc > 1 ? strtoul(argv[1], NULL, 10) : 1;
    unsigned long rounds = argc > 2 ? strtoul(argv[2], NULL, 10) : 200;
    gmp_randinit_default(rs);
    gmp_randseed_ui(rs, seed);
    unsigned long addbacks = 0, qmax = 0;
    ln_div_addbacks = ln_div_qhat_max = 0;
    corners();
    for (unsigned long i = 0; i < rounds; i++)
        round_once();
    addbacks += ln_div_addbacks;
    qmax += ln_div_qhat_max;
    printf("checks=%lu failures=%lu addbacks=%lu qhat_max=%lu\n", checks, failures, addbacks, qmax);
    gmp_randclear(rs);
    return failures != 0;
}
