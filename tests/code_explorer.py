import os
import ast
import json
import re
import sys
from collections import Counter

# Directories to never descend into
SKIP_DIRS = {
    # VCS / caches
    '.git', '__pycache__', '.dart_tool', '.pytest_cache',
    # IDE / tooling
    '.idea', '.vscode', '.VSCodeCounter', '.claude', '.gradle',
    # Virtual environments
    '.venv', 'venv', 'env',
    # Build artifacts
    'build', 'node_modules', '.pub-cache', '.pub', 'dist', 'htmlcov',
    # Platform dirs (Flutter)
    'ios', 'android', 'web', 'linux', 'macos', 'windows',
    # Project-specific noise
    'deprecated', 'logs', 'assets', 'docs',
}

# Dart keywords that regex false-positives as functions/calls
DART_KEYWORDS = {
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'catch',
    'try', 'finally', 'return', 'throw', 'assert', 'new', 'const',
    'var', 'final', 'class', 'extends', 'implements', 'with', 'mixin',
    'enum', 'typedef', 'import', 'export', 'part', 'library', 'show',
    'hide', 'as', 'is', 'in', 'on', 'super', 'this', 'late', 'print',
}

# Minimum occurrences before an import gets a token
TOKEN_THRESHOLD = 3


def extract_python(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"imports": [], "classes": [], "functions": []}

    imports = []
    classes = []
    functions = []

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                s = f"import {alias.name}"
                if alias.asname:
                    s += f" as {alias.asname}"
                imports.append(s)
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            module = node.module or ''
            for alias in node.names:
                s = f"from {module} import {alias.name}"
                if alias.asname:
                    s += f" as {alias.asname}"
                imports.append(s)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(f"{b.value.id}.{b.attr}" if isinstance(b.value, ast.Name) else b.attr)
            sig = f"{node.name}({', '.join(bases)})" if bases else node.name
            classes.append(sig)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            args = [a.arg for a in node.args.args]
            functions.append(f"{node.name}({', '.join(args)})")
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

    Visitor().visit(tree)
    return {"imports": imports, "classes": classes, "functions": functions}


