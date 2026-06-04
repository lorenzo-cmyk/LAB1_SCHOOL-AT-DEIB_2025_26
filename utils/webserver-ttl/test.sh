#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (needs iptables + raw sockets)." >&2
    exec sudo "$0" "$@"
fi

PORT=2000
SERVER_PID=""
PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null || true
    iptables -t mangle -D OUTPUT -p tcp --dport "$PORT" -j TTL --ttl-set 128 2>/dev/null || true
}
trap cleanup EXIT

pass() { ((PASS++)); echo "  PASS: $1"; }
fail() { ((FAIL++)); echo "  FAIL: $1"; }

check_proof() {
    local body="$1" label="$2"
    if (( ${#body} < 13 )); then
        fail "$label: body too short for proof check"
        return
    fi
    local sum
    sum=$(echo "${body:0:13}" | od -An -tuC | awk '{for(i=1;i<=NF;i++)s+=$i}END{print s}')
    if (( sum % 7 == 0 )); then
        pass "$label: ASCII sum ($sum) divisible by 7"
    else
        fail "$label: sum $sum not divisible by 7 (remainder $((sum % 7)))"
    fi
}

# ── ensure Go is installed ──────────────────────────────────────────────────
if ! command -v go &>/dev/null; then
    echo "===> Installing Go"
    apt-get update -qq
    apt-get install -y -qq golang-go
fi

# ── build ────────────────────────────────────────────────────────────────────
echo "===> Building"
cd "$SCRIPT_DIR"
CGO_ENABLED=0 go build -o webserver-ttl .
file webserver-ttl | grep -q "statically linked" && pass "static binary" || fail "not a static binary"

# ── start server ─────────────────────────────────────────────────────────────
echo "===> Starting server on :$PORT"
./webserver-ttl &
SERVER_PID=$!
sleep 0.5

# verify it's running
kill -0 "$SERVER_PID" 2>/dev/null && pass "server started (pid $SERVER_PID)" || { fail "server not running"; exit 1; }

# ── test 1: default TTL (64) should be denied ────────────────────────────────
echo "===> Test 1 — default TTL (64 < 100) → expect 403 ACCESS_DENIED"
RESP=$(curl -s --max-time 2 "http://127.0.0.1:$PORT/test" 2>/dev/null || true)
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:$PORT/test" 2>/dev/null || true)
if [[ "$CODE" == "403" ]]; then
    pass "HTTP 403 returned"
else
    fail "expected HTTP 403, got $CODE"
fi
if [[ "$RESP" == "ACCESS_DENIED" ]]; then
    pass "body is ACCESS_DENIED"
else
    fail "body is '$RESP', expected ACCESS_DENIED"
fi

# ── test 2: set TTL=128 via iptables mangle ──────────────────────────────────
echo "===> Test 2 — mangled TTL (128 >= 100) → expect 200 + TTL suffix"
iptables -t mangle -A OUTPUT -p tcp --dport "$PORT" -j TTL --ttl-set 128

BODY=$(curl -s --max-time 2 "http://127.0.0.1:$PORT/any-endpoint" 2>/dev/null || true)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:$PORT/any-endpoint" 2>/dev/null || true)

if [[ "$HTTP_CODE" == "200" ]]; then
    pass "HTTP 200 returned"
else
    fail "expected HTTP 200, got $HTTP_CODE"
fi

LEN=${#BODY}
if [[ "$LEN" == "16" ]]; then
    pass "body length is 16 chars"
else
    fail "body length is $LEN, expected 16"
fi

if [[ "$BODY" == *TTL ]]; then
    pass "body ends with 'TTL'"
else
    fail "body does not end with 'TTL' — got: $BODY"
fi

# verify it's printable ASCII
if echo "$BODY" | grep -qP '^[\x20-\x7E]{16}$'; then
    pass "body is printable ASCII"
else
    fail "body contains non-printable chars"
fi

# verify sum of first 13 chars is divisible by 7 (proof property)
check_proof "$BODY" "proof-on-TTL-200"

# ── test 3: different endpoints and methods ───────────────────────────────────
echo "===> Test 3 — POST /foo should also work"
BODY2=$(curl -s -X POST --max-time 2 "http://127.0.0.1:$PORT/foo" 2>/dev/null || true)
if [[ "$BODY2" == *TTL && ${#BODY2} == 16 ]]; then
    pass "POST /foo → 16-char body ending with TTL"
else
    fail "POST /foo unexpected body: $BODY2"
fi
check_proof "$BODY2" "proof-on-POST"

# ── test 4: remove mangle rule, TTL back to 64 → denied again ────────────────
echo "===> Test 4 — remove mangle, back to TTL 64 → expect 403"
iptables -t mangle -D OUTPUT -p tcp --dport "$PORT" -j TTL --ttl-set 128

RESP2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:$PORT/test" 2>/dev/null || true)
if [[ "$RESP2" == "403" ]]; then
    pass "403 again after removing TTL mangle"
else
    fail "expected 403, got $RESP2"
fi

# ── test 5: each response is random ──────────────────────────────────────────
echo "===> Test 5 — responses are random"
iptables -t mangle -A OUTPUT -p tcp --dport "$PORT" -j TTL --ttl-set 128
B1=$(curl -s --max-time 2 "http://127.0.0.1:$PORT/a" 2>/dev/null || true)
B2=$(curl -s --max-time 2 "http://127.0.0.1:$PORT/b" 2>/dev/null || true)
if [[ "$B1" != "$B2" && -n "$B1" && -n "$B2" ]]; then
    pass "two requests returned different random strings"
else
    fail "responses not random (got '$B1' and '$B2')"
fi
check_proof "$B1" "proof-on-random-1"
check_proof "$B2" "proof-on-random-2"

# ── summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo " Results:  $PASS passed,  $FAIL failed"
echo "========================================="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
