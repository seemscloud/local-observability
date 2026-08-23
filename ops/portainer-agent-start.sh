#!/bin/sh

set -eu

AGENT_SECRET="$(cat /run/secrets/portainer-agent-secret)"
export AGENT_SECRET

exec /app/agent "$@"
