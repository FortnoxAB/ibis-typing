"""IntelliJ setup for ibis-typing."""

import argparse
import logging
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplatePaths:
    @property
    def clone_paths(self):
        return {
            self.git: self.dot_git,
            self.files: self.repo_root,
        }

    @property
    @lru_cache
    def repo_root(self):
        cmd = "git rev-parse --show-toplevel".split()
        root = subprocess.check_output(cmd).decode().strip()
        return Path(root)

    @property
    def ide(self):
        return self.repo_root / "ide"

    @property
    def files(self):
        return self.ide / "files"

    @property
    def git(self):
        return self.ide / "git"

    @property
    def dot_git(self):
        # Note: .git-directories are excluded from GIT.
        return self.repo_root / ".git"


def main(argv=None):
    args = parse_args(argv)
    paths = TemplatePaths()

    logging.basicConfig(level=logging.INFO)
    for source, target in paths.clone_paths.items():
        merge_dirs(source, target, update_templates=args.update_templates)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-templates", action="store_true")
    return parser.parse_args(argv)


def merge_dirs(source: Path, target: Path, *, update_templates: bool = False):
    logger.info(f"Cloning files between {source} and {target}")
    for src in source.glob("**/*"):
        if src.is_file():
            _copy_file(src, target / src.relative_to(source), update_templates)


def _copy_file(src: Path, dst: Path, update_templates: bool) -> None:
    if dst.suffix == ".template":
        dst = dst.with_suffix("")

    logger.info(f"Copying {src}" if not update_templates else f"Updating {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if update_templates:
        src, dst = dst, src

    shutil.copyfile(src, dst)
    shutil.copymode(src, dst)


if __name__ == "__main__":
    main()
