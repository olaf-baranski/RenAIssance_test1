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

    print(f"Found {len(txt_files)} pages. Starting pipeline: Binarize -> Segment -> Inject")
    
    for txt_path in txt_files:
        png_path = txt_path.with_suffix(".png")
        xml_path = txt_path.with_suffix(".xml")
        
        if not png_path.exists():
            print(f"WARNING Missing image for: {txt_path.name}")
            continue

        print(f"-> Processing: {png_path.name}")
        
        cmd = f'kraken -a -i "{png_path}" "{xml_path}" binarize segment'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        
        if result.returncode != 0 or not xml_path.exists():
            print(f"   [ERROR] Kraken pipeline failed for {png_path.name}.")
            print(f"   Kraken Error Log: {result.stderr.decode('utf-8').strip()}")
            continue
            
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                gt_lines = [line.strip() for line in f if line.strip()]
                
            tree = etree.parse(str(xml_path))
            xml_lines = tree.xpath('//*[local-name()="TextLine"]')
            
            if len(xml_lines) != len(gt_lines):
                print(f"WARNING Line mismatch in {png_path.name} | Found {len(xml_lines)} boxes for {len(gt_lines)} text lines.")
            
            for xml_line, gt_line in zip(xml_lines, gt_lines):
                string_element = xml_line.xpath('./*[local-name()="String"]')
                if string_element:
                    string_element[0].set("CONTENT", gt_line)

            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
            print(f"SUCCESS XML generated and mapped successfully.")
            
        except Exception as e:
            print(f"ERROR Failed to inject text for {png_path.name}: {e}")

    print("\nProcess finished. Your dataset is ready.")

if __name__ == "__main__":
    main()