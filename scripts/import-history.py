"""Import authentic saved release states and commit current feature groups."""

import argparse
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    subprocess.run(["git", *map(str, args)], cwd=ROOT, check=True)


def stage_snapshot(archive, destination):
    with ZipFile(archive) as release:
        for entry in release.infolist():
            name = PurePosixPath(entry.filename.replace(chr(92), "/"))
            if entry.is_dir():
                continue
            if name.is_absolute() or ".." in name.parts or ":" in str(name):
                raise ValueError(f"Unsafe archive path {name}")
            if any(part.startswith(".") and part != ".gitignore" for part in name.parts):
                raise ValueError(f"Unexpected hidden path {name}")
            if name.suffix.lower() in {".exe", ".dll", ".pt", ".onnx", ".weights", ".sqlite3", ".pem", ".pfx"}:
                raise ValueError(f"Unexpected binary or private file {name}")
            target = destination.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(release.read(entry))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path)
    args = parser.parse_args()
    if (ROOT / ".git").exists():
        parser.error("Run only against an uninitialized checkout.")
    releases = [
        (args.outputs / "FocusGoblin-source.zip", "0.1"),
        (args.outputs / "FocusGoblin-v0.2" / "FocusGoblin-source.zip", "0.2"),
        (args.outputs / "FocusGoblin-v0.3" / "FocusGoblin-source.zip", "0.3"),
    ]
    with tempfile.TemporaryDirectory(prefix="mistwatch-history-") as temporary:
        base = Path(temporary)
        for archive, version in releases:
            stage_snapshot(archive, base / version)
        git("init", "-b", "main")
        for _, version in releases:
            git(f"--work-tree={base / version}", "add", "-A")
            git("commit", "-m", f"Import saved Focus Goblin {version} release snapshot")
        git("add", "--", ".gitignore")
        git("commit", "-m", "Exclude local builds, models and private configuration")
        git("add", "--", "focus_goblin/ui.py")
        git("commit", "-m", "Add a Ko-fi support link to the desktop footer")
        git("add", "--", "extension")
        git("commit", "-m", "Add the Manifest V3 browser focus timer")
        git("add", "--", "README.md", "docs/BROWSER-PRIVACY.md", "docs/BROWSER-PUBLISHING.md", "docs/HISTORY.md", "scripts")
        git("commit", "-m", "Document Mistwatch architecture, release history and store submission")
        git("fsck", "--full")
        git("status", "--short")
        git("log", "--oneline")


if __name__ == "__main__":
    main()
