#!/usr/bin/env bash
# Refresh official nightly; Python isolation prevents Nix PYTHONPATH shadowing it.
exec uv --no-config tool run --isolated --refresh \
  --from 'yt-dlp[default] @ https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.tar.gz' \
  python -I -m yt_dlp --js-runtimes node "$@"
