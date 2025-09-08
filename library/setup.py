from setuptools import setup, Extension
import glob
from pathlib import Path


def detect_uld_api_dir(src_root: Path):
    candidates = [
        p for p in src_root.iterdir()
        if p.is_dir() and p.name.upper().endswith("_ULD_API") and p.name.upper().startswith("VL53")
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def generate_files(gendir: Path, variant_token: str, api_inc_dir: Path, api_src_dir: Path):
    gendir.mkdir(parents=True, exist_ok=True)

    upper = variant_token
    lower = variant_token.lower()

    has_motion = (api_inc_dir / f"{lower}_plugin_motion_indicator.h").exists()
    has_xtalk = (api_inc_dir / f"{lower}_plugin_xtalk.h").exists()
    has_thresh = (api_inc_dir / f"{lower}_plugin_detection_thresholds.h").exists()

    # Render from templates and return early
    templates_dir = Path(__file__).resolve().parent / "templates"
    is_l7 = variant_token.upper().startswith("VL53L7")

    mapping = {
        "UPPER": upper,
        "lower": lower,
        "HAS_MOTION": "1" if has_motion else "0",
        "HAS_XTALK": "1" if has_xtalk else "0",
        "HAS_THRESH": "1" if has_thresh else "0",
        "IS_L7": "1" if is_l7 else "0",
    }

    def _render(src_name: str, out_name: str):
        content = (templates_dir / src_name).read_text()
        for k, v in mapping.items():
            content = content.replace("{{" + k + "}}", v)
        (gendir / out_name).write_text(content)

    _render("platform.h.tmpl", "platform.h")
    _render("platform.c.tmpl", "platform.c")
    _render("module.cpp.tmpl", "module.cpp")

    return


here = Path(__file__).resolve().parent
src_root = here / "src"
api_dir = detect_uld_api_dir(src_root)
if not api_dir:
    # Fallback to any *_ULD_API folder present
    candidates = list(src_root.glob("*_ULD_API"))
    api_dir = candidates[0] if candidates else None
if not api_dir:
    raise RuntimeError("No *_ULD_API directory found under library/src. Use import_uld.py to add ST ULD.")

api_inc_dir = api_dir / "inc"
api_src_dir = api_dir / "src"

variant_token = api_dir.name.split("_ULD_API")[0]

gendir = here / "_generated"
generate_files(gendir, variant_token, api_inc_dir, api_src_dir)

api_sources = sorted(glob.glob(str(api_src_dir / "*.c")))
# Ensure our generated platform symbols match the ULD expectations by using
# generic names (RdMulti, WrMulti, WaitMs, etc.)
nb_target_macro = f"{variant_token}_NB_TARGET_PER_ZONE"

extension = Extension(
    'vl53_ctypes',
    define_macros=[(nb_target_macro, '1')],
    extra_compile_args=['-include', str(gendir / 'platform.h')],
    include_dirs=[str(gendir), str(api_inc_dir)],
    libraries=[],
    library_dirs=[],
    sources=[str(gendir / 'platform.c')] + api_sources + [str(gendir / 'module.cpp')]
)

setup(ext_modules=[extension])
