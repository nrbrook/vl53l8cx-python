#!/usr/bin/env python3
"""Import an ST VL53 ULD zip and extract the C API into library/src.

Usage:
  python3 import_uld.py /path/to/STSW-IMG036.zip

The script searches the zip for a directory named like `VL53*CX_ULD_API` and
extracts the `inc/` and `src/` subdirectories into `library/src/<API_DIR>/`.

Supported archive structures include nested paths such as:
  STSW-IMG036/VL53L7CX_ULD_driver_2.0.1/VL53L7CX_ULD_API/{inc,src}

If multiple API directories are found, the script will prompt to choose or
use the first if run with --non-interactive.
"""

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path


def _top_level_dirs(zf: zipfile.ZipFile):
    """Return a sorted list of top-level directories in the zip."""
    tops = set()
    for n in zf.namelist():
        if "/" in n:
            tops.add(n.split("/", 1)[0])
    return sorted(tops)


def find_api_root_structured(zf: zipfile.ZipFile):
    """Locate API root using expected ST structure.

    Expected: <TOP>/VL53L?CX_ULD_driver_<ver>/VL53L?CX_ULD_API/{inc,src}
    Returns the path inside the zip to VL53L?CX_ULD_API (no trailing slash).
    """
    names = zf.namelist()
    tops = _top_level_dirs(zf)
    if len(tops) != 1:
        raise RuntimeError("Zip must contain a single top-level directory (eg: STSW-IMG036)")
    top = tops[0]
    prefix_top = f"{top}/"
    second_levels = set()
    for n in names:
        if n.startswith(prefix_top):
            rest = n[len(prefix_top):]
            if "/" in rest:
                second_levels.add(rest.split("/", 1)[0])
    print(second_levels)
    driver_dirs = sorted([d for d in second_levels if re.match(r"VL53L\d+CX_ULD_driver_", d)])
    if not driver_dirs:
        raise RuntimeError("No VL53L?CX_ULD_driver_* directory found under top-level directory")
    driver_dir = driver_dirs[-1]
    api_candidates = set()
    prefix_driver = f"{top}/{driver_dir}/"
    for n in names:
        if n.startswith(prefix_driver):
            m = re.search(r"(^|/)VL53L\d+CX_ULD_API(/|$)", n)
            if m:
                api_prefix = n[: m.end()].rstrip("/")
                api_candidates.add(api_prefix)
    if not api_candidates:
        raise RuntimeError("No VL53L?CX_ULD_API directory found under the driver directory")
    api_root = sorted(api_candidates)[-1]
    has_inc = any(p.startswith(f"{api_root}/inc/") for p in names)
    has_src = any(p.startswith(f"{api_root}/src/") for p in names)
    if not (has_inc and has_src):
        raise RuntimeError("ULD API missing required inc/ or src/ directories")
    return api_root


def extract_api(zf: zipfile.ZipFile, api_root: str, dest_root: Path):
    """Extract inc/ and src/ under api_root into dest_root/<API_DIR>/..."""
    api_dirname = Path(api_root).name
    target_base = dest_root / api_dirname
    for member in zf.namelist():
        if member.startswith(f"{api_root}/inc/") or member.startswith(f"{api_root}/src/"):
            # Compute path relative to api_root/
            rel_inside_api = member[len(api_root.rstrip('/') + '/') :]
            target_path = target_base / rel_inside_api
            if member.endswith("/"):
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src_f, target_path.open("wb") as dst_f:
                    dst_f.write(src_f.read())


def main():
    """CLI entrypoint for importing a VL53 ULD zip into library/src."""
    parser = argparse.ArgumentParser(description="Import ST VL53 ULD zip into library/src")
    parser.add_argument("zip_path", help="Path to STSW zip file containing the ULD")
    parser.add_argument("--non-interactive", action="store_true", help="Skip prompts; fail fast on unexpected layouts")
    args = parser.parse_args()

    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        print(f"Zip not found: {zip_path}")
        return 1

    repo_root = Path(__file__).resolve().parent
    out_root = repo_root / "library" / "src"
    out_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            api_choice = find_api_root_structured(zf)
        except Exception as e:
            print(str(e))
            return 2

        # The last path component is the API dir name, eg VL53L7CX_ULD_API
        api_dirname = Path(api_choice).name
        dest_root = out_root

        # Clear existing destination API dir if present to avoid stale files
        existing_api_dir = dest_root / api_dirname
        if existing_api_dir.exists():
            shutil.rmtree(existing_api_dir)

        print(f"Extracting {api_dirname} to {dest_root}...")
        extract_api(zf, api_choice, dest_root)
        print("Done.")
        print("You can now build/install the wrapper. The setup will auto-detect the variant.")

    return 0


if __name__ == "__main__":
    sys.exit(main())


