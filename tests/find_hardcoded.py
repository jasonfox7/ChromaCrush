# Scans project for hardcoded literal assignments.
# Supports: Python (.py), Dart (.dart), GLSL shaders (.frag, .vert)
# Ignores: Markdown (.md), JSON, lock files, generated files, binaries
# Respects .gitignore. Can be run from any location.
import ast
import os
import re
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# Get project root (1 level up from tests/)
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# ─── File type configuration ─────────────────────────────────────
SCAN_EXTENSIONS = {".py", ".dart", ".frag", ".vert"}
SKIP_EXTENSIONS = {
    ".md",
    ".json",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp3",
    ".ogg",
    ".wav",
    ".mp4",
    ".pdf",
    ".parquet",
    ".jsonl",
    ".yaml",
    ".yml",
}
DART_GENERATED_SUFFIXES = (".g.dart", ".freezed.dart", ".mocks.dart")

# ─── Dart regex patterns ─────────────────────────────────────────
# Matches: identifier = value;  (excludes ==, !=, >=, <=, =>, +=, etc.)
DART_ASSIGN_RE = re.compile(r"\b(\w+)\s*(?<![!=<>+\-*/%&|^])=(?![=>])\s*(.+?)\s*;")
# Simple literal values --no interpolation, no function calls
DART_LITERAL_RE = re.compile(
    r"""^(?:
        '(?:[^'\\$]|\\.)*'                    |  # single-quoted string
        "(?:[^"\\$]|\\.)*"                    |  # double-quoted string
        -?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?      |  # numeric
        0[xX][0-9a-fA-F]+                     |  # hex literal
        true | false | null                       # keywords
    )$""",
    re.VERBOSE,
)
# Keywords that look like identifiers but aren't variable names
DART_KEYWORDS = {
    "return",
    "if",
    "else",
    "while",
    "for",
    "switch",
    "case",
    "default",
    "assert",
    "throw",
    "yield",
    "await",
    "break",
    "continue",
    "new",
    "super",
    "this",
    "class",
    "extends",
    "implements",
    "with",
    "enum",
}

# ─── GLSL regex patterns ─────────────────────────────────────────
GLSL_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(.+?)\s*$")
GLSL_CONST_RE = re.compile(
    r"^\s*const\s+" r"(?:float|int|uint|bool)\s+" r"(\w+)\s*=\s*(.+?)\s*;\s*$"
)


# ─── Gitignore handling ──────────────────────────────────────────
def load_gitignore_specs(root_dir: str) -> PathSpec:
    specs = []
    current = Path(root_dir).resolve()
    while current != current.parent:
        gitignore_path = current / ".gitignore"
        if gitignore_path.is_file():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    lines = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                if lines:
                    spec = PathSpec.from_lines(GitWildMatchPattern, lines)
                    specs.append(spec)
                    print(f"Loaded .gitignore from: {gitignore_path}")
            except Exception as e:
                print(f"Warning reading {gitignore_path}: {e}")
        current = current.parent
        if current == current.parent:
            break
    if specs:
        combined = specs[0]
        for s in specs[1:]:
            combined += s
        return combined
    return PathSpec([])


# ─── Python scanner (AST) ────────────────────────────────────────
def is_likely_real_python(path: Path) -> bool:
    """Reject obvious non-Python files that happen to have a .py extension."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096).lower().strip()
        bad_starts = [
            "{",
            "[",
            "<!doctype",
            "<html",
            "<head",
            "<body",
            "---",
            "===",
            "<?xml",
            "<svg",
        ]
        if any(head.startswith(s) for s in bad_starts):
            print(f"  Skipped (non-code content): {os.path.relpath(path)}")
            return False
        if path.stat().st_size < 50:
            print(f"  Skipped (too small): {os.path.relpath(path)}")
            return False
        return True
    except Exception as e:
        print(f"  Error opening {os.path.relpath(path)}: {e}")
        return False


def scan_python(file_path: Path) -> list[str]:
    """Scan a Python file using AST for hardcoded literal assignments."""
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if isinstance(node.value, ast.Constant):
                            value = repr(node.value.value)
                            results.append(
                                f"{file_path}:{node.lineno}  {var_name} = {value}"
                            )
    except SyntaxError as e:
        print(f"  Syntax error in {file_path}: {e}")
    except Exception as e:
        print(f"  Error scanning {file_path}: {type(e).__name__} - {e}")
    return results


# ─── Dart scanner (regex) ────────────────────────────────────────
def scan_dart(file_path: Path) -> list[str]:
    """Scan a Dart file for hardcoded literal assignments using regex."""
    results = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return results

    in_block_comment = False
    for lineno, raw_line in enumerate(lines, 1):
        line = raw_line.strip()

        # Track block comments
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if "/*" in line:
            if "*/" not in line:
                in_block_comment = True
            continue

        # Skip comment lines, imports, empty lines
        if (
            not line
            or line.startswith("//")
            or line.startswith("import ")
            or line.startswith("export ")
            or line.startswith("part ")
            or line.startswith("@")
        ):
            continue

        # Strip trailing comment
        code = re.sub(r"\s*//.*$", "", line)

        # Find assignment
        m = DART_ASSIGN_RE.search(code)
        if m:
            var_name = m.group(1)
            value = m.group(2).strip()

            # Skip language keywords that look like identifiers
            if var_name in DART_KEYWORDS:
                continue

            if DART_LITERAL_RE.match(value):
                results.append(f"{file_path}:{lineno}  {var_name} = {value}")

    return results


# ─── GLSL scanner (regex) ────────────────────────────────────────
def scan_glsl(file_path: Path) -> list[str]:
    """Scan a GLSL shader for #define macros and const declarations."""
    results = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return results

    in_block_comment = False
    for lineno, raw_line in enumerate(lines, 1):
        line = raw_line.strip()

        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if "/*" in line:
            if "*/" not in line:
                in_block_comment = True
            continue

        if not line or line.startswith("//"):
            continue

        # #define macros
        dm = GLSL_DEFINE_RE.match(line)
        if dm:
            results.append(f"{file_path}:{lineno}  #define {dm.group(1)} {dm.group(2)}")
            continue

        # const scalar declarations
        cm = GLSL_CONST_RE.match(line)
        if cm:
            results.append(f"{file_path}:{lineno}  const {cm.group(1)} = {cm.group(2)}")

    return results


