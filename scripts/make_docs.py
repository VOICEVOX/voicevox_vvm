"""
VVM関連の利用規約と、VVM内に含まれる声（キャラクター＋スタイル）の一覧ドキュメントを更新する。

このスクリプトを実行する前に、必ず scripts/merge_vvm.py を実行してVVMファイルを結合してください。
"""

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never
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


VvmCategory = Literal["talk", "song", "nemo_talk"]


def main():
    terms = fetch_and_generate_terms()

    vvm_files = get_vvm_files()
    assert len(vvm_files) > 0, "VVMが見つかりませんでした。"
    vvm_text = generate_vvm_text(vvm_files)

    readme_path = Path("README.md")
    update_readme(readme_path=readme_path, terms=terms, vvm_text=vvm_text)
    print(f"{readme_path} has been updated!")

    terms_path = Path("TERMS.txt")
    update_terms(terms_path=terms_path, terms=terms)
    print(f"{terms_path} has been updated!")


def fetch_and_generate_terms() -> Terms:
    """VOICEVOXとVOICEVOX Nemoの利用規約を取得し、利用規約を生成"""
    voicevox_terms = fetch_voicevox_terms()
    nemo_terms = fetch_and_extract_nemo_terms()

    combined_markdown = voicevox_terms.markdown.rstrip() + "\n\n" + nemo_terms.markdown
    combined_text = voicevox_terms.text.rstrip() + "\n\n" + nemo_terms.text

    return Terms(markdown=combined_markdown, text=combined_text)


def fetch_voicevox_terms() -> Terms:
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


def fetch_and_extract_nemo_terms() -> Terms:
    """VOICEVOX Nemoの音声ライブラリ利用規約部分を抽出"""
    base_url = (
        "https://raw.githubusercontent.com/VOICEVOX/voicevox_nemo_resource/"
        "refs/heads/main/"
    )

    markdown_url = base_url + "voicevox_nemo/vvm/README.md"
    with request.urlopen(markdown_url) as response:
        full_markdown = response.read().decode("utf-8")

    text_url = base_url + "voicevox_nemo/vvm/README.txt"
    with request.urlopen(text_url) as response:
        full_text = response.read().decode("utf-8")

    markdown = extract_nemo_section(full_markdown)
    text = extract_nemo_section(full_text)

    return Terms(markdown=markdown, text=text)


def extract_nemo_section(content: str) -> str:
    """VOICEVOX Nemo音声ライブラリ利用規約のセクションを抽出"""
    parts = content.split("---")
    if len(parts) != 2:
        raise ValueError("利用規約のフォーマットが想定と異なります。")

    voice_library_section = parts[1].strip()

    lines = voice_library_section.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("## VOICEVOX Nemo"):
            nemo_start_index = i
            break
    else:
        raise ValueError("VOICEVOX Nemoのセクションが見つかりません。")

    nemo_section = "\n".join(lines[nemo_start_index:]).strip() + "\n"

    return nemo_section


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
    """vvmファイル内のmetas.jsonを読み込み、トーク・ソング・Nemoトーク用の分離されたテーブルを生成"""

    talk_entries: list[StyleEntry] = []
    song_entries: list[StyleEntry] = []
    nemo_talk_entries: list[StyleEntry] = []

    for vvm_file in vvm_files:
        with zipfile.ZipFile(vvm_file, "r") as zipf:
            with zipf.open("metas.json") as f:
                data = json.load(f)
                for entry in data:
                    speaker_name = entry["name"]
                    for style in entry["styles"]:
                        style_name = style["name"]
                        style_id = style["id"]
                        vvm_category = get_vvm_category(vvm_file, style)

                        entry_data = StyleEntry(
                            vvm_file_name=vvm_file.name,
                            speaker_name=speaker_name,
                            style_name=style_name,
                            style_id=style_id,
                        )
                        match vvm_category:
                            case "talk":
                                talk_entries.append(entry_data)
                            case "song":
                                song_entries.append(entry_data)
                            case "nemo_talk":
                                nemo_talk_entries.append(entry_data)
                            case _:
                                assert_never(vvm_category)

    output_text = "# 音声モデル(.vvm)ファイルと声（キャラクター・スタイル名）とスタイル ID の対応表\n\n"

    output_text += generate_table("トーク", talk_entries)
    output_text += "\n"
    output_text += generate_table("ソング", song_entries)
    output_text += "\n"
    output_text += generate_table("Nemo トーク", nemo_talk_entries)

    return output_text


def get_vvm_category(vvm_file: Path, style: dict) -> VvmCategory:
    """VVMのカテゴリを判定"""
    style_type = style.get("type", None)
    is_song = style_type in ["frame_decode", "singing_teacher", "sing"]
    is_nemo = re.match(r"^n\d+\.vvm$", vvm_file.name) is not None

    if is_song:
        return "song"
    else:
        if is_nemo:
            return "nemo_talk"
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
