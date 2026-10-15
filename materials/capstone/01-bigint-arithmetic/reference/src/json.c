/*
 * json.c — recursive-descent JSON parser (strict RFC 8259 grammar, nesting depth
 * limited) and a string writer. See json.h.
 */
#include "json.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_DEPTH 64

typedef struct {
    const char *p, *end;
    char *err;
    size_t errlen;
    int failed;
} parser;

static void fail(parser *ps, const char *fmt, ...)
{
    if (ps->failed)
        return;
    ps->failed = 1;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(ps->err, ps->errlen, fmt, ap);
    va_end(ap);
}

static void *xalloc(parser *ps, size_t bytes)
{
    void *p = malloc(bytes ? bytes : 1);
    if (!p)
        fail(ps, "out of memory");
    return p;
}

static void skip_ws(parser *ps)
{
    while (ps->p < ps->end && (*ps->p == ' ' || *ps->p == '\t' || *ps->p == '\n' || *ps->p == '\r'))
        ps->p++;
}

static int literal(parser *ps, const char *word)
{
    size_t n = strlen(word);
    if ((size_t)(ps->end - ps->p) >= n && memcmp(ps->p, word, n) == 0) {
        ps->p += n;
        return 1;
    }
    return 0;
}

static int hex4(const char *s, unsigned *out)
{
    unsigned v = 0;
    for (int i = 0; i < 4; i++) {
        char c = s[i];
        v <<= 4;
        if (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
        else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') v |= (unsigned)(c - 'A' + 10);
        else return -1;
    }
    *out = v;
    return 0;
}

static size_t put_utf8(char *o, unsigned cp)
{
    if (cp < 0x80) { o[0] = (char)cp; return 1; }
    if (cp < 0x800) { o[0] = (char)(0xC0 | cp >> 6); o[1] = (char)(0x80 | (cp & 0x3F)); return 2; }
    if (cp < 0x10000) {
        o[0] = (char)(0xE0 | cp >> 12); o[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        o[2] = (char)(0x80 | (cp & 0x3F)); return 3;
    }
    o[0] = (char)(0xF0 | cp >> 18); o[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    o[2] = (char)(0x80 | ((cp >> 6) & 0x3F)); o[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}

/* A string literal at ps->p (the opening quote); the decoded text never exceeds the
 * source length, so one allocation of that size suffices. */
static char *parse_string(parser *ps, size_t *outlen)
{
    const char *start = ++ps->p;
    const char *q = start;
    while (q < ps->end && *q != '"') {
        if (*q == '\\')
            q++;
        q++;
    }
    if (q >= ps->end) {
        fail(ps, "unterminated string");
        return NULL;
    }
    char *out = xalloc(ps, (size_t)(q - start) + 1), *o = out;
    if (!out)
        return NULL;
    while (ps->p < ps->end && *ps->p != '"') {
        unsigned char c = (unsigned char)*ps->p++;
        if (c < 0x20) {
            fail(ps, "control character in string");
            break;
        }
        if (c != '\\') {
            *o++ = (char)c;
            continue;
        }
        if (ps->p >= ps->end) {
            fail(ps, "bad escape");
            break;
        }
        char e = *ps->p++;
        switch (e) {
        case '"': *o++ = '"'; break;
        case '\\': *o++ = '\\'; break;
        case '/': *o++ = '/'; break;
        case 'b': *o++ = '\b'; break;
        case 'f': *o++ = '\f'; break;
        case 'n': *o++ = '\n'; break;
        case 'r': *o++ = '\r'; break;
        case 't': *o++ = '\t'; break;
        case 'u': {
            unsigned cp, lo;
            if (ps->end - ps->p < 4 || hex4(ps->p, &cp)) {
                fail(ps, "bad \\u escape");
                break;
            }
            ps->p += 4;
            if (cp >= 0xD800 && cp < 0xDC00) {        /* a surrogate pair */
                if (ps->end - ps->p < 6 || ps->p[0] != '\\' || ps->p[1] != 'u'
                    || hex4(ps->p + 2, &lo) || lo < 0xDC00 || lo >= 0xE000) {
                    fail(ps, "bad surrogate pair");
                    break;
                }
                ps->p += 6;
                cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
            } else if (cp >= 0xDC00 && cp < 0xE000) {
                fail(ps, "lone low surrogate");
                break;
            }
            o += put_utf8(o, cp);    /* <= 6 source bytes -> <= 4 output bytes */
            break;
        }
        default:
            fail(ps, "bad escape \\%c", e);
        }
        if (ps->failed)
            break;
    }
    if (ps->failed) {
        free(out);
        return NULL;
    }
    ps->p++;                                     /* closing quote */
    *o = '\0';
    *outlen = (size_t)(o - out);
    return out;
}

static int is_digit(char c) { return c >= '0' && c <= '9'; }

static void parse_number(parser *ps)
{
    const char *p = ps->p;
    if (p < ps->end && *p == '-')
        p++;
    if (p < ps->end && *p == '0')
        p++;
    else if (p < ps->end && is_digit(*p))
        while (p < ps->end && is_digit(*p))
            p++;
    else {
        fail(ps, "bad number");
        return;
    }
    if (p < ps->end && *p == '.') {
        p++;
        if (p >= ps->end || !is_digit(*p)) {
            fail(ps, "bad number");
            return;
        }
        while (p < ps->end && is_digit(*p))
            p++;
    }
    if (p < ps->end && (*p == 'e' || *p == 'E')) {
        p++;
        if (p < ps->end && (*p == '+' || *p == '-'))
            p++;
        if (p >= ps->end || !is_digit(*p)) {
            fail(ps, "bad number");
            return;
        }
        while (p < ps->end && is_digit(*p))
            p++;
    }
    ps->p = p;
}

static void parse_value(parser *ps, jval *v, int depth);

/* Items of an array or object, collected in a growing array. */
static void parse_container(parser *ps, jval *v, int depth, int is_object)
{
    char close = is_object ? '}' : ']';
    size_t cap = 0;
    ps->p++;                                      /* '[' or '{' */
    skip_ws(ps);
    if (ps->p < ps->end && *ps->p == close) {
        ps->p++;
        return;
    }
    for (;;) {
        if (v->count == cap) {
            cap = cap ? cap * 2 : 4;
            jval *items = realloc(v->items, cap * sizeof *items);
            if (!items) {
                fail(ps, "out of memory");
                return;
            }
            v->items = items;
            if (is_object) {
                char **keys = realloc(v->keys, cap * sizeof *keys);
                if (!keys) {
                    fail(ps, "out of memory");
                    return;
                }
                v->keys = keys;
            }
        }
        jval *item = &v->items[v->count];
        memset(item, 0, sizeof *item);
        if (is_object) {
            v->keys[v->count] = NULL;
            skip_ws(ps);
            if (ps->p >= ps->end || *ps->p != '"') {
                fail(ps, "expected a member name");
                return;
            }
            size_t klen;
            char *key = parse_string(ps, &klen);
            if (!key)
                return;
            v->keys[v->count] = key;
            skip_ws(ps);
            if (ps->p >= ps->end || *ps->p != ':') {
                v->count++;
                fail(ps, "expected ':'");
                return;
            }
            ps->p++;
        }
        v->count++;
        parse_value(ps, item, depth + 1);
        if (ps->failed)
            return;
        skip_ws(ps);
        if (ps->p < ps->end && *ps->p == ',') {
            ps->p++;
            continue;
        }
        if (ps->p < ps->end && *ps->p == close) {
            ps->p++;
            return;
        }
        fail(ps, "expected ',' or '%c'", close);
        return;
    }
}

static void parse_value(parser *ps, jval *v, int depth)
{
    if (depth > MAX_DEPTH) {
        fail(ps, "nesting too deep");
        return;
    }
    skip_ws(ps);
    if (ps->p >= ps->end) {
        fail(ps, "unexpected end of input");
        return;
    }
    v->raw = ps->p;
    char c = *ps->p;
    if (c == '{') {
        v->type = J_OBJECT;
        parse_container(ps, v, depth, 1);
    } else if (c == '[') {
        v->type = J_ARRAY;
        parse_container(ps, v, depth, 0);
    } else if (c == '"') {
        v->type = J_STRING;
        v->str = parse_string(ps, &v->len);
    } else if (c == '-' || is_digit(c)) {
        v->type = J_NUMBER;
        parse_number(ps);
    } else if (literal(ps, "true")) {
        v->type = J_TRUE;
    } else if (literal(ps, "false")) {
        v->type = J_FALSE;
    } else if (literal(ps, "null")) {
        v->type = J_NULL;
    } else {
        fail(ps, "unexpected character '%c'", c);
    }
    v->rawlen = (size_t)(ps->p - v->raw);
}

int json_parse(const char *text, size_t len, jval *out, char *err, size_t errlen)
{
    parser ps = {text, text + len, err, errlen, 0};
    memset(out, 0, sizeof *out);
    if (errlen)
        err[0] = '\0';
    parse_value(&ps, out, 0);
    skip_ws(&ps);
    if (!ps.failed && ps.p != ps.end)
        fail(&ps, "trailing characters after the value");
    return ps.failed ? -1 : 0;
}

void json_free(jval *v)
{
    for (size_t i = 0; i < v->count; i++) {
        json_free(&v->items[i]);
        if (v->keys)
            free(v->keys[i]);
    }
    free(v->items);
    free(v->keys);
    free(v->str);
    memset(v, 0, sizeof *v);
}

const jval *json_get(const jval *obj, const char *key)
{
    if (!obj || obj->type != J_OBJECT)
        return NULL;
    for (size_t i = obj->count; i-- > 0;)
        if (obj->keys[i] && strcmp(obj->keys[i], key) == 0)
            return &obj->items[i];
    return NULL;
}

int json_int(const jval *v, long long lo, long long hi, long long *out)
{
    if (!v || v->type != J_NUMBER || v->rawlen > 20)
        return -1;
    char buf[24];
    memcpy(buf, v->raw, v->rawlen);
    buf[v->rawlen] = '\0';
    if (strpbrk(buf, ".eE"))
        return -1;
    char *end;
    long long x = strtoll(buf, &end, 10);
    if (*end || x < lo || x > hi)
        return -1;
    *out = x;
    return 0;
}

/* ---------------------------------------------------------------- writer ---------- */

void sb_init(strbuf *b)
{
    b->s = NULL;
    b->len = b->cap = 0;
}

void sb_free(strbuf *b)
{
    free(b->s);
    sb_init(b);
}

void sb_putn(strbuf *b, const char *s, size_t n)
{
    if (b->len + n + 1 > b->cap) {
        size_t cap = b->cap ? b->cap : 256;
        while (cap < b->len + n + 1)
            cap *= 2;
        char *p = realloc(b->s, cap);
        if (!p) {
            fprintf(stderr, "out of memory\n");
            abort();
        }
        b->s = p;
        b->cap = cap;
    }
    memcpy(b->s + b->len, s, n);
    b->len += n;
    b->s[b->len] = '\0';
}

void sb_puts(strbuf *b, const char *s) { sb_putn(b, s, strlen(s)); }

void sb_json_string(strbuf *b, const char *s)
{
    sb_putn(b, "\"", 1);
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        char esc[8];
        if (c == '"' || c == '\\') {
            esc[0] = '\\';
            esc[1] = (char)c;
            sb_putn(b, esc, 2);
        } else if (c < 0x20) {
            snprintf(esc, sizeof esc, "\\u%04x", c);
            sb_puts(b, esc);
        } else {
            sb_putn(b, (const char *)&c, 1);
        }
    }
    sb_putn(b, "\"", 1);
}
