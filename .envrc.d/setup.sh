# Gitignored workspace for inputs, intermediates, outputs, and Whisper models.
export INBOX_DIR="$PWD/local/inbox"
export TRANSCRIPTS_DIR="$PWD/local/transcripts"
export SUMMARIES_DIR="$PWD/local/summaries"
export MODELS_DIR="$PWD/local/models"

mkdir -p "$INBOX_DIR" "$TRANSCRIPTS_DIR" "$SUMMARIES_DIR" "$MODELS_DIR"
