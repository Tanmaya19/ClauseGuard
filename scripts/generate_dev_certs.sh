#!/usr/bin/env bash
# Generate a self-signed certificate for LOCAL TLS testing only.
#
# A self-signed certificate proves the TLS configuration works end to end.
# It is NOT a production certificate: browsers will warn, because nothing
# vouches for it. Production uses a CA-issued certificate — see
# docs/DEPLOYMENT.md.
#
# Usage:  bash scripts/generate_dev_certs.sh [output-dir]
set -euo pipefail

CERT_DIR="${1:-certs}"
DAYS=365

mkdir -p "$CERT_DIR"

# A config file rather than -subj and -addext, for two reasons:
#
#  1. Under Git Bash / MSYS on Windows, an argument beginning with "/" is
#     rewritten as a Windows path, so -subj "/C=IN/ST=..." arrives mangled and
#     openssl writes the key but never the certificate. A config file has no
#     leading-slash arguments to mangle.
#  2. -addext is not available on older openssl builds, whereas
#     req_extensions in a config file has worked for far longer.
#
# subjectAltName is required, not optional: browsers have ignored commonName
# for host matching since 2017, so a CN-only certificate fails verification
# even once trusted.
CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT

cat > "$CONFIG" <<'CONF'
[req]
distinguished_name = dn
x509_extensions    = v3_ext
prompt             = no

[dn]
C  = IN
ST = Tamil Nadu
L  = Chennai
O  = ClauseGuard (development)
CN = localhost

[v3_ext]
basicConstraints = critical, CA:FALSE
keyUsage         = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName   = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = clauseguard.local
IP.1  = 127.0.0.1
CONF

# Errors are deliberately NOT suppressed here. An earlier version sent stderr
# to /dev/null, which hid exactly this failure and left a key with no
# certificate beside it.
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -days "$DAYS" \
  -config "$CONFIG"

chmod 600 "$CERT_DIR/privkey.pem"

# Verify the pair actually matches before claiming success: a key written
# without its certificate is the failure mode this script already had once.
key_hash=$(openssl rsa  -in "$CERT_DIR/privkey.pem"   -noout -modulus | openssl sha256)
crt_hash=$(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -modulus | openssl sha256)
if [ "$key_hash" != "$crt_hash" ]; then
    echo "ERROR: the private key does not match the certificate." >&2
    exit 1
fi

echo
echo "Wrote a matching self-signed pair to $CERT_DIR/"
openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -subject -dates
openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -ext subjectAltName
echo
echo "Start the TLS stack with:"
echo "  docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build"
echo "Then open https://localhost and accept the browser warning."
