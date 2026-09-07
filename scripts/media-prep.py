#!/usr/bin/env python3
"""Mechanical media preparation. Content review, cleanup and publishing stay external."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FFMPEG = ["ffmpeg", "-v", "error", "-nostdin", "-n"]
YTDLP = ["bash", ROOT / "scripts/yt-dlp.sh"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in (path, *path.parents)), f"Symlink path refused: {path}")
    return path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args, log=None):
    args = list(map(str, args))
    result = subprocess.run(args, capture_output=True)
    if log:
        with log.open("ab") as stream:
            stream.write(("\n$ " + repr(args) + "\n").encode())
            stream.write(result.stdout + result.stderr)
    require(result.returncode == 0, f"Command failed ({args[0]}); " + (f"see {log}" if log else result.stderr.decode(errors="replace")[-2000:]))
    return result.stdout


def probe(path, log=None):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path], log))


def stamp(ms, separator="."):
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def srt_cues(text):
    cues = []
    for block in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n").strip("\ufeff\n")):
        lines = block.splitlines()
        if not lines:
            continue
        require(len(lines) >= 3 and lines[0].isdigit(), "Invalid SRT cue index")
        match = re.fullmatch(r"(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2,}):([0-5]\d):([0-5]\d),(\d{3})", lines[1])
        require(match, "Invalid SRT timestamp")
        values = list(map(int, match.groups()))
        start, end = [(h * 3600 + m * 60 + s) * 1000 + ms for h, m, s, ms in (values[:4], values[4:])]
        # ffmpeg trims leading cue whitespace; originals remain byte-for-byte preserved.
        content = "\n".join(lines[2:]).lstrip()
        require(content.strip() and end > start, "Empty or non-positive SRT cue")
        require(not cues or start >= cues[-1][0], "Subtitle cues out of chronological order")
        cues.append((start, end, content))
    require(cues, "No usable subtitle cues")
    return cues


def subtitle_cues(work, raw):
    if raw.suffix == ".json3":
        cues = []
        for event in json.loads(raw.read_text())["events"]:
            text = "".join(segment.get("utf8", "") for segment in event.get("segs", [])).strip()
            if not text:
                continue
            start, duration = event.get("tStartMs"), event.get("dDurationMs")
            require(type(start) is int and type(duration) is int and start >= 0 and duration > 0,
                    "JSON3 text event lacks usable timing")
            cues.append((start, start + duration, text))
        return srt_cues(render_srt(cues))
    if raw.suffix == ".vtt":
        converted = work.output(work.prep / (work.data["id"] + ".from-vtt.srt"),
            lambda p: run([*FFMPEG, "-i", raw, p], work.log))
        return srt_cues(converted.read_text(encoding="utf-8-sig"))
    require(raw.suffix == ".srt", "Supported sidecars: .srt, .vtt, .json3")
    return srt_cues(raw.read_text(encoding="utf-8-sig"))


def render_srt(cues):
    return "".join(f"{i}\n{stamp(start, ',')} --> {stamp(end, ',')}\n{text}\n\n" for i, (start, end, text) in enumerate(cues, 1))


def packet_hash(path, index, timing=True):
    # ponytail: one stream's packet listing in memory; stream ffprobe output for very long recordings.
    fields = "pts_time,dts_time,duration_time,data_hash" if timing else "data_hash"
    packets = json.loads(run(["ffprobe", "-v", "error", "-select_streams", str(index),
        "-show_packets", "-show_data_hash", "sha256", "-show_entries",
        "packet=" + fields, "-of", "json", path]))["packets"]
    values = [[packet.get(field) for field in fields.split(",")] for packet in packets]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def same_media(original, candidate, acquisition=False):
    before, after = probe(original), probe(candidate)
    # Initial container remux may shift negative timestamps (e.g. AAC priming).
    tolerance = 1 if acquisition else 0.05
    require(abs(float(before["format"]["duration"]) - float(after["format"]["duration"])) <= tolerance, "Archive duration changed")
    require(len(after["streams"]) >= len(before["streams"]), "Archive lost streams")
    fields = ("codec_type", "codec_name", "width", "height", "pix_fmt", "sample_rate", "channels", "channel_layout")
    for old, new in zip(before["streams"], after["streams"]):
        require(all(old.get(k) == new.get(k) for k in fields), "Archive stream properties changed")
        require(packet_hash(original, old["index"], not acquisition) == packet_hash(candidate, new["index"], not acquisition), "Archive packet data/timing changed")


def embedded_cues(archive, index):
    return srt_cues(run([*FFMPEG, "-i", archive, "-map", f"0:{index}", "-f", "srt", "-"]).decode("utf-8"))


class Work:
    def __init__(self, directory, readonly=False):
        self.directory = safe_path(directory)
        self.manifest = safe_path(self.directory / ".media-prep.json")
        self.data = json.loads(self.manifest.read_text())
        require(self.data.get("version") == 1, "Unsupported preparation manifest")
        self.workspace = safe_path(self.data["workspace"])
        require(self.directory == self.workspace / "summaries" / self.data["slug"], "Workspace location changed")
        self.prep = safe_path(self.workspace / "transcripts" / (self.data["id"] + ".prep"))
        self.lock = safe_path(self.prep / "lock").open("rb")
        fcntl.flock(self.lock, (fcntl.LOCK_SH if readonly else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        # Reload after locking: a competing preparation may just have committed a stage.
        self.data = json.loads(self.manifest.read_text())
        self.log = None if readonly else safe_path(self.prep / "commands.log")
        self.check_files()

    def path(self, relative):
        path = safe_path(self.workspace / relative)
        require(path.is_relative_to(self.directory) or path.is_relative_to(self.prep)
                or (path.parent == self.workspace / "transcripts" and path.name.startswith(self.data["id"] + ".")), "Artifact outside source workspace")
        return path

    def key(self, path):
        return str(path.relative_to(self.workspace))

    def check_files(self):
        for relative, expected in self.data["files"].items():
            path = self.path(relative)
            require(path.is_file() and sha(path) == expected, f"Missing/changed recorded artifact: {path}")

    def save(self):
        with tempfile.NamedTemporaryFile(mode="w", dir=self.directory, prefix=".media-prep-", delete=False) as stream:
            json.dump(self.data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(stream.name, self.manifest)

    def output(self, path, produce):
        path = self.path(self.key(path))
        key = self.key(path)
        if key not in self.data["files"]:
            require(not path.exists(), f"Unrecorded artifact; inspect before resuming: {path}")
            produce(path)
            require(path.is_file() and path.stat().st_size, f"Missing/empty output: {path}")
            self.data["files"][key] = sha(path)
            self.save()
        return path

    def text(self, path, text):
        def write(destination):
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(text)
        return self.output(path, write)

    def copy(self, source, destination):
        def copy(path):
            with source.open("rb") as src, path.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            require(sha(source) == sha(path), f"Provenance copy differs: {path}")
        self.output(destination, copy)
        require(sha(source) == sha(destination), f"Provenance copy differs: {destination}")
        return destination

    def result(self, **extra):
        return {"status": "ok", "directory": str(self.directory), "archive": str(self.directory / (self.data["id"] + ".mkv")),
                "transcript": str(self.directory / (self.data["id"] + ".transcript.txt")),
                "manifest": str(self.manifest), "log": str(self.prep / "commands.log"),
                "warnings": self.data["warnings"] + ["Mechanical checks only; full transcript, factual and visual review, summary and final editing remain."], **extra}


def initialize(args, identity, metadata):
    workspace = safe_path(args.workspace)
    directory = safe_path(workspace / "summaries" / args.slug)
    prep = safe_path(workspace / "transcripts" / (args.id + ".prep"))
    if directory.exists():
        require((directory / ".media-prep.json").is_file(), f"Existing unowned summary directory: {directory}")
        work = Work(directory)
        require(work.data["identity"] == identity, "Source or preparation options differ from recorded owner")
        return work
    require(not prep.exists(), f"Source ID already reserved: {prep}")
    transcripts = safe_path(workspace / "transcripts")
    require(not transcripts.exists() or not list(transcripts.glob(args.id + ".*")), "Existing transcript artifacts; choose a fresh ID or inspect manually")
    directory.parent.mkdir(parents=True, exist_ok=True)
    transcripts.mkdir(parents=True, exist_ok=True)
    prep.mkdir()
    directory.mkdir()
    (prep / "lock").touch(exist_ok=False)
    data = {"version": 1, "id": args.id, "slug": args.slug, "workspace": str(workspace), "identity": identity,
            "metadata": metadata, "files": {}, "warnings": [], "ready": False}
    with (directory / ".media-prep.json").open("x") as stream:
        json.dump(data, stream, indent=2)
    return Work(directory)


def verify(work):
    require(work.data["ready"], "Preparation incomplete; resume prepare after resolving blocker")
    archive = work.directory / (work.data["id"] + ".mkv")
    run(["bash", ROOT / "scripts/verify-archive.sh", archive])
    original = work.directory / (work.data["id"] + ".pre-subs.mkv")
    if original.exists():
        same_media(original, archive)
    expected = srt_cues(work.path(work.data["subtitle"]).read_text())
    require(embedded_cues(archive, work.data["subtitle_index"]) == expected, "Embedded subtitle text/timing differs")
    for source, destination in work.data["copies"]:
        require(sha(work.path(source)) == sha(work.path(destination)), "Preserved provenance differs")
    return work.result()


def online_subtitles(work, args):
    prefix = work.prep / (work.data["id"] + ".source")
    if not work.data.get("subtitle_search_done"):
        require(not list(work.prep.glob(prefix.name + ".*")), "Unrecorded subtitle download; inspect before resuming")
        youtube = "youtube" in work.data["metadata"].get("extractor", "").lower()
        run([*YTDLP, "--ignore-config", "--no-playlist", "--no-overwrites", "--write-subs", "--write-auto-subs",
             "--sub-langs", args.language, "--sub-format", "json3" if youtube else "srt/vtt/best", "--skip-download",
             "-o", str(prefix).replace("%", "%%"), "--", args.source], work.log)
        paths = sorted(work.prep.glob(prefix.name + ".*"))
        require(all(p.suffix in (".srt", ".vtt", ".json3") and p.is_file() for p in paths), "Unsupported downloaded subtitles; supply --subtitles FILE")
        require(len(paths) <= 1, "Multiple downloaded subtitles; select one with --subtitles FILE")
        for path in paths:
            work.data["files"][work.key(safe_path(path))] = sha(path)
        work.data["downloaded_subtitles"] = [work.key(p) for p in paths]
        work.data["subtitle_search_done"] = True
        work.save()
    paths = work.data["downloaded_subtitles"]
    if paths:
        return work.path(paths[0])
    if urlparse(args.source).hostname in ("archive.org", "www.archive.org"):
        require(args.source_subtitles_checked, "Check archive.org item download page for .srt/.vtt; supply --subtitles FILE, or --source-subtitles-checked only after finding none")
    return None


def select_subtitles(work, args, archive):
    selected = work.data.get("selection")
    if selected:
        if args.subtitles:
            path = safe_path(args.subtitles)
            require(selected.get("input") == str(path) and selected.get("sha256") == sha(path), "Subtitle input differs from recorded selection")
        if args.subtitle_stream is not None:
            require(selected.get("index") == args.subtitle_stream, "Subtitle stream differs from recorded selection")
        if selected.get("input"):
            require(sha(safe_path(selected["input"])) == selected["sha256"], "Subtitle input changed")
        return work.path(selected["raw"])
    ident = work.data["id"]
    if args.subtitles:
        path = safe_path(args.subtitles)
        require(path.suffix in (".srt", ".vtt", ".json3"), "Supported sidecars: .srt, .vtt, .json3")
        raw = work.copy(path, work.prep / path.name)
        selected = {"input": str(path), "sha256": sha(path)}
    else:
        streams = probe(archive)["streams"]
        text_tracks = [s for s in streams if s.get("codec_name") in ("subrip", "webvtt", "ass", "ssa", "mov_text", "text")]
        if args.subtitle_stream is not None:
            tracks = [s for s in text_tracks if s["index"] == args.subtitle_stream]
            require(tracks, "Requested subtitle stream is not a usable text track")
        else:
            languages = {args.language, "eng"} if args.language == "en" else {args.language}
            tracks = [s for s in text_tracks if s.get("tags", {}).get("language") in languages]
            if not tracks and len(text_tracks) == 1 and text_tracks[0].get("tags", {}).get("language", "und") == "und":
                tracks = text_tracks
            require(len(tracks) <= 1 and (tracks or not text_tracks), "Ambiguous/nonmatching text subtitles; choose --subtitle-stream INDEX or --subtitles FILE")
        if tracks:
            index = tracks[0]["index"]
            raw = work.output(work.workspace / "transcripts" / (ident + ".embedded.srt"),
                lambda p: run([*FFMPEG, "-i", archive, "-map", f"0:{index}", p], work.log))
            selected = {"index": index}
        else:
            downloaded = online_subtitles(work, args) if urlparse(args.source).scheme in ("http", "https") else None
            if downloaded:
                work.data["selection"] = {"raw": work.key(downloaded)}
                work.save()
                return downloaded
            model = safe_path(args.model)
            require(model.is_file() and model.stat().st_size, f"Whisper model unavailable: {model}; provide --model or source subtitles")
            require(shutil.which("whisper-cli"), "whisper-cli unavailable; install it or supply source subtitles")
            wav = work.output(work.workspace / "transcripts" / (ident + ".wav"), lambda p: run(
                [*FFMPEG, "-i", archive, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", p], work.log))
            raw = work.output(work.workspace / "transcripts" / (ident + ".asr.srt"), lambda p: run(
                ["whisper-cli", "-m", model, "-f", wav, "-l", args.language, "-t", "8", "-osrt", "-of", str(p)[:-4]], work.log))
            selected = {"asr_model": str(model), "model_sha256": sha(model)}
            work.data["warnings"].append("ASR is uncorrected; verify names, technical terms and quotations against primary sources and visuals.")
    selected["raw"] = work.key(raw)
    work.data["selection"] = selected
    work.save()
    return raw


def prepare(args):
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){3,5}", args.slug), "Slug must contain 4–6 lowercase hyphenated words")
    require(re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)*", args.language), "Invalid subtitle language")
    remote = urlparse(args.source).scheme in ("http", "https")
    if remote:
        source = args.source
        existing = safe_path(Path(args.workspace) / "summaries" / args.slug / ".media-prep.json")
        if existing.is_file():
            metadata = json.loads(existing.read_text())["metadata"]
        else:
            metadata = json.loads(run([*YTDLP, "--ignore-config", "--no-playlist", "--dump-json", "--no-download", "--", source]))
        require(args.id is None or args.id == metadata["id"], "Online ID must match yt-dlp metadata")
        args.id = metadata["id"]
        identity = {"source": source, "language": args.language}
    else:
        source = safe_path(args.source)
        require(source.is_file(), f"Local source unavailable: {source}")
        source_hash = sha(source)
        args.id = args.id or "local-" + source_hash[:16]
        info = probe(source)
        metadata = {"id": args.id, "original_filename": source.name, "original_path": str(source), "sha256": source_hash,
                    "title": args.title or source.stem, "speaker": args.speaker, "date": args.date, "source_url": args.source_url,
                    "duration": float(info["format"]["duration"])}
        identity = {"source": str(source), "sha256": source_hash, "metadata": metadata, "language": args.language}
    require(isinstance(args.id, str) and re.fullmatch(r"[A-Za-z0-9_-]+", args.id), "Unsafe source ID")
    work = initialize(args, identity, metadata)
    if work.data["ready"]:
        select_subtitles(work, args, work.directory / (args.id + ".mkv"))
        return verify(work)
    ident = args.id
    archive = work.directory / (ident + ".mkv")
    copies = []
    meta = work.text(work.workspace / "transcripts" / (ident + ".meta.json"), json.dumps(metadata, indent=2) + "\n")
    work.copy(meta, work.directory / meta.name)
    if remote:
        def download(path):
            require(not [p for p in work.directory.glob(ident + ".*") if work.key(p) not in work.data["files"]], "Unrecorded download files; inspect before resuming")
            run([*YTDLP, "--ignore-config", "--config-locations", ROOT / "scripts/archive.conf", "-o",
                 str(path.with_suffix("")).replace("%", "%%") + ".%(ext)s", "--", source], work.log)
        work.output(archive, download)
    else:
        work.output(archive, lambda p: run([*FFMPEG, "-i", source, "-map", "0", "-c", "copy", p], work.log))
    run(["bash", ROOT / "scripts/verify-archive.sh", archive, "--no-subtitles"], work.log)
    if not remote:
        same_media(source, archive, acquisition=True)
    duration = float(probe(archive)["format"]["duration"])
    require(math.isfinite(duration) and duration > 0, "Invalid archive duration")
    if metadata.get("duration") is not None:
        require(abs(duration - float(metadata["duration"])) <= 1, "Archive duration differs from source metadata")
    raw = select_subtitles(work, args, archive)
    cues = subtitle_cues(work, raw)
    require(cues[-1][1] <= int(float(probe(archive)["format"]["duration"]) * 1000) + 1000, "Subtitle timing exceeds archive duration")
    normalized = work.text(work.workspace / "transcripts" / (ident + ".normalized.srt"), render_srt(cues))
    transcript = work.text(work.workspace / "transcripts" / (ident + ".transcript.txt"),
                           "\n\n".join(f"[{stamp(start)}] {text}" for start, _, text in cues) + "\n")
    for path in (meta, raw, normalized, transcript):
        preserved = work.copy(path, work.directory / path.name)
        copies.append([work.key(path), work.key(preserved)])
    index = work.data["selection"].get("index")
    if index is None or embedded_cues(archive, index) != cues:
        candidate = work.directory / (ident + ".with-subs.mkv")
        work.output(candidate, lambda p: run([*FFMPEG, "-i", archive, "-i", normalized, "-map", "0", "-map", "1:0", "-c", "copy", p], work.log))
        run(["bash", ROOT / "scripts/verify-archive.sh", candidate], work.log)
        same_media(archive, candidate)
        index = len(probe(archive)["streams"])
        require(embedded_cues(candidate, index) == cues, "Candidate subtitle text/timing differs")
        work.copy(archive, work.directory / (ident + ".pre-subs.mkv"))
        os.replace(candidate, archive)
        work.data["files"][work.key(archive)] = work.data["files"].pop(work.key(candidate))
    work.data.update(ready=True, subtitle=work.key(normalized), subtitle_index=index, copies=copies)
    work.save()
    return verify(work)


def capture(args):
    work = Work(args.directory)
    verify(work)
    archive = work.directory / (work.data["id"] + ".mkv")
    duration = float(probe(archive)["format"]["duration"])
    times = args.at if args.at is not None else [duration * (i + 0.5) / 12 for i in range(12)]
    require(all(math.isfinite(t) and 0 <= t < duration for t in times), "Capture time must be within archive duration")
    outputs = []
    for i, time in enumerate(times):
        prefix = f"candidate-{time}" if args.at is not None else f"overview-{i + 1:02}"
        count = 5 if args.at is not None else 1
        paths = [work.path(work.key(work.prep / f"{prefix}-{n:03}.jpg")) for n in range(1, count + 1)]
        if not all(work.key(p) in work.data["files"] for p in paths):
            require(not any(p.exists() for p in paths), f"Partial capture; inspect before resuming: {prefix}")
            run([*FFMPEG, "-ss", str(time), "-i", archive, "-map", "0:v:0", "-frames:v", str(count), "-q:v", "2", work.prep / (prefix + "-%03d.jpg")], work.log)
            require(all(p.is_file() and p.stat().st_size for p in paths), "Incomplete frame burst; choose earlier timestamp")
            for path in paths:
                work.data["files"][work.key(path)] = sha(path)
            work.save()
        outputs.extend(map(str, paths))
    return work.result(frames=outputs, timestamps=times)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Acquire once, preserve subtitles/transcript and verify embedding")
    prep.add_argument("source")
    prep.add_argument("--workspace", default="local", help="Local artifact root (default: local)")
    prep.add_argument("--slug", required=True)
    for option in ("id", "title", "speaker", "date", "source-url", "subtitles"):
        prep.add_argument("--" + option)
    prep.add_argument("--subtitle-stream", type=int, help="Absolute ffprobe stream index")
    prep.add_argument("--language", default="en")
    prep.add_argument("--model", default="local/models/ggml-large-v3-turbo.bin")
    prep.add_argument("--source-subtitles-checked", action="store_true", help="Confirm archive.org direct sidecars were checked and none were usable")
    for name in ("verify", "capture"):
        command = commands.add_parser(name)
        command.add_argument("directory", help="Summary directory created by prepare")
        if name == "capture":
            command.add_argument("--at", nargs="+", type=float, help="Seconds; five-frame burst per time (default: 12 overview frames)")
    args = parser.parse_args()
    try:
        result = prepare(args) if args.command == "prepare" else capture(args) if args.command == "capture" else verify(Work(args.directory, readonly=True))
        print(json.dumps(result))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error), "warnings": ["Partial files preserved; no cleanup performed."]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
