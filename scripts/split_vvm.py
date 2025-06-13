"""
大きなVVMファイルを分割するスクリプト
"""

from pathlib import Path


def main():
    vvm_dir = Path("vvms")
    max_size = 100 * 1000 * 1000  # 100MB

    vvm_files = list_vvm_files(vvm_dir)
    for vvm_file in vvm_files:
        filesize = vvm_file.stat().st_size
        if filesize > max_size:
            split_vvm_file(vvm_file, max_size)
            print(
                f"{vvm_file.name} を分割しました (サイズ: {filesize / (1000 * 1000):.1f}MB)"
            )


def list_vvm_files(vvm_dir: Path) -> list[Path]:
    """VVMファイル一覧を取得"""
    if not vvm_dir.exists():
        raise FileNotFoundError(f"VVMディレクトリが見つかりません: {vvm_dir}")

    return list(vvm_dir.glob("*.vvm"))


def split_vvm_file(vvm_file: Path, max_size: int):
    """VVMファイルを分割"""
    filesize = vvm_file.stat().st_size
    if filesize <= max_size:
        return

    num_parts = (filesize + max_size - 1) // max_size
    data = vvm_file.read_bytes()
    chunk_size = filesize // num_parts + (1 if filesize % num_parts else 0)

    for i in range(num_parts):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, filesize)

        chunk = data[start:end]
        output_path = vvm_file.parent / f"{vvm_file.stem}.vvm.{i + 1:03d}"
        output_path.write_bytes(chunk)
    vvm_file.unlink()


if __name__ == "__main__":
    main()
