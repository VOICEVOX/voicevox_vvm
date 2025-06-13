"""
分割されたVVMファイルを結合するスクリプト
"""

import re
from pathlib import Path


def main():
    vvm_dir = Path("vvms")

    split_files = get_split_vvm_files(vvm_dir)
    if not split_files:
        print("分割されたVVMファイルが見つかりませんでした。")
        return

    file_groups = group_split_files(split_files)
    for base_name, files in file_groups.items():
        merged_file = merge_vvm_files(base_name, files)
        print(f"{len(files)} 個のファイルを {merged_file.name} に結合しました")


def get_split_vvm_files(vvm_dir: Path) -> list[Path]:
    """分割されたVVMファイル一覧を取得"""
    if not vvm_dir.exists():
        raise FileNotFoundError(f"VVMディレクトリが見つかりません: {vvm_dir}")

    pattern = re.compile(r"(.+)\.vvm\.(\d{3})$")

    split_files = []
    for file_path in vvm_dir.iterdir():
        match = pattern.match(file_path.name)
        if match and file_path.is_file():
            split_files.append(file_path)

    return split_files


def group_split_files(split_files: list[Path]) -> dict[str, list[Path]]:
    """分割ファイルをベースファイル名でグループ化"""
    pattern = re.compile(r"(.+)\.vvm\.(\d{3})$")

    file_groups = {}
    for file_path in split_files:
        match = pattern.match(file_path.name)
        if match:
            base_name = match.group(1)
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)

    for base_name in file_groups:
        file_groups[base_name].sort(key=lambda p: int(p.name.split(".")[-1]))

    return file_groups


def merge_vvm_files(base_name: str, split_files: list[Path]) -> Path:
    """分割されたファイルをマージ"""
    if not split_files:
        raise ValueError("分割ファイルが指定されていません")

    output_path = split_files[0].parent / f"{base_name}.vvm"

    all_data = bytearray()
    for file_path in split_files:
        all_data.extend(file_path.read_bytes())
        file_path.unlink()

    output_path.write_bytes(all_data)

    return output_path


if __name__ == "__main__":
    main()