def extract_dart(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    clean = re.sub(r'//.*', '', code)
    clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

    imports = re.findall(r"^import\s+['\"](.+?)['\"]", clean, re.MULTILINE)
    classes = re.findall(r'\bclass\s+(\w+)', clean)
    classes += re.findall(r'\bmixin\s+(\w+)', clean)

    dart_types = r'(?:void|Future|Stream|Widget|State|String|int|double|num|bool|List|Map|Set|dynamic|Object|Iterable)'
    fn_re = dart_types + r'(?:<[^>]*>)?\??\s+(\w+)\s*(?:<[^>]*>)?\s*\('
    functions = re.findall(fn_re, clean)
    functions = sorted(set(f for f in functions if f not in DART_KEYWORDS))

    return {"imports": imports, "classes": classes, "functions": functions}


def extract_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return list(data.keys())
        if isinstance(data, list):
            return [f"(array of {len(data)})"]
        return [str(type(data).__name__)]
    except Exception:
        return ["(parse error)"]


def build_token_map(all_imports):
    """Assign short tokens to imports that repeat >= TOKEN_THRESHOLD times."""
    counts = Counter(all_imports)
    # Sort by frequency descending so the most common get the shortest mental scan
    frequent = [(imp, n) for imp, n in counts.most_common() if n >= TOKEN_THRESHOLD]
    token_map = {}  # import string -> token
    for i, (imp, _) in enumerate(frequent):
        token_map[imp] = f"I{i + 1}"
    return token_map


def fmt_inline(title, items, token_map=None):
    """Render a compact inline section."""
    if not items:
        return ""
    if token_map:
        items = [token_map.get(x, x) for x in items]
    return f"  {title}: {', '.join(items)}\n"


def generate_skeleton(root_dir='.', output='project_skeleton.md'):
    # --- Pass 1: collect all file data and count imports ---
    file_data = []  # list of (rel_path, lang, data_dict)
    all_imports = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir_raw = os.path.relpath(dirpath, root_dir).replace('\\', '/')

        def keep_dir(d):
            if d.startswith('.'):
                return False
            if d not in SKIP_DIRS:
                return True
            if d == 'assets' and 'chromacrush_app' in rel_dir_raw:
                return True
            return False
        dirnames[:] = sorted(d for d in dirnames if keep_dir(d))

        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''

        for fname in sorted(filenames):
            if fname.startswith('.'):
                continue
            fpath = os.path.join(dirpath, fname)
            rel_path = (os.path.join(rel_dir, fname) if rel_dir else fname).replace('\\', '/')

            if fname.endswith('.py'):
                data = extract_python(fpath)
                lang = 'py'
            elif fname.endswith('.dart'):
                data = extract_dart(fpath)
                lang = 'dart'
            elif fname.endswith('.json'):
                keys = extract_json(fpath)
                file_data.append((rel_path, 'json', {"keys": keys}))
                continue
            else:
                continue

            all_imports.extend(data.get("imports", []))
            file_data.append((rel_path, lang, data))

    # --- Build token legend ---
    token_map = build_token_map(all_imports)
    # Reverse map for the legend: token -> import string
    legend = {v: k for k, v in token_map.items()}

    # --- Pass 2: write output ---
    with open(output, 'w', encoding='utf-8') as f:
        f.write(f"# Project Skeleton — {len(file_data)} files\n\n")

        if legend:
            f.write("## Import Legend\n")
            f.write("| Token | Import |\n|---|---|\n")
            for tok in sorted(legend, key=lambda t: int(t[1:])):
                f.write(f"| {tok} | `{legend[tok]}` |\n")
            f.write("\n")

        # Separate test files from source files
        test_files = []
        source_files = []
        for entry in file_data:
            rel_path = entry[0]
            if '/test/' in rel_path or '/tests/' in rel_path or rel_path.startswith('tests/') or '_test.' in rel_path:
                test_files.append(entry)
            else:
                source_files.append(entry)

        # Write source files (skip empty entries)
        for rel_path, lang, data in source_files:
            if lang == 'json':
                f.write(f"### `{rel_path}` (json)\n")
                f.write(f"  keys: {', '.join(data['keys'])}\n\n")
            else:
                imports = data.get("imports", [])
                classes = data.get("classes", [])
                functions = data.get("functions", [])
                if not imports and not classes and not functions:
                    continue
                f.write(f"### `{rel_path}` ({lang})\n")
                f.write(fmt_inline("imports", imports, token_map))
                f.write(fmt_inline("classes", classes))
                f.write(fmt_inline("functions", functions))
                f.write("\n")

        # Write test files as compact summary
        if test_files:
            f.write("## Test Files\n\n")
            # Group by directory
            test_dirs = {}
            for rel_path, lang, data in test_files:
                d = '/'.join(rel_path.split('/')[:-1]) or '(root)'
                test_dirs.setdefault(d, []).append((rel_path, data))
            for d in sorted(test_dirs):
                f.write(f"**{d}/**\n")
                for rel_path, data in test_dirs[d]:
                    fname = rel_path.split('/')[-1]
                    classes = data.get("classes", [])
                    funcs = data.get("functions", [])
                    # Show just the test class/function names
                    test_names = [c for c in classes] + [fn for fn in funcs if fn.startswith('test')]
                    suffix = f" — {', '.join(test_names)}" if test_names else ""
                    f.write(f"  {fname}{suffix}\n")
                f.write("\n")

    print(f"Done: {output} ({len(file_data)} files, {len(token_map)} tokens in legend)")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    out = sys.argv[2] if len(sys.argv) > 2 else 'project_skeleton.md'
    generate_skeleton(target, out)
