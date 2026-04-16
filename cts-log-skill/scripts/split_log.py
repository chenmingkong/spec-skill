#!/usr/bin/env python3
"""
CTS 日志切分工具
将大型 CTS 日志文件切分为多个片段，便于逐片分析
"""
import argparse
import json
import sys
from pathlib import Path


def split_log(log_file: str, chunk_size: int = 5000, output_dir: str = None) -> list:
    """
    将日志文件切分为多个片段。

    Args:
        log_file:   日志文件路径
        chunk_size: 每个片段的最大行数（默认 5000）
        output_dir: 输出目录；默认为 skill 目录下的 workspace/<日志文件名>/

    Returns:
        切分后的文件路径列表（按顺序）
    """
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"[ERROR] 日志文件不存在：{log_file}", file=sys.stderr)
        sys.exit(1)

    if output_dir:
        out_dir = Path(output_dir)
    else:
        skill_dir = Path(__file__).parent.parent          # scripts/ 的上一级 = cts-log-skill/
        out_dir = skill_dir / "workspace" / log_path.stem

    out_dir.mkdir(parents=True, exist_ok=True)

    # 读取全部行
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)
    total_chunks = max(1, (total_lines + chunk_size - 1) // chunk_size)

    chunk_files = []
    for i in range(total_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, total_lines)

        chunk_path = out_dir / f"chunk_{i + 1:03d}_of_{total_chunks:03d}.log"
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.writelines(lines[start:end])

        chunk_files.append(str(chunk_path))
        print(f"  片段 {i + 1:>3}/{total_chunks}  行 {start + 1:>7} ~ {end:<7}  → {chunk_path.name}")

    print(f"\n切分完成：{total_lines} 行 / {total_chunks} 片段（每片段上限 {chunk_size} 行）")
    print(f"输出目录：{out_dir}\n")

    # 输出 JSON 摘要，方便调用方解析
    summary = {
        "log_file": str(log_path.resolve()),
        "total_lines": total_lines,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "output_dir": str(out_dir),
        "chunk_files": chunk_files,
    }
    summary_path = out_dir / "split_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"摘要已写入：{summary_path}")

    return chunk_files


def main():
    parser = argparse.ArgumentParser(
        description="CTS 日志切分工具 —— 将大型日志文件切分为固定行数的片段"
    )
    parser.add_argument("log_file", help="CTS 日志文件路径（绝对或相对路径）")
    parser.add_argument(
        "--chunk-size", "-n",
        type=int,
        default=5000,
        help="每个片段的最大行数（默认 5000）",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="切分片段的输出目录（默认：skill目录/workspace/<日志文件名>/）",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="仅输出切分后的文件路径列表（每行一个），不做任何说明",
    )

    args = parser.parse_args()
    chunk_files = split_log(args.log_file, args.chunk_size, args.output_dir)

    if args.list_only:
        for f in chunk_files:
            print(f)
    else:
        print("\n=== 切分文件列表 ===")
        for idx, f in enumerate(chunk_files, 1):
            print(f"  [{idx}] {f}")


if __name__ == "__main__":
    main()
