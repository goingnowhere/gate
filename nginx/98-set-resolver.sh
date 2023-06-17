#!/bin/sh

nameserver=$(cat /etc/resolv.conf | grep nameserver | head -1 | cut -d' ' -f2)

cat << EOF > /etc/nginx/nginx.resolv.conf
resolver ${nameserver} valid=30s ipv6=off;
EOF
