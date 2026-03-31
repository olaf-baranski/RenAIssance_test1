from pathlib import Path
from statistics import median
from lxml import etree
from PIL import Image


def parse_points(points_str: str):
    pts = []
    for pair in points_str.strip().split():
        x, y = pair.split(",")
        pts.append((int(float(x)), int(float(y))))
    return pts


def bbox_from_points(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def collect_lines(xml_path: Path):
    tree = etree.parse(str(xml_path))
    page_el = tree.xpath('//*[local-name()="Page"]')[0]

    image_filename = page_el.get("imageFilename")
    image_width = int(page_el.get("imageWidth"))
    image_height = int(page_el.get("imageHeight"))

    records = []

    textlines = tree.xpath('//*[local-name()="TextLine"]')
    for tl in textlines:
        coords_el = tl.xpath('./*[local-name()="Coords"]')
        text_el = tl.xpath('./*[local-name()="TextEquiv"]/*[local-name()="Unicode"]')

        if not coords_el or not text_el:
            continue

        text = text_el[0].text
        if text is None:
            continue

        text = text.strip()
        if not text:
            continue

        pts = parse_points(coords_el[0].get("points"))
        x0, y0, x1, y1 = bbox_from_points(pts)
        w = x1 - x0
        h = y1 - y0

        if w <= 2 or h <= 2:
            continue

        records.append({
            "text": text,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "w": w,
            "h": h,
            "cx": (x0 + x1) / 2.0,
            "cy": (y0 + y1) / 2.0,
        })

    records.sort(key=lambda r: (r["cy"], r["x0"]))

    return {
        "image_filename": image_filename,
        "image_width": image_width,
        "image_height": image_height,
        "lines": records,
    }


def select_body_lines(page_data):
    lines = page_data["lines"]
    page_h = page_data["image_height"]

    if len(lines) < 6:
        return []

    widths = [l["w"] for l in lines]
    heights = [l["h"] for l in lines]

    med_h = max(1, median(heights))

    filtered = [l for l in lines if l["w"] >= 0.20 * median(widths) and l["h"] >= 0.60 * med_h]
    if len(filtered) < 6:
        return []

    lower_part = [l for l in filtered if l["cy"] > 0.20 * page_h]
    if len(lower_part) < 5:
        lower_part = filtered

    body_x0 = median([l["x0"] for l in lower_part])
    body_w = median([l["w"] for l in lower_part])
    body_h = max(1, median([l["h"] for l in lower_part]))

    kept = []
    for l in filtered:
        if l["cy"] < 0.12 * page_h and l["w"] < 0.75 * body_w:
            continue

        if abs(l["x0"] - body_x0) > max(40, 1.8 * body_h):
            continue

        if l["w"] < max(50, 0.35 * body_w):
            continue

        kept.append(l)

    kept2 = []
    for l in kept:
        if l["h"] > 1.6 * body_h:
            continue

        if l["cy"] < 0.16 * page_h:
            continue

        kept2.append(l)

    kept2.sort(key=lambda r: (r["cy"], r["x0"]))

    if len(kept2) > 4:
        kept2 = kept2[2:]

    return kept2


def main():
    base_dir = Path(__file__).resolve().parent.parent
    xml_dir = base_dir / "data" / "train_pages_clean"
    out_dir = base_dir / "data" / "line_dataset"
    out_dir.mkdir(parents=True, exist_ok=True)

    for old in out_dir.glob("*"):
        if old.is_file():
            old.unlink()

    xml_files = sorted(xml_dir.glob("*.xml"))
    line_counter = 1
    kept_pages = 0
    skipped_pages = 0
    kept_lines = 0

    for xml_path in xml_files:
        try:
            page_data = collect_lines(xml_path)
        except Exception as e:
            print(f"SKIP {xml_path.name}: XML parse error: {e}")
            skipped_pages += 1
            continue

        image_filename = page_data["image_filename"]
        if not image_filename:
            print(f"SKIP {xml_path.name}: missing imageFilename")
            skipped_pages += 1
            continue

        img_path = xml_path.parent / image_filename
        if not img_path.exists():
            print(f"SKIP {xml_path.name}: missing image {image_filename}")
            skipped_pages += 1
            continue

        try:
            img = Image.open(img_path)
        except Exception as e:
            print(f"SKIP {xml_path.name}: cannot open image: {e}")
            skipped_pages += 1
            continue

        body_lines = select_body_lines(page_data)

        if len(body_lines) < 5:
            print(f"SKIP {xml_path.name}: too few usable body lines ({len(body_lines)})")
            skipped_pages += 1
            continue

        page_line_count = 0

        for line in body_lines:
            x0, y0, x1, y1 = line["x0"], line["y0"], line["x1"], line["y1"]

            pad_x = 2
            pad_y = 2

            x0 = max(0, x0 - pad_x)
            y0 = max(0, y0 - pad_y)
            x1 = min(img.width, x1 + pad_x)
            y1 = min(img.height, y1 + pad_y)

            if x1 <= x0 or y1 <= y0:
                continue

            crop = img.crop((x0, y0, x1, y1))

            stem = f"{line_counter:06d}"
            out_img = out_dir / f"{stem}.png"
            out_txt = out_dir / f"{stem}.gt.txt"

            crop.save(out_img)
            out_txt.write_text(line["text"], encoding="utf-8")

            line_counter += 1
            kept_lines += 1
            page_line_count += 1

        if page_line_count == 0:
            print(f"SKIP {xml_path.name}: no lines extracted")
            skipped_pages += 1
            continue

        print(f"KEEP {xml_path.name}: extracted {page_line_count} body lines")
        kept_pages += 1

    print("\nDone.")
    print(f"Kept pages   : {kept_pages}")
    print(f"Skipped pages: {skipped_pages}")
    print(f"Kept lines   : {kept_lines}")
    print(f"Output dir   : {out_dir}")


if __name__ == "__main__":
    main()