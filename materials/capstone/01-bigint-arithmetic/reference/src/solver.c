/*
 * solver.c — `bigint-solver`: the JSON-lines front end of the library (bench contract,
 * see ../README.md and materials/capstone/README.md).
 *
 * Each stdin line is a request {"id": ..., "input": {"op": "...", ...}}; each gets one
 * stdout line {"id": ..., "output": {...}[, "extra": {...}]} or {"id": ..., "error": "..."},
 * flushed at once. Numbers are hex strings with an optional sign ("-0x1f"); small
 * integers (k, q, repeat, threshold) are JSON numbers. A JSON integer is also accepted
 * for a bigint field.
 *
 * "repeat": R (default 1) runs the operation R times on the same operands and answers
 * the last result, so that the per-operation time is wall / R even for operations far
 * below the timer resolution. One-time set-up (parsing, the Montgomery context of
 * remark 3 and conversions into Montgomery form) stays outside the loop.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bigint.h"
#include "json.h"

#define MAX_REPEAT 100000000LL
#define MAX_SHIFT (1LL << 24)          /* bits; keeps a typo from exhausting memory */
#define MAX_POW_BITS (1ULL << 24)      /* size of a plain (non-modular) power */

typedef struct {
    const jval *in;                    /* the "input" object */
    long long repeat;
    strbuf out, extra;                 /* the members of "output" / "extra" */
    char err[256];
} request;

/* ---------------------------------------------------------------- input ----------- */

static int fail(request *rq, const char *fmt, const char *arg)
{
    snprintf(rq->err, sizeof rq->err, fmt, arg);
    return -1;
}

/* A required bigint field: a hex string (or a JSON integer). */
static int get_big(request *rq, const char *key, bigint *x)
{
    const jval *v = json_get(rq->in, key);
    if (!v)
        return fail(rq, "missing field '%s'", key);
    if (v->type == J_STRING) {
        if (strlen(v->str) != v->len || bi_from_hex(x, v->str) != 0)
            return fail(rq, "field '%s': not a hex number", key);
        return 0;
    }
    long long i;
    if (json_int(v, -0x7fffffffffffffffLL, 0x7fffffffffffffffLL, &i) == 0) {
        bi_set_si(x, i);
        return 0;
    }
    return fail(rq, "field '%s': expected a hex string", key);
}

/* An integer field in [lo, hi]; `def` if absent (def < lo: required). */
static int get_int(request *rq, const char *key, long long lo, long long hi, long long def,
                   long long *out)
{
    const jval *v = json_get(rq->in, key);
    if (!v) {
        if (def < lo)
            return fail(rq, "missing field '%s'", key);
        *out = def;
        return 0;
    }
    if (json_int(v, lo, hi, out) != 0) {
        snprintf(rq->err, sizeof rq->err, "field '%s': expected an integer in [%lld, %lld]",
                 key, lo, hi);
        return -1;
    }
    return 0;
}

/* ---------------------------------------------------------------- output ---------- */

static void put_key(strbuf *b, const char *key)
{
    if (b->len)
        sb_putn(b, ",", 1);
    sb_json_string(b, key);
    sb_putn(b, ":", 1);
}

static void put_big(strbuf *b, const char *key, const bigint *x)
{
    char *h = bi_to_hex(x);
    put_key(b, key);
    sb_json_string(b, h);
    free(h);
}

static void put_ull(strbuf *b, const char *key, unsigned long long v)
{
    char num[32];
    snprintf(num, sizeof num, "%llu", v);
    put_key(b, key);
    sb_puts(b, num);
}

static void put_raw(strbuf *b, const char *key, const char *json)
{
    put_key(b, key);
    sb_puts(b, json);
}

/* ---------------------------------------------------------------- operations ------ */

#define REPEAT(rq) for (long long rep_ = 0; rep_ < (rq)->repeat; rep_++)

