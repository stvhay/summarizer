#!/usr/bin/env python3
"""Offline preparation checks. Real ffmpeg/ffprobe; no existing local media."""
import hashlib
import importlib.util
import functools
import http.server
import os
import shutil
import threading
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/media-prep.py"


def run(*args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): (digest(p), p.stat().st_mtime_ns)
            for p in path.rglob("*") if p.is_file()}


def cli(*args, ok=True, env=None):
    result = subprocess.run([sys.executable, str(HELPER), *map(str, args)], capture_output=True, text=True, env=env)
    assert (result.returncode == 0) == ok, (args, result.stdout, result.stderr)
    payload = json.loads(result.stdout)
    assert payload["status"] == ("ok" if ok else "blocked"), payload
    return payload


def main():
    assert HELPER.is_file(), "missing prepare/capture/verify helper"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("media_prep", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with tempfile.TemporaryDirectory(prefix="media-prep-check-") as tmp:
        tmp = Path(tmp).resolve()
        # Fake only package resolution; every media operation still uses real yt-dlp.
        tools = tmp / "tools"
        tools.mkdir()
        uv_log = tmp / "uv.jsonl"
        uv = tools / "uv"
        uv.write_text(f"#!{sys.executable}\n" + f'''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
assert args[:9] == ['--no-config', 'tool', 'run', '--isolated', '--refresh', '--from',
    'yt-dlp[default] @ https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.tar.gz',
    'python', '-I'], args
assert args[9:11] == ['-m', 'yt_dlp'], args
assert args[11:13] == ['--js-runtimes', 'node'], args
with Path({str(uv_log)!r}).open('a') as log:
    log.write(json.dumps(args[11:]) + '\\n')
if os.environ.get('TEST_UV_FAIL'):
    sys.exit(19)
if os.environ.get('TEST_DOWNLOAD_FAIL') and '--config-locations' in args:
    template = args[args.index('-o') + 1]
    Path(template.replace('%(ext)s', 'mp4.part')).write_bytes(b'partial transfer')
    sys.exit(19)
os.execv({shutil.which('yt-dlp')!r}, ['yt-dlp', *args[11:]])
''')
        uv.chmod(0o755)
        os.environ["PATH"] = str(tools) + os.pathsep + os.environ["PATH"]
        wrapper = ROOT / "scripts/yt-dlp.sh"
        version = subprocess.run(["bash", str(wrapper), "--version"], capture_output=True)
        assert version.returncode == 0, version.stderr
        assert version.stdout == run("yt-dlp", "--version")
        assert json.loads(uv_log.read_text().splitlines()[-1]) == ["--js-runtimes", "node", "--version"]
        failed = subprocess.run(["bash", str(wrapper), "--version"], capture_output=True,
                                env={**os.environ, "TEST_UV_FAIL": "1"})
        assert failed.returncode == 19 and not failed.stdout, "refresh failure fell back to installed yt-dlp"
        workspace = tmp / "local"
        blocked = cli("prepare", "https://example.invalid/video", "--workspace", workspace,
                      "--slug", "test-nightly-refresh-failure", ok=False,
                      env={**os.environ, "TEST_UV_FAIL": "1"})
        assert "Command failed" in blocked["error"] and not workspace.exists()
        source = tmp / "original recording.mkv"
        run("ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "color=size=64x48:rate=10",
            "-f", "lavfi", "-i", "sine=sample_rate=16000", "-t", "3", "-c:v", "ffv1", "-c:a", "pcm_s16le", source)
        original_hash = digest(source)
        subs = tmp / "lecture.srt"
        subs.write_text("1\n00:00:00,200 --> 00:00:01,000\n  First line\nSecond line\n\n2\n00:00:01,200 --> 00:00:02,800\nLast line\n", encoding="utf-8")
        args = ("prepare", source, "--workspace", workspace, "--id", "fixture", "--slug", "four-word-test-recording", "--subtitles", subs)
        result = cli(*args)
        summary = workspace / "summaries/four-word-test-recording"
        archive = summary / "fixture.mkv"
        assert result["archive"] == str(archive)
        assert digest(source) == original_hash
        assert (summary / "lecture.srt").read_bytes() == subs.read_bytes()
        assert "[00:00:00.200] First line\nSecond line" in (summary / "fixture.transcript.txt").read_text()
        metadata = json.loads((summary / "fixture.meta.json").read_text())
        assert metadata["original_filename"] == source.name
        assert metadata["duration"] == 3 and metadata["speaker"] is None
        run("bash", ROOT / "scripts/verify-archive.sh", archive)
        before = tree(workspace)
        cli("verify", summary)
        assert tree(workspace) == before, "verify wrote files"
        cli(*args)
        assert tree(workspace) == before, "completed resume wrote files"
        # Failed downloads retain hashed ownership, not a completed output claim.
        from types import SimpleNamespace
        pending_args = SimpleNamespace(workspace=workspace, slug="test-pending-download-recording", id="pending")
        work = helper.initialize(pending_args, {"source": "https://example.invalid/pending"}, {"id": "pending"})
        prefix = work.directory / "pending"
        component = work.directory / "pending.f1.webm.part"
        def fail_download():
            component.write_bytes(b"partial")
            raise ValueError("download failed")
        try:
            work.download(prefix, fail_download)
        except ValueError as error:
            assert str(error) == "download failed"
        assert work.data["pending_downloads"][work.key(component)] == digest(component)
        assert work.key(component) not in work.data["files"]
        component.write_bytes(b"changed")
        before = tree(workspace)
        try:
            work.download(prefix, lambda: None)
        except ValueError as error:
            assert "changed" in str(error).lower()
        else:
            raise AssertionError("changed pending file accepted")
        assert tree(workspace) == before
        component.write_bytes(b"partial")
        def finish_download():
            assert component.read_bytes() == b"partial"
            component.rename(work.directory / "pending.webm")
        work.download(prefix, finish_download)
        assert work.key(component) not in work.data["pending_downloads"]
        assert work.key(work.directory / "pending.webm") in work.data["pending_downloads"]
        unowned = work.directory / "pending.keep"
        unowned.write_text("unrelated")
        before = tree(workspace)
        try:
            work.download(prefix, lambda: None)
        except ValueError as error:
            assert "Unrecorded" in str(error)
        else:
            raise AssertionError("unrecorded file adopted")
        assert tree(workspace) == before
        link = work.directory / "pending.link"
        outside_download = tmp / "outside-download"
        link.symlink_to(outside_download)
        try:
            work.download(prefix, lambda: None)
        except ValueError as error:
            assert "Symlink" in str(error)
        else:
            raise AssertionError("symlink download accepted")
        assert not outside_download.exists()
        work.lock.close()
        # Explicit recovery validates completed media and provenance before any write.
        manifest = summary / ".media-prep.json"
        completed = json.loads(manifest.read_text())
        incomplete = {**completed, "ready": False, "files": {k: v for k, v in completed["files"].items() if k.endswith(".meta.json")}}
        for key in ("selection", "subtitle", "subtitle_index", "copies"):
            incomplete.pop(key)
        manifest.write_text(json.dumps(incomplete))
        recovery = ("recover", summary, "--source", str(source), "--archive-sha256", digest(archive),
                    "--subtitles", workspace / "transcripts/fixture.prep/lecture.srt")
        before = tree(workspace)
        blocked = cli(*recovery, "--source", "wrong-source", ok=False)
        assert "Source" in blocked["error"] and tree(workspace) == before
        cli(*recovery, "--archive-sha256", "0" * 64, ok=False)
        assert tree(workspace) == before
        preserved = summary / "fixture.transcript.txt"
        saved = preserved.read_bytes()
        preserved.write_text("wrong transcript")
        before = tree(workspace)
        cli(*recovery, ok=False)
        assert tree(workspace) == before
        preserved.write_bytes(saved)
        # An external edit after parsing must not become the recorded baseline.
        recovery_raw = workspace / "transcripts/fixture.prep/lecture.srt"
        raw_bytes = recovery_raw.read_bytes()
        parse = helper.srt_cues
        def edit_after_parse(text):
            cues = parse(text)
            replacement = raw_bytes.replace(b"First line", b"Other line")
            recovery_raw.write_bytes(replacement)
            (summary / "lecture.srt").write_bytes(replacement)
            return cues
        helper.srt_cues = edit_after_parse
        try:
            try:
                helper.recover(SimpleNamespace(directory=summary, source=str(source), archive_sha256=digest(archive),
                                               subtitles=recovery_raw, provenance=[]))
            except ValueError:
                assert not json.loads(manifest.read_text())["ready"]
            else:
                raise AssertionError("recovery committed stale subtitle verification")
        finally:
            helper.srt_cues = parse
            recovery_raw.write_bytes(raw_bytes)
            (summary / "lecture.srt").write_bytes(raw_bytes)
        before = tree(workspace)
        cli(*recovery)
        after = tree(workspace)
        assert {k: v for k, v in before.items() if not k.endswith(".media-prep.json")} == {k: v for k, v in after.items() if not k.endswith(".media-prep.json")}
        cli("verify", summary)
        cli(*recovery)
        assert tree(workspace) == after, "repeated recovery wrote files"
        cli(*args[:-2])
        assert tree(workspace) == after, "recovered prepare wrote files"
        # Structural validity is insufficient: packet content and subtitle timing must match.
        changed = tmp / "changed.mkv"
        run("ffmpeg", "-v", "error", "-nostdin", "-i", source, "-vf", "negate", "-c:v", "ffv1", "-c:a", "copy", changed)
        try:
            helper.same_media(source, changed)
        except ValueError as error:
            assert "packet" in str(error)
        else:
            raise AssertionError("changed media packets accepted")
        for invalid in ("", "1\n00:00:01,000 --> 00:00:00,000\nReverse\n", "1\n00:99:00,000 --> 01:00:00,000\nBad time\n"):
            try:
                helper.srt_cues(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("malformed subtitles accepted")
        # archive.org must not fall through to ASR before direct-sidecar review.
        from types import SimpleNamespace
        gate = SimpleNamespace(prep=tmp, data={"id": "archive", "metadata": {}, "subtitle_search_done": True, "downloaded_subtitles": []})
        try:
            helper.online_subtitles(gate, SimpleNamespace(source="https://archive.org/details/fixture", source_subtitles_checked=False))
        except ValueError as error:
            assert "Check archive.org" in str(error)
        else:
            raise AssertionError("archive.org direct-subtitle check bypassed")
        cli("capture", summary, "--at", "0.5", "1.5")
        assert len(list((workspace / "transcripts/fixture.prep").glob("candidate-*.jpg"))) == 10
        cli("capture", summary)
        assert len(list((workspace / "transcripts/fixture.prep").glob("overview-*.jpg"))) == 12
        before = tree(workspace)
        cli("capture", summary)
        assert tree(workspace) == before
        cli("capture", summary, "--at", "3", ok=False)
        precise = cli("capture", summary, "--at", "0.5001", "0.5002")
        assert len(set(precise["frames"])) == 10, "distinct timestamps collided"
        # VTT uses ffmpeg parsing; JSON3 shares exactly the transcript's timed cues.
        vtt = tmp / "source.vtt"
        vtt.write_text("WEBVTT\n\n00:00.200 --> 00:01.000\nVTT line\n")
        json3 = tmp / "source.json3"
        json3.write_text(json.dumps({"events": [{"tStartMs": 200, "dDurationMs": 800, "segs": [{"utf8": "JSON3 "}, {"utf8": "line"}]}]}))
        for sidecar, label in ((vtt, "vtt"), (json3, "json3")):
            output = cli("prepare", source, "--workspace", workspace, "--id", label, "--slug", f"test-{label}-subtitle-recording", "--subtitles", sidecar)
            assert (Path(output["directory"]) / sidecar.name).read_bytes() == sidecar.read_bytes()
            assert f"[{ '00:00:00.200' }] {label.upper()} line" in Path(output["transcript"]).read_text()
            cli("verify", output["directory"])
        # Existing matching embedded text subtitles avoid a second subtitle stream.
        embedded = tmp / "embedded.mkv"
        run("ffmpeg", "-v", "error", "-nostdin", "-i", source, "-i", subs, "-map", "0", "-map", "1", "-c", "copy", "-metadata:s:s:0", "language=eng", embedded)
        output = cli("prepare", embedded, "--workspace", workspace, "--id", "embedded", "--slug", "test-embedded-subtitle-recording")
        streams = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-of", "json", output["archive"]))["streams"]
        assert len(streams) == 3
        assert not (Path(output["directory"]) / "embedded.pre-subs.mkv").exists()
        # Missing model blocks after acquisition, keeping resumable archive and metadata.
        output = cli("prepare", source, "--workspace", workspace, "--id", "no-model", "--slug", "test-missing-model-recording", "--model", tmp / "missing.bin", ok=False)
        assert "model" in output["error"].lower()
        partial = workspace / "summaries/test-missing-model-recording"
        assert (partial / "no-model.mkv").is_file()
        assert (partial / "no-model.meta.json").is_file()
        cli("verify", partial, ok=False)
        # Supplying a newly found sidecar can resume only before subtitle selection.
        cli("prepare", source, "--workspace", workspace, "--id", "no-model", "--slug", partial.name, "--subtitles", subs)
        # Real yt-dlp against a loopback HTTP source; no Internet and no fake downloader.
        online = tmp / "online.mp4"
        run("ffmpeg", "-v", "error", "-nostdin", "-i", source, "-c:v", "mpeg4", "-c:a", "aac", online)
        local_mp4 = cli("prepare", online, "--workspace", workspace, "--id", "local-mp4", "--slug", "test-local-mp4-recording", "--subtitles", vtt)
        cli("verify", local_mp4["directory"])
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(tmp)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/online.mp4"
            retry_workspace = tmp / "retry"
            retry_args = ("prepare", url, "--workspace", retry_workspace, "--slug", "test-retry-video-recording", "--subtitles", vtt)
            cli(*retry_args, ok=False, env={**os.environ, "TEST_DOWNLOAD_FAIL": "1"})
            retry_manifest = retry_workspace / "summaries/test-retry-video-recording/.media-prep.json"
            pending = json.loads(retry_manifest.read_text())
            assert len(pending["pending_downloads"]) == 1 and not pending["ready"]
            retry_result = cli(*retry_args)
            cli("verify", retry_result["directory"])
            assert not json.loads(retry_manifest.read_text())["pending_downloads"]
            result = cli("prepare", url, "--workspace", workspace, "--slug", "test-online-video-recording", "--subtitles", vtt)
            (tmp / "lecture.html").write_text('<title>Subtitle source test lecture</title><video controls src="/online.mp4"><track src="/source.vtt" kind="subtitles" srclang="en" label="English"></video>')
            downloaded = cli("prepare", f"http://127.0.0.1:{server.server_port}/lecture.html", "--workspace", workspace, "--slug", "test-downloaded-subtitle-recording", "--model", tmp / "missing.bin")
            assert "VTT line" in Path(downloaded["transcript"]).read_text()
            assert not list((Path(downloaded["directory"])).glob("*.asr.srt"))
            cli("verify", result["directory"])
            assert json.loads((Path(result["directory"]) / "online.meta.json").read_text())["webpage_url"] == url
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        before = tree(workspace)
        cli("prepare", url, "--workspace", workspace, "--slug", "test-online-video-recording", "--subtitles", vtt)
        assert tree(workspace) == before, "online resume must not need network or rewrite metadata"
        calls = [json.loads(line) for line in uv_log.read_text().splitlines()]
        for flag in ("--dump-json", "--config-locations", "--write-subs"):
            assert any(flag in call for call in calls), f"nightly launcher bypassed for {flag}"
        # Fake Whisper to exercise our audio/CLI/output contract, not ASR quality.
        whisper = tools / "whisper-cli"
        whisper.write_text(f"#!{sys.executable}\n" + '''import pathlib, sys
args = sys.argv[1:]
assert args[args.index('-l') + 1] == 'en'
assert args[args.index('-t') + 1] == '8'
assert '-osrt' in args
pathlib.Path(args[args.index('-of') + 1] + '.srt').write_text('1\\n00:00:00,200 --> 00:00:01,000\\nASR fixture\\n')
''')
        whisper.chmod(0o755)
        model = tmp / "model.bin"
        model.write_bytes(b"fixture model; never loaded by real Whisper")
        env = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]}
        result = cli("prepare", source, "--workspace", workspace, "--id", "asr", "--slug", "test-asr-video-recording", "--model", model, env=env)
        assert "ASR" in " ".join(result["warnings"])
        assert (Path(result["directory"]) / "asr.asr.srt").read_bytes() == (workspace / "transcripts/asr.asr.srt").read_bytes()
        wav = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-of", "json", workspace / "transcripts/asr.wav"))["streams"][0]
        assert wav["sample_rate"] == "16000" and wav["channels"] == 1
        # Failed candidate must never replace original, even on a matching resume.
        cli("prepare", source, "--workspace", workspace, "--id", "partial", "--slug", "test-partial-video-recording", "--model", tmp / "missing.bin", ok=False)
        partial_dir = workspace / "summaries/test-partial-video-recording"
        old_hash = digest(partial_dir / "partial.mkv")
        broken = partial_dir / "partial.with-subs.mkv"
        broken.write_bytes(b"incomplete candidate")
        blocked = cli("prepare", source, "--workspace", workspace, "--id", "partial", "--slug", partial_dir.name, "--subtitles", vtt, ok=False)
        assert "Unrecorded artifact" in blocked["error"]
        assert digest(partial_dir / "partial.mkv") == old_hash and broken.read_bytes() == b"incomplete candidate"
        # Symlink ownership and concurrent mutations fail closed, without writes.
        import fcntl
        with (workspace / "transcripts/asr.prep/lock").open("rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            before = tree(workspace)
            cli("capture", result["directory"], ok=False)
            assert tree(workspace) == before
        linked = tmp / "linked"
        linked.symlink_to(workspace, target_is_directory=True)
        before = tree(workspace)
        cli("prepare", source, "--workspace", linked, "--id", "symlink", "--slug", "test-symlink-video-recording", "--subtitles", vtt, ok=False)
        assert tree(workspace) == before
        # Unrecorded dangling capture links must not create files outside the workspace.
        outside = tmp / "outside-capture.jpg"
        dangling = workspace / "transcripts/fixture.prep/candidate-0.75-001.jpg"
        dangling.symlink_to(outside)
        blocked = cli("capture", summary, "--at", "0.75", ok=False)
        assert "Symlink path refused" in blocked["error"]
        assert dangling.is_symlink() and not outside.exists()
        # Changed inputs and preserved sidecars must not be adopted or repaired silently.
        subs.write_text(subs.read_text() + "\n")
        cli(*args, ok=False)
        assert digest(source) == original_hash
        (summary / "lecture.srt").write_text("tampered")
        before = tree(workspace)
        cli("verify", summary, ok=False)
        assert tree(workspace) == before
        cli(*args, ok=False)
        # Existing unrelated files and unsafe identifiers are rejected before writes.
        unrelated = workspace / "summaries/existing-four-word-summary"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("keep")
        before = tree(workspace)
        cli("prepare", source, "--workspace", workspace, "--id", "other", "--slug", unrelated.name, "--subtitles", subs, ok=False)
        cli("prepare", source, "--workspace", workspace, "--id", "../escape", "--slug", "new-four-word-summary", ok=False)
        assert tree(workspace) == before
    print("PASS: local prep, provenance, embedding, capture, resume and read-only conflict checks")


if __name__ == "__main__":
    main()
