#!/bin/sh

set -eu

exec /usr/sbin/nsenter \
  --target 1 \
  --mount \
  --uts \
  --ipc \
  --net \
  --pid \
  --root=/proc/1/root \
  --wd=/ \
  /usr/bin/env \
    HOME=/root \
    USER=root \
    LOGNAME=root \
    SHELL=/bin/bash \
    /usr/bin/cockpit-bridge
