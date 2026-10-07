"""小模型跟大模型學（四）：把訓練好的模型打包成 GitHub Release 附件。

做法：複製 models/en_core_web_sm_distilled → 改模型說明（名稱、版本、資料來源、授權）→ 附 README → 壓成 .tar.gz。
Render 部署時下載這個附件、解壓到 models/（見 render.yaml），程式用 SPACY_MODEL 指到那個資料夾。

用法：
  python tools/distill_package.py 1.0.0
輸出：models/en_core_web_sm_distilled-1.0.0.tar.gz（models/ 不上傳；這個檔案上傳到 GitHub Release）
"""
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "models" / "en_core_web_sm_distilled"
NAME = "en_core_web_sm_distilled"

README = """# en_core_web_sm_distilled {version}

英文句子骨架分析網站（https://github.com/LuniHorn27/english-sentence-skeleton）的小型分析模型。

從 spaCy 的 en_core_web_sm 3.8.0（MIT）出發，用大型模型 en_core_web_trf 3.8.0（MIT）分析的
{n_train} 句 Tatoeba 英文句子（CC BY 2.0 FR，https://tatoeba.org）繼續訓練「字的特徵、詞性、句子結構」。
人名地名辨識、原形規則沒有改。不需要 PyTorch，大小和記憶體跟 en_core_web_sm 差不多。

訓練、檢查方式見專案的 tools/distill_*.py。

授權：MIT。訓練句子來自 Tatoeba（CC BY 2.0 FR），模型原始版本來自 Explosion 的 en_core_web_sm。
"""


def main():
    from spacy.tokens import DocBin

    version = sys.argv[1]
    total = sum(len(DocBin().from_disk(f)) for f in sorted((ROOT / "data" / "distill").glob("train*.spacy")))
    assert total, "找不到訓練資料（data/distill/train*.spacy）"

    out_dir = ROOT / "models" / f"{NAME}-{version}" / NAME
    shutil.rmtree(out_dir.parent, ignore_errors=True)
    shutil.copytree(SRC, out_dir)
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({
        "name": "core_web_sm_distilled",
        "version": version,
        "description": f"en_core_web_sm 3.8.0 fine-tuned on {total:,} Tatoeba sentences labelled by en_core_web_trf 3.8.0 "
                       "(tagger and parser only). For https://github.com/LuniHorn27/english-sentence-skeleton",
        "license": "MIT",
    })
    meta["sources"] = meta.get("sources", []) + [
        {"name": "Tatoeba", "url": "https://tatoeba.org", "license": "CC BY 2.0 FR"},
        {"name": "en_core_web_trf 3.8.0 (labels)", "url": "https://github.com/explosion/spacy-models", "license": "MIT"},
    ]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "README.md").write_text(README.format(version=version, n_train=f"{total:,}"), encoding="utf-8")

    tar_path = ROOT / "models" / f"{NAME}-{version}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(out_dir, arcname=NAME)
    shutil.rmtree(out_dir.parent)
    print(f"打包好：{tar_path.relative_to(ROOT)}（{tar_path.stat().st_size / 1e6:.1f} MB，訓練 {total:,} 句）")


if __name__ == "__main__":
    main()
