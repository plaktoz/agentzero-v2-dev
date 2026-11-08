"""Expose existing Claude skills to Codex without copying their contents."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--claude-home", type=Path, default=Path.home() / ".claude",
        help="Claude configuration directory (default: ~/.claude)",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = (args.claude_home.expanduser() / "skills", root / ".claude" / "skills")
    skills = {}
    for source in sources:
        if source.is_dir():
            for skill in sorted(source.iterdir()):
                if (skill / "SKILL.md").is_file():
                    skills[skill.name] = skill.resolve()

    if not skills:
        parser.error("No SKILL.md files found in: " + ", ".join(map(str, sources)))

    destination = root / ".agents" / "skills"
    # Validate every name before creating any links. Never overwrite local work.
    for name, target in skills.items():
        link = destination / name
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != target:
                parser.error(f"Conflicting skill: {link}; move it before retrying")

    destination.mkdir(parents=True, exist_ok=True)
    for name, target in skills.items():
        link = destination / name
        if not link.is_symlink():
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                parser.exit(1, f"Cannot link {link}: {exc}\n"
                            "On Windows, enable Developer Mode or use an elevated terminal.\n")
        print(f"{name}: {target}")
    print(f"Ready: {len(skills)} shared skills. Restart Codex if needed.")


if __name__ == "__main__":
    main()