typedef int (*op_fn)(request *rq, const char *op, bigint *v);   /* v: 8 scratch bigints */

/* add, sub, mul_school, mul_karatsuba, mul, sqr, sqr_school: c */
static int op_ring(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *b = &v[1], *c = &v[2];
    int unary = strncmp(op, "sqr", 3) == 0;
    long long T = 0;
    if (get_big(rq, "a", a) || (!unary && get_big(rq, "b", b)))
        return -1;
    if (!strcmp(op, "mul_karatsuba") &&
        get_int(rq, "threshold", 2, 1 << 20, KARATSUBA_THRESHOLD, &T))
        return -1;
    if (!strcmp(op, "sqr") && get_int(rq, "threshold", 2, 1 << 20, KARATSUBA_SQR_THRESHOLD, &T))
        return -1;
    if (!strcmp(op, "add"))                REPEAT(rq) bi_add(c, a, b);
    else if (!strcmp(op, "sub"))           REPEAT(rq) bi_sub(c, a, b);
    else if (!strcmp(op, "mul_school"))    REPEAT(rq) bi_mul_school(c, a, b);
    else if (!strcmp(op, "mul_karatsuba")) REPEAT(rq) bi_mul_karatsuba(c, a, b, (size_t)T);
    else if (!strcmp(op, "mul"))           REPEAT(rq) bi_mul(c, a, b);
    else if (!strcmp(op, "sqr_school"))    REPEAT(rq) bi_sqr_school(c, a);
    else                                   REPEAT(rq) bi_sqr_karatsuba(c, a, (size_t)T);
    put_big(&rq->out, "c", c);
    return 0;
}

/* divmod: q, r (truncated division); mod: r in [0, |b|) */
static int op_div(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *b = &v[1], *q = &v[2], *r = &v[3];
    if (get_big(rq, "a", a) || get_big(rq, "b", b))
        return -1;
    if (bi_is_zero(b))
        return fail(rq, "%s: division by zero", op);
    int full = !strcmp(op, "divmod");
    REPEAT(rq) {
        ln_div_addbacks = ln_div_qhat_max = 0;  /* statistics of the last repetition */
        if (full)
            bi_divmod(q, r, a, b);
        else
            bi_mod(r, a, b);
    }
    if (full)
        put_big(&rq->out, "q", q);
    put_big(&rq->out, "r", r);
    put_ull(&rq->extra, "addbacks", ln_div_addbacks);
    put_ull(&rq->extra, "qhat_max", ln_div_qhat_max);
    return 0;
}

/* gcd: g; xgcd: g, x, y with a x + b y = g; inv: a^{-1} mod m or null */
static int op_gcd(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *b = &v[1], *g = &v[2], *x = &v[3], *y = &v[4];
    if (!strcmp(op, "inv")) {
        if (get_big(rq, "a", a) || get_big(rq, "m", b))
            return -1;
        if (bi_sign(b) <= 0)
            return fail(rq, "%s: the modulus must be positive", op);
        int ok = 0;
        REPEAT(rq) ok = bi_invmod(g, a, b);
        if (ok)
            put_big(&rq->out, "inv", g);
        else
            put_raw(&rq->out, "inv", "null");
        return 0;
    }
    if (get_big(rq, "a", a) || get_big(rq, "b", b))
        return -1;
    if (!strcmp(op, "gcd")) {
        REPEAT(rq) bi_gcd(g, a, b);
        put_big(&rq->out, "g", g);
    } else {
        REPEAT(rq) bi_xgcd(g, x, y, a, b);
        put_big(&rq->out, "g", g);
        put_big(&rq->out, "x", x);
        put_big(&rq->out, "y", y);
    }
    return 0;
}

