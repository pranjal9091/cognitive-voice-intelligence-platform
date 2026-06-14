# ==============================================================================
# Dockerfile - PostgreSQL Database
# ==============================================================================

FROM postgres:15-alpine

# Copy schema.sql to the postgres initdb directory
# Scripts in /docker-entrypoint-initdb.d/ are executed in alphabetical order
# when the container starts for the first time.
COPY database/schema.sql /docker-entrypoint-initdb.d/10_schema.sql
