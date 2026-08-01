#!/bin/sh
set -e

KEY=${METRICS_API_KEY}
KEY=${KEY#\"}
KEY=${KEY%\"}

sed "s/\${METRICS_API_KEY}/${KEY}/g" /etc/prometheus/prometheus.yml > /tmp/prometheus.yml

exec prometheus --config.file=/tmp/prometheus.yml