# ─── Main scanner ────────────────────────────────────────────────
def find_hardcoded_vars(root_dir="."):
    root_path = Path(root_dir).resolve()
    gitignore_spec = load_gitignore_specs(root_dir)

    py_results, dart_results, glsl_results = [], [], []
    scanned = {"py": [], "dart": [], "glsl": []}

    for subdir, _, files in os.walk(root_dir):
        for file in files:
            full_path = Path(os.path.join(subdir, file)).resolve()
            try:
                rel_path = os.path.relpath(str(full_path), str(root_path))
            except ValueError:
                continue  # skip files on different drives / Windows device names
            ext = full_path.suffix.lower()

            # Only scan supported extensions
            if ext not in SCAN_EXTENSIONS:
                continue

            # Skip gitignored files
            if gitignore_spec.match_file(rel_path):
                continue

            # Skip generated Dart files
            if any(file.endswith(s) for s in DART_GENERATED_SUFFIXES):
                print(f"  Skipped (generated): {rel_path}")
                continue

            print(f"Scanning: {rel_path}")

            if ext == ".py":
                if not is_likely_real_python(full_path):
                    continue
                results = scan_python(full_path)
                py_results.extend(results)
                scanned["py"].append(rel_path)

            elif ext == ".dart":
                if full_path.stat().st_size < 30:
                    print(f"  Skipped (too small): {rel_path}")
                    continue
                results = scan_dart(full_path)
                dart_results.extend(results)
                scanned["dart"].append(rel_path)

            elif ext in (".frag", ".vert"):
                results = scan_glsl(full_path)
                glsl_results.extend(results)
                scanned["glsl"].append(rel_path)

    return py_results, dart_results, glsl_results, scanned


# ─── Entry point ─────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print("Scanning for hardcoded literals (respecting .gitignore)...\n")

    py_results, dart_results, glsl_results, scanned = find_hardcoded_vars(
        str(PROJECT_ROOT)
    )

    total_results = len(py_results) + len(dart_results) + len(glsl_results)
    total_files = len(scanned["py"]) + len(scanned["dart"]) + len(scanned["glsl"])

    # ── Console output ──
    if py_results:
        print(f"\n{'-'*60}")
        print(f"Python -- {len(py_results)} hardcoded literal(s):")
        print("-" * 60)
        for item in py_results:
            print(f"  {item}")

    if dart_results:
        print(f"\n{'-'*60}")
        print(f"Dart -- {len(dart_results)} hardcoded literal(s):")
        print("-" * 60)
        for item in dart_results:
            print(f"  {item}")

    if glsl_results:
        print(f"\n{'-'*60}")
        print(f"GLSL -- {len(glsl_results)} constant(s):")
        print("-" * 60)
        for item in glsl_results:
            print(f"  {item}")

    if total_results == 0:
        print("\nNo hardcoded literal assignments found.")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"Summary: {total_results} finding(s) across {total_files} file(s)")
    print("=" * 60)
    for lang, label in [("py", "Python"), ("dart", "Dart"), ("glsl", "GLSL")]:
        if scanned[lang]:
            print(f"\n  {label} ({len(scanned[lang])} files):")
            for f in sorted(scanned[lang]):
                print(f"    - {f}")

    if total_files == 0:
        print("  (no scannable files found outside ignored folders)")

    # ── Save to file ──
    output_file = SCRIPT_DIR / "hardcoded_vars.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Hardcoded Literal Scan Results\n")
        f.write(f"Project: {PROJECT_ROOT}\n")
        f.write("=" * 60 + "\n\n")

        for label, results in [
            ("Python", py_results),
            ("Dart", dart_results),
            ("GLSL", glsl_results),
        ]:
            if results:
                f.write(f"{label} --{len(results)} finding(s):\n")
                for item in results:
                    f.write(f"  {item}\n")
                f.write("\n")

        if total_results == 0:
            f.write("No hardcoded literal assignments found.\n\n")

        f.write("=" * 60 + "\n")
        f.write(f"Scanned {total_files} file(s):\n")
        for lang, label in [("py", "Python"), ("dart", "Dart"), ("glsl", "GLSL")]:
            if scanned[lang]:
                f.write(f"\n  {label} ({len(scanned[lang])}):\n")
                for sf in sorted(scanned[lang]):
                    f.write(f"    - {sf}\n")

    print(f"\nResults saved -> {output_file}")
