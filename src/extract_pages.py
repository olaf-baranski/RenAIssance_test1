import os
from pathlib import Path
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

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
    
    BATCH_SIZE = 10
    
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        
        try:
            info = pdfinfo_from_path(pdf_path)
            total_pages = info["Pages"]
            print(f"  Total pages to process: {total_pages}")
            
            expected_last_page = output_dir / f"{pdf_path.stem}_page_{total_pages:03d}.png"
            if expected_last_page.exists():
                print(f"Skipping {pdf_path.name} - already fully processed.")
                continue
            
            for start_page in range(1, total_pages + 1, BATCH_SIZE):
                end_page = min(start_page + BATCH_SIZE - 1, total_pages)
                print(f"  Extracting pages {start_page} to {end_page}...")
                
                images = convert_from_path(
                    pdf_path, 
                    dpi=300, 
                    first_page=start_page, 
                    last_page=end_page,
                    use_cropbox=True
                )
                
                for i, image in enumerate(images):
                    actual_page_num = start_page + i
                    image_name = f"{pdf_path.stem}_page_{actual_page_num:03d}.png"
                    image_path = output_dir / image_name
                    image.save(image_path, "PNG")
                    
            print(f"  Successfully processed all {total_pages} pages from {pdf_path.name}")
            
        except Exception as e:
            print(f"Error processing {pdf_path.name}.")
            print(f"Error details: {e}")

    print("Successfully extracted all pages")

if __name__ == "__main__":
    main()