#!/usr/bin/env bash
set -euo pipefail

domain="tg2ding.top"
www_domain="www.tg2ding.top"
expected_ip="46.8.101.74"
certificate="/etc/letsencrypt/live/${domain}/fullchain.pem"

if [[ -f "${certificate}" ]]; then
    exit 0
fi

resolved_ip="$(getent ahostsv4 "${domain}" 2>/dev/null | awk 'NR == 1 { print $1 }' || true)"
if [[ "${resolved_ip}" != "${expected_ip}" ]]; then
    exit 0
fi

certbot --nginx \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --redirect \
    -d "${domain}" \
    -d "${www_domain}"

nginx -t
systemctl reload nginx
