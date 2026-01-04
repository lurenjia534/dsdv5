#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys


def decode_text(path):
    with open(path, "rb") as f:
        data = f.read()
    # 处理常见 BOM，避免 JSON 里出现乱码。
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="ignore")
    return data.decode("utf-8", errors="ignore")


def is_cjk(ch):
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
    )


def has_cjk(text):
    return any(is_cjk(ch) for ch in text)


def opencc_convert(text):
    # 调用 opencc 的 t2s 转换；失败时返回 None。
    result = subprocess.run(
        ["opencc", "-c", "t2s.json"],
        input=text,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


_CHAR_CACHE = {}


def is_traditional_char(ch):
    cached = _CHAR_CACHE.get(ch)
    if cached is not None:
        return cached
    mapped = opencc_convert(ch)
    is_trad = mapped is not None and mapped != ch
    _CHAR_CACHE[ch] = is_trad
    return is_trad


def find_traditional_chars(text):
    if not has_cjk(text):
        return []
    converted = opencc_convert(text)
    if converted is None or converted == text:
        return []
    chars = set()
    if len(converted) == len(text):
        # 快速路径：一对一转换时，按位置逐字比对。
        for original, simplified in zip(text, converted):
            if is_cjk(original) and original != simplified:
                chars.add(original)
        if chars:
            return sorted(chars)
    # 兜底路径：转换后长度变化时，逐字探测。
    for ch in text:
        if is_cjk(ch) and is_traditional_char(ch):
            chars.add(ch)
    return sorted(chars)


def has_traditional(text):
    return bool(find_traditional_chars(text))


def traditional_char_positions(text, one_based=False):
    positions = {}
    for index, ch in enumerate(text):
        if not is_cjk(ch):
            continue
        if not is_traditional_char(ch):
            continue
        pos = index + 1 if one_based else index
        positions.setdefault(ch, []).append(pos)
    return positions


def json_pointer_escape(token):
    return token.replace("~", "~0").replace("/", "~1")


def collect_json_strings(value, path, output):
    if isinstance(value, str):
        output.append((path, value))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            collect_json_strings(item, f"{path}/{index}", output)
        return
    if isinstance(value, dict):
        # 对 JSON 对象 key 使用 JSON Pointer 转义规则。
        for key, item in value.items():
            next_path = f"{path}/{json_pointer_escape(str(key))}"
            collect_json_strings(item, next_path, output)
        return


def file_has_traditional(path):
    try:
        text = decode_text(path)
    except OSError:
        return False
    strings = extract_json_strings(text)
    for _, value in strings:
        if has_traditional(value):
            return True
    return False


def file_traditional_details(path, one_based=False):
    try:
        text = decode_text(path)
    except OSError:
        return []
    details = []
    strings = extract_json_strings(text)
    for json_path, value in strings:
        positions = traditional_char_positions(value, one_based=one_based)
        if positions:
            details.append((format_json_path(json_path), value, positions))
    return details


def extract_json_strings(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 非 JSON 文本时，作为一个整体字符串处理。
        return [("/", text)]
    strings = []
    collect_json_strings(data, "", strings)
    if not strings:
        return []
    return strings


def format_json_path(path):
    return path if path else "/"


def is_json_file(name):
    return name.lower().endswith(".json")


def preview_text(text, limit=160):
    # 预览用：转义控制字符并截断过长文本。
    cleaned = (
        text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    )
    if len(cleaned) > limit:
        return f"{cleaned[: limit - 3]}..."
    return cleaned


def iter_top_dirs(base):
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if os.path.isdir(path):
            yield name, path


def main():
    if not shutil.which("opencc"):
        print("opencc not found. Please install it or adjust the script.", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(
        description="Find JSON files containing Traditional Chinese characters."
    )
    # 模式互斥：只允许汇总或详情输出之一。
    mode = parser.add_mutually_exclusive_group()
    # --summary：按文件夹汇总 YES/NO。
    mode.add_argument(
        "--summary",
        action="store_true",
        help="Show per-folder YES/NO summary instead of listing files.",
    )
    # --details：输出每个 JSON 路径的命中字符串与字符位置。
    mode.add_argument(
        "--details",
        action="store_true",
        help="Show JSON path and matched string values per file.",
    )
    # --one-based：位置索引用 1 基（仅在 --details 下生效）。
    parser.add_argument(
        "--one-based",
        action="store_true",
        help="Use 1-based indexes for character positions (details mode only).",
    )
    # --files：在 --summary 模式下列出命中的 JSON 路径。
    parser.add_argument(
        "--files",
        action="store_true",
        help="Show matched JSON paths under each folder (summary mode only).",
    )
    args = parser.parse_args()

    base = os.getcwd()
    dirs = list(iter_top_dirs(base))
    if not dirs:
        print("No folders found in the current directory.")
        return 0

    any_match = False
    for name, path in dirs:
        matched = []
        for root, _, files in os.walk(path):
            for file_name in files:
                if not is_json_file(file_name):
                    continue
                file_path = os.path.join(root, file_name)
                rel = os.path.relpath(file_path, base)
                if args.details:
                    details = file_traditional_details(file_path, one_based=args.one_based)
                    if details:
                        any_match = True
                        print(rel)
                        for json_path, value, positions in details:
                            preview = preview_text(value)
                            print(f"  {json_path} {preview}")
                            for ch, pos_list in positions.items():
                                pos_str = ",".join(str(pos) for pos in pos_list)
                                print(f"    {ch} x{len(pos_list)} @{pos_str}")
                else:
                    if file_has_traditional(file_path):
                        matched.append(rel)
                        if args.summary and not args.files:
                            break
            if matched and args.summary and not args.files:
                break
        if args.summary:
            print(f"{name}\t{'YES' if matched else 'NO'}")
            if args.files and matched:
                for rel_path in matched:
                    print(f"  {rel_path}")
        elif not args.details:
            for rel_path in matched:
                any_match = True
                print(rel_path)
    if not args.summary and not args.details and not any_match:
        print("No JSON files with Traditional Chinese found.")
    if args.details and not any_match:
        print("No JSON files with Traditional Chinese found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
