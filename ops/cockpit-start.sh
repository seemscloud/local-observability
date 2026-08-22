#!/bin/sh

set -eu

eval "$(ssh-agent -s)" >/dev/null
ssh-add /run/secrets/cockpit-ssh-key >/dev/null

exec /container/label-run --no-tls
