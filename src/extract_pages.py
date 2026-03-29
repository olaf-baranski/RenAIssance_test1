import os
from pathlib import Path
import fitz  

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    
    input_dir = base_dir / "data" / "original_pdfs"
    output_dir = base_dir / "data" / "raw_pages"
    
    print(f"Looking for PDFs in: {input_dir}")
    print(f"Output directory for images: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in directory: {input_dir}")
        return
        
    print(f"Found {len(pdf_files)} PDF(s). Starting conversion")
    
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}.")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            print(f"  Total pages to process: {total_pages}")
            
            expected_last_page = output_dir / f"{pdf_path.stem}_page_{total_pages:03d}.png"
            if expected_last_page.exists():
                print(f"  Skipping {pdf_path.name} - already fully processed.")
                doc.close()
                continue
            
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                
                pix = page.get_pixmap(dpi=300)
                
                actual_page_num = page_num + 1
                image_name = f"{pdf_path.stem}_page_{actual_page_num:03d}.png"
                image_path = output_dir / image_name
                
                pix.save(str(image_path))
                
            print(f"Successfully processed all {total_pages} pages from {pdf_path.name}")
            doc.close()
            
        except Exception as e:
            print(f"Error processing {pdf_path.name}.")
            print(f"Error details: {e}")

    print("Successfully extracted all pages")

if __name__ == "__main__":
    main()