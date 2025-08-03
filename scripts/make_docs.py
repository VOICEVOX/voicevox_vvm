"""
VVM関連の利用規約と、VVM内に含まれる声（キャラクター＋スタイル）の一覧ドキュメントを更新する。

このスクリプトを実行する前に、必ず scripts/merge_vvm.py を実行してVVMファイルを結合してください。
"""

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib import request


@dataclass
class Terms:
    markdown: str
    text: str


@dataclass
class StyleEntry:
    vvm_file_name: str
    speaker_name: str
    style_name: str
    style_id: int


def main():
    terms = fetch_terms()

    vvm_files = get_vvm_files()
    assert len(vvm_files) > 0, "VVMが見つかりませんでした。"
    vvm_text = generate_vvm_text(vvm_files)

    readme_path = Path("README.md")
    update_readme(readme_path=readme_path, terms=terms, vvm_text=vvm_text)
    print(f"{readme_path} has been updated!")

    terms_path = Path("TERMS.txt")
    update_terms(terms_path=terms_path, terms=terms)
    print(f"{terms_path} has been updated!")


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
    vvms_dir_paths = Path("vvms").glob("*.vvm")
    return sorted(
        vvms_dir_paths,
        key=lambda p: tuple(
            int(chunk) if chunk.isdigit() else chunk
            for chunk in re.split(r"(\d+)", p.stem)
        ),
    )


def generate_vvm_text(vvm_files: list[Path]):
    """vvmファイル内のmetas.jsonを読み込み、トークとソング用の分離されたテーブルを生成"""

    talk_entries: list[StyleEntry] = []
    song_entries: list[StyleEntry] = []

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

                        entry_data = StyleEntry(
                            vvm_file_name=vvm_file.name,
                            speaker_name=speaker_name,
                            style_name=style_name,
                            style_id=style_id,
                        )
                        if style_type == "talk":
                            talk_entries.append(entry_data)
                        else:
                            song_entries.append(entry_data)

    output_text = "# 音声モデル(.vvm)ファイルと声（キャラクター・スタイル名）とスタイル ID の対応表\n\n"

    output_text += generate_table("トーク", talk_entries)
    output_text += "\n"
    output_text += generate_table("ソング", song_entries)

    return output_text


def get_style_type(style: dict) -> Literal["talk", "song"]:
    """スタイルがソングかトークかを判定"""
    style_type = style.get("type", None)
    if style_type in ["frame_decode", "singing_teacher"]:
        return "song"
    else:
        return "talk"


def generate_table(section_name: str, entries: list[StyleEntry]) -> str:
    """指定されたエントリからMarkdownテーブルを生成"""
    table_text = f"## {section_name}\n\n"
    table_text += "| VVMファイル名 | 話者名 | スタイル名 | スタイルID |\n"
    table_text += "|---|---|---|---|\n"
    for entry in entries:
        table_text += f"| {entry.vvm_file_name} | {entry.speaker_name} | {entry.style_name} | {entry.style_id} |\n"
    return table_text


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
