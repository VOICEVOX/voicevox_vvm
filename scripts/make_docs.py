"""
VVM関連の利用規約と、VVM内に含まれる声（キャラクター＋スタイル）の一覧ドキュメントを更新する
"""

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib import request


@dataclass
class Terms:
    markdown: str
    text: str


def main():
    terms = fetch_terms()

    vvm_files = get_vvm_files()
    assert len(vvm_files) > 0, "VVMが見つかりませんでした。"
    vvm_text = generate_vvm_text(vvm_files)

    # Clean up any temporary merged files
    cleanup_temp_merged_files()

    readme_path = Path("README.md")
    update_readme(readme_path=readme_path, terms=terms, vvm_text=vvm_text)
    print(f"{readme_path} has been updated!")

    terms_path = Path("TERMS.txt")
    update_terms(terms_path=terms_path, terms=terms)
    print(f"{terms_path} has been updated!")


def cleanup_temp_merged_files():
    """一時的に作成されたマージファイルをクリーンアップ"""
    vvms_dir = Path("vvms")
    split_files = get_split_vvm_files(vvms_dir)
    
    if split_files:
        file_groups = group_split_files(split_files)
        for base_name in file_groups.keys():
            temp_file = vvms_dir / f"{base_name}.vvm"
            if temp_file.exists():
                # 対応する.001ファイルが存在する場合のみ削除（一時ファイルの確認）
                split_file_001 = vvms_dir / f"{base_name}.vvm.001"
                if split_file_001.exists():
                    temp_file.unlink()
                    print(f"Cleaned up temporary file: {temp_file.name}")


def fetch_terms() -> Terms:
    """VOICEVOXのリポジトリから利用規約を取得"""
    base_url = (
        "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/refs/heads/main/"
    )

    markdown_url = base_url + "vvm/README.md"
    with request.urlopen(markdown_url) as response:
        markdown = response.read().decode("utf-8")

    text_url = base_url + "vvm/README.txt"
    with request.urlopen(text_url) as response:
        text = response.read().decode("utf-8")

    return Terms(markdown=markdown, text=text)


def get_vvm_files() -> list[Path]:
    vvms_dir_paths = list(Path("vvms").glob("*.vvm"))
    
    # Check for split files and temporarily merge them for processing
    split_files = get_split_vvm_files(Path("vvms"))
    
    if split_files:
        file_groups = group_split_files(split_files)
        for base_name, files in file_groups.items():
            # Create temporary merged file for processing
            temp_merged_file = create_temp_merged_vvm(base_name, files)
            vvms_dir_paths.append(temp_merged_file)
    
    return sorted(
        vvms_dir_paths,
        key=lambda p: tuple(
            int(chunk) if chunk.isdigit() else chunk
            for chunk in re.split(r"(\d+)", p.stem)
        ),
    )


def get_split_vvm_files(vvm_dir: Path) -> list[Path]:
    """分割されたVVMファイル一覧を取得"""
    if not vvm_dir.exists():
        return []
    
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


def create_temp_merged_vvm(base_name: str, split_files: list[Path]) -> Path:
    """分割されたファイルを一時的にマージ（元ファイルは削除しない）"""
    if not split_files:
        raise ValueError("分割ファイルが指定されていません")
    
    temp_output_path = split_files[0].parent / f"{base_name}.vvm"
    
    # 元のファイルが存在する場合は何もしない
    if temp_output_path.exists():
        return temp_output_path
    
    all_data = bytearray()
    for file_path in split_files:
        all_data.extend(file_path.read_bytes())
    
    temp_output_path.write_bytes(all_data)
    
    return temp_output_path


def get_style_type(style: dict) -> str:
    """スタイルがソングかトークかを判定"""
    style_type = style.get("type", "")
    if style_type in ["frame_decode", "singing_teacher"]:
        return "ソング"
    else:
        return "トーク"


def generate_vvm_text(vvm_files: list[Path]):
    """vvmファイル内のmetas.jsonを読み込み、トークとソング用の分離されたテーブルを生成"""

    talk_entries = []
    song_entries = []

    for vvm_file in vvm_files:
        with zipfile.ZipFile(vvm_file, "r") as zipf:
            with zipf.open("metas.json") as f:
                data = json.load(f)
                for entry in data:
                    speaker_name = entry["name"]
                    for style in entry["styles"]:
                        style_name = style["name"]
                        style_id = style["id"]
                        style_type = get_style_type(style)
                        
                        entry_data = (vvm_file.name, speaker_name, style_name, style_id)
                        if style_type == "トーク":
                            talk_entries.append(entry_data)
                        else:
                            song_entries.append(entry_data)

    output_text = "# 音声モデル(.vvm)ファイルと声（キャラクター・スタイル名）とスタイル ID の対応表\n\n"
    
    # トーク用テーブル
    output_text += "## トーク\n\n"
    output_text += "| VVMファイル名 | 話者名 | スタイル名 | スタイルID |\n"
    output_text += "|---|---|---|---|\n"
    for vvm_file_name, speaker_name, style_name, style_id in talk_entries:
        output_text += f"| {vvm_file_name} | {speaker_name} | {style_name} | {style_id} |\n"
    
    # ソング用テーブル
    output_text += "\n## ソング\n\n"
    output_text += "| VVMファイル名 | 話者名 | スタイル名 | スタイルID |\n"
    output_text += "|---|---|---|---|\n"
    for vvm_file_name, speaker_name, style_name, style_id in song_entries:
        output_text += f"| {vvm_file_name} | {speaker_name} | {style_name} | {style_id} |\n"

    return output_text


def update_readme(readme_path: Path, terms: Terms, vvm_text: str):
    """README.mdの内容を置換"""
    readme_text = readme_path.read_text(encoding="utf-8")

    def update_section(pattern: str, target: str) -> str:
        match = re.search(pattern, readme_text, flags=re.DOTALL)
        if match:
            return readme_text[: match.start()] + target + readme_text[match.end() :]
        else:
            raise ValueError(
                f"対象範囲がREADME.mdに見つかりませんでした。 pattern: {pattern}"
            )

    readme_text = update_section(
        pattern=r"(?<=<!-- terms start -->\n\n).*?(?=\n<!-- terms end -->)",
        target=terms.markdown,
    )
    readme_text = update_section(
        pattern=r"(?<=<!-- vvm-table start -->\n\n).*?(?=\n<!-- vvm-table end -->)",
        target=vvm_text,
    )
    readme_path.write_text(readme_text, encoding="utf-8")


def update_terms(terms_path: Path, terms: Terms):
    """利用規約テキストを更新"""
    terms_path.write_text(terms.text, encoding="utf-8")


if __name__ == "__main__":
    main()