/* shl: a 2^k; shr: floor(a / 2^k) */
static int op_shift(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *c = &v[1];
    long long k;
    if (get_big(rq, "a", a) || get_int(rq, "k", 0, MAX_SHIFT, -1, &k))
        return -1;
    if (!strcmp(op, "shl"))
        REPEAT(rq) bi_shl(c, a, (size_t)k);
    else
        REPEAT(rq) bi_shr(c, a, (size_t)k);
    put_big(&rq->out, "c", c);
    return 0;
}

/* mont_redc: c = t R^{-1} mod m and r_bits = log2 R;
 * mont_mul: c = a b mod m through Montgomery multiplication (the loop times one
 * multiplication of operands already in Montgomery form); extra: REDC(a b) = a b R^-1. */
static int op_mont(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *b = &v[1], *m = &v[2], *c = &v[3], *am = &v[4], *bm = &v[5];
    bi_mont ctx;
    int redc = !strcmp(op, "mont_redc");
    if (get_big(rq, redc ? "t" : "a", a) || (!redc && get_big(rq, "b", b)) || get_big(rq, "m", m))
        return -1;
    if (bi_mont_init(&ctx, m) != 0)
        return fail(rq, "%s: Montgomery arithmetic needs an odd modulus m > 0", op);
    if (redc) {
        REPEAT(rq) bi_mont_redc(&ctx, c, a);
        put_big(&rq->out, "c", c);
        put_ull(&rq->out, "r_bits", bi_mont_rbits(&ctx));
    } else {
        bi_mont_to(&ctx, am, a);                /* a R mod m */
        bi_mont_to(&ctx, bm, b);
        REPEAT(rq) bi_mont_mul(&ctx, c, am, bm);  /* (a b) R mod m */
        bi_mont_from(&ctx, c, c);
        put_big(&rq->out, "c", c);
        bi_mod(am, a, m);
        bi_mod(bm, b, m);
        bi_mont_mul(&ctx, c, am, bm);           /* REDC(a b) */
        put_big(&rq->extra, "mont", c);
        put_ull(&rq->extra, "r_bits", bi_mont_rbits(&ctx));
    }
    bi_mont_free(&ctx);
    return 0;
}

/* pow_binary, pow_qary (q): a^e; powmod_binary, powmod_qary (q): a^e mod m */
static int op_pow(request *rq, const char *op, bigint *v)
{
    bigint *a = &v[0], *e = &v[1], *m = &v[2], *c = &v[3];
    int modular = !strncmp(op, "powmod", 6), qary = strstr(op, "qary") != NULL;
    long long q = 2;
    if (get_big(rq, "a", a) || get_big(rq, "e", e) || (modular && get_big(rq, "m", m)))
        return -1;
    if (qary && get_int(rq, "q", 2, 256, -1, &q))
        return -1;
    if (qary && (q & (q - 1)))
        return fail(rq, "%s: q must be a power of two (2, 4, ..., 256)", op);
    if (bi_sign(e) < 0)
        return fail(rq, "%s: negative exponent", op);
    if (modular && bi_sign(m) <= 0)
        return fail(rq, "%s: the modulus must be positive", op);
    /* A plain power has about bitlen(a) * e bits: refuse absurd sizes (|a| <= 1 is fine). */
    if (!modular && bi_bitlen(a) > 1 &&
        (bi_bitlen(e) > 32 || (unsigned long long)bi_bitlen(a) * (e->n ? e->d[0] : 0) > MAX_POW_BITS))
        return fail(rq, "%s: the result would be too large; use powmod", op);
    int method = 0;
    if (!modular && !qary)     REPEAT(rq) bi_pow_binary(c, a, e);
    else if (!modular)         REPEAT(rq) bi_pow_qary(c, a, e, (unsigned)q);
    else if (!qary)            REPEAT(rq) bi_powmod_binary(c, a, e, m, &method);
    else                       REPEAT(rq) bi_powmod_qary(c, a, e, m, (unsigned)q, &method);
    put_big(&rq->out, "c", c);
    if (modular)
        put_raw(&rq->extra, "method", method == POW_MONTGOMERY ? "\"montgomery\"" : "\"division\"");
    return 0;
}

