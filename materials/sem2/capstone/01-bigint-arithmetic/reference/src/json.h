/*
 * json.h — a small, strict JSON (RFC 8259) parser and a string writer, enough for the
 * solver's JSON-lines protocol. Values form a tree owned by the root; `raw` points into
 * the source text, so a value (e.g. a request id) can be echoed back verbatim.
 */
#ifndef JSON_H
#define JSON_H

#include <stddef.h>

typedef enum { J_NULL, J_FALSE, J_TRUE, J_NUMBER, J_STRING, J_ARRAY, J_OBJECT } jtype;

typedef struct jval {
    jtype type;
    const char *raw;          /* the value's text in the source */
    size_t rawlen;
    char *str;                /* J_STRING: decoded, NUL-terminated (UTF-8) */
    size_t len;               /* J_STRING: decoded length (may contain NUL) */
    size_t count;             /* J_ARRAY / J_OBJECT: number of items */
    char **keys;              /* J_OBJECT: decoded member names */
    struct jval *items;       /* J_ARRAY / J_OBJECT: the items / member values */
} jval;

/* Parse exactly one JSON value (surrounding whitespace allowed). Returns 0 on success;
 * on failure -1 and a message in err. Free with json_free in both cases. */
int json_parse(const char *text, size_t len, jval *out, char *err, size_t errlen);
void json_free(jval *v);

/* Member lookup in an object (the last one wins for duplicate names), or NULL. */
const jval *json_get(const jval *obj, const char *key);

/* A J_NUMBER that is an integer in [lo, hi] (no fraction or exponent). 0 ok, -1 not. */
int json_int(const jval *v, long long lo, long long hi, long long *out);

/* Append s as a JSON string literal (with escapes) to a growing buffer. */
typedef struct {
    char *s;
    size_t len, cap;
} strbuf;
void sb_init(strbuf *b);
void sb_free(strbuf *b);
void sb_putn(strbuf *b, const char *s, size_t n);
void sb_puts(strbuf *b, const char *s);
void sb_json_string(strbuf *b, const char *s);

#endif
