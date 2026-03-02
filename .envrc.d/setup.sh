# Working directories for intermediate artifacts and final output.
# Both are gitignored — transcripts are disposable, summaries are local-only.
export TRANSCRIPTS_DIR="$PWD/transcripts"
export SUMMARIES_DIR="$PWD/summaries"

mkdir -p "$TRANSCRIPTS_DIR" "$SUMMARIES_DIR"