static const struct {
    const char *name;
    op_fn fn;
} OPS[] = {
    {"add", op_ring}, {"sub", op_ring}, {"mul_school", op_ring}, {"mul_karatsuba", op_ring},
    {"mul", op_ring}, {"sqr", op_ring}, {"sqr_school", op_ring},
    {"divmod", op_div}, {"mod", op_div},
    {"gcd", op_gcd}, {"xgcd", op_gcd}, {"inv", op_gcd},
    {"shl", op_shift}, {"shr", op_shift},
    {"mont_redc", op_mont}, {"mont_mul", op_mont},
    {"pow_binary", op_pow}, {"pow_qary", op_pow}, {"powmod_binary", op_pow}, {"powmod_qary", op_pow},
};

/* ---------------------------------------------------------------- main loop ------- */

static int run(request *rq)
{
    const jval *op = json_get(rq->in, "op");
    if (!op || op->type != J_STRING)
        return fail(rq, "missing \"op\" (a string)%s", "");
    if (get_int(rq, "repeat", 1, MAX_REPEAT, 1, &rq->repeat))
        return -1;
    for (size_t i = 0; i < sizeof OPS / sizeof *OPS; i++) {
        if (strcmp(op->str, OPS[i].name) == 0) {
            bigint v[8];
            for (int k = 0; k < 8; k++)
                bi_init(&v[k]);
            int rc = OPS[i].fn(rq, OPS[i].name, v);
            for (int k = 0; k < 8; k++)
                bi_free(&v[k]);
            return rc;
        }
    }
    return fail(rq, "unknown op '%.100s'", op->str);
}

static void answer(const char *line, size_t len)
{
    jval root;
    char perr[160];
    strbuf resp;
    request rq = {0};
    sb_init(&resp);
    sb_init(&rq.out);
    sb_init(&rq.extra);

    int ok = json_parse(line, len, &root, perr, sizeof perr) == 0;
    const jval *id = ok ? json_get(&root, "id") : NULL;
    sb_puts(&resp, "{\"id\":");
    if (id)
        sb_putn(&resp, id->raw, id->rawlen);
    else
        sb_puts(&resp, "null");

    if (!ok) {
        snprintf(rq.err, sizeof rq.err, "bad JSON: %s", perr);
    } else if (root.type != J_OBJECT || !(rq.in = json_get(&root, "input"))
               || rq.in->type != J_OBJECT) {
        snprintf(rq.err, sizeof rq.err, "expected {\"id\": ..., \"input\": {...}}");
        ok = 0;
    } else {
        ok = run(&rq) == 0;
    }
    if (ok) {
        sb_puts(&resp, ",\"output\":{");
        if (rq.out.len)
            sb_putn(&resp, rq.out.s, rq.out.len);
        sb_puts(&resp, "}");
        if (rq.extra.len) {
            sb_puts(&resp, ",\"extra\":{");
            sb_putn(&resp, rq.extra.s, rq.extra.len);
            sb_puts(&resp, "}");
        }
    } else {
        sb_puts(&resp, ",\"error\":");
        sb_json_string(&resp, rq.err);
    }
    sb_puts(&resp, "}\n");
    fwrite(resp.s, 1, resp.len, stdout);
    fflush(stdout);
    json_free(&root);
    sb_free(&resp);
    sb_free(&rq.out);
    sb_free(&rq.extra);
}

int main(void)
{
    char *line = NULL;
    size_t cap = 0;
    ssize_t len;
    while ((len = getline(&line, &cap, stdin)) != -1) {
        while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r'))
            line[--len] = '\0';
        size_t i = 0;
        while (i < (size_t)len && (line[i] == ' ' || line[i] == '\t'))
            i++;
        if (i == (size_t)len)
            continue;                    /* blank lines are not requests */
        answer(line, (size_t)len);
    }
    free(line);
    return 0;
}
