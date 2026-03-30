import os
import subprocess
from pathlib import Path
from lxml import etree

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    raw_pages_dir = base_dir / "data" / "raw_pages"
    
    txt_files = list(raw_pages_dir.glob("*.txt"))
    
    if not txt_files:
        print("No .txt transcript files found.")
        return

    print("Cleaning up old ALTO XML files to prevent conflicts...")
    for old_xml in raw_pages_dir.glob("*.xml"):
        old_xml.unlink()

    print(f"Found {len(txt_files)} pages. Starting PAGE XML pipeline...")
    
    for txt_path in txt_files:
        png_path = txt_path.with_suffix(".png")
        xml_path = txt_path.with_suffix(".xml")
        
        if not png_path.exists():
            continue

        print(f"-> Processing: {png_path.name}")
        
        # STEP 1: Vision (Kraken Pipeline with -x for PAGE XML format)
        cmd = f'kraken -x -i "{png_path}" "{xml_path}" binarize segment'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        
        if result.returncode != 0 or not xml_path.exists():
            print(f"   [ERROR] Kraken failed for {png_path.name}.")
            continue
            
        # STEP 2: Data Injection (PAGE XML structure)
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                gt_lines = [line.strip() for line in f if line.strip()]
                
            tree = etree.parse(str(xml_path))
            # Find all TextLine elements (ignoring namespaces)
            xml_lines = tree.xpath('//*[local-name()="TextLine"]')
            
            if len(xml_lines) != len(gt_lines):
                print(f"   [WARNING] Line mismatch: Found {len(xml_lines)} boxes for {len(gt_lines)} text lines.")
            
            # Inject text by creating TextEquiv and Unicode child elements
            for xml_line, gt_line in zip(xml_lines, gt_lines):
                # Retrieve the default namespace dynamically
                ns = xml_line.nsmap.get(None, "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15")
                
                # Build the text node structure required by PAGE XML
                text_equiv = etree.SubElement(xml_line, f"{{{ns}}}TextEquiv")
                unicode_el = etree.SubElement(text_equiv, f"{{{ns}}}Unicode")
                unicode_el.text = gt_line

            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
            print(f"   [SUCCESS] PAGE XML generated and mapped successfully.")
            
        except Exception as e:
            print(f"   [ERROR] Failed to inject text for {png_path.name}: {e}")

    print("\nProcess finished. Your PAGE XML dataset is ready for training.")

if __name__ == "__main__":
    main()