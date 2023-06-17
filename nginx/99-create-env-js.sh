#!/bin/sh

set -e

cat << EOF > /usr/share/nginx/js/env.js
const eeapi_url = '${eeapi_url}';
const eeapi_session = '${eeapi_session}';
EOF
