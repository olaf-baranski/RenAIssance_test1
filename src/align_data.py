import shutil
import subprocess
from pathlib import Path
from lxml import etree

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent

    raw_pages_dir = base_dir / "data" / "raw_pages"
    clean_dir = base_dir / "data" / "train_pages_clean"
    clean_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(raw_pages_dir.glob("*.txt"))

    if not txt_files:
        print("No .txt transcript files found.")
        return

    print(f"Found {len(txt_files)} transcript files.")
    print("Building CLEAN training subset only\n")

    kept = 0
    skipped = 0

    for txt_path in txt_files:
        stem = txt_path.stem
        png_path = raw_pages_dir / f"{stem}.png"

        if not png_path.exists():
            print(f"SKIP Missing PNG for {stem}")
            skipped += 1
            continue

        out_png = clean_dir / png_path.name
        out_txt = clean_dir / txt_path.name
        out_xml = clean_dir / f"{stem}.xml"

        print(f"Processing {stem}")

        cmd = [
            "kraken",
            "-x",
            "-i", str(png_path),
            str(out_xml),
            "binarize",
            "segment"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or not out_xml.exists():
            print(f"SKIP Kraken segmentation failed for {stem}")
            if result.stderr:
                print(result.stderr.strip())
            skipped += 1
            continue

        with open(txt_path, "r", encoding="utf-8") as f:
            gt_lines = [line.rstrip("\r\n") for line in f if line.rstrip("\r\n") != ""]

        try:
            tree = etree.parse(str(out_xml))

            page_el = tree.xpath('//*[local-name()="Page"]')[0]
            page_el.set("imageFilename", out_png.name)

            xml_lines = tree.xpath('//*[local-name()="TextLine"]')

            if len(xml_lines) != len(gt_lines):
                print(f"   [SKIP] Line mismatch: XML={len(xml_lines)} TXT={len(gt_lines)}")
                out_xml.unlink(missing_ok=True)
                skipped += 1
                continue

            for xml_line, gt_line in zip(xml_lines, gt_lines):
                for child in list(xml_line):
                    if etree.QName(child).localname == "TextEquiv":
                        xml_line.remove(child)

                ns = xml_line.nsmap.get(None, "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15")
                text_equiv = etree.SubElement(xml_line, f"{{{ns}}}TextEquiv")
                unicode_el = etree.SubElement(text_equiv, f"{{{ns}}}Unicode")
                unicode_el.text = gt_line

            final_texts = tree.xpath(
                '//*[local-name()="TextLine"]/*[local-name()="TextEquiv"]/*[local-name()="Unicode"]/text()'
            )
            if len(final_texts) != len(gt_lines):
                print(f"   [SKIP] Final validation failed for {stem}")
                out_xml.unlink(missing_ok=True)
                skipped += 1
                continue

            shutil.copy2(png_path, out_png)
            shutil.copy2(txt_path, out_txt)

            tree.write(str(out_xml), encoding="utf-8", xml_declaration=True, pretty_print=True)
            print(f"KEEP Clean PAGE XML written: {out_xml.name}")
            kept += 1

        except Exception as e:
            print(f"SKIP XML processing failed for {stem}: {e}")
            out_xml.unlink(missing_ok=True)
            skipped += 1
            continue

    print("\nDone.")
    print(f"Kept pages   : {kept}")
    print(f"Skipped pages: {skipped}")
    print(f"Output dir   : {clean_dir}")

if __name__ == "__main__":
    main()