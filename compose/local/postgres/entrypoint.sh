#!/bin/bash
set -e

# Extract postgres_password
POSTGRES_PASSWORD=$(grep postgres_password /passwords/password.txt | cut -d '=' -f2)
echo "postgres_password: $POSTGRES_PASSWORD"

# Export it so that it can be used by the postgres process
export POSTGRES_PASSWORD

# Call the original docker-entrypoint.sh with any arguments passed in
exec docker-entrypoint.sh postgres "$@"
