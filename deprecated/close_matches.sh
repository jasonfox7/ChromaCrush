#!/bin/bash
# Close all active matches in the database.
# Usage: bash close_matches.sh

docker exec chromacrush-postgres psql -U chromacrush -d chromacrush -c \
  "UPDATE matches SET status = 'completed', completed_at = NOW() WHERE status IN ('pending', 'in_progress');"
