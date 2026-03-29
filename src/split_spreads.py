import os
import cv2
import numpy as np
from pathlib import Path

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    input_dir = base_dir / "data" / "raw_pages"
    
    print(f"Scanning {input_dir} for dual-page spreads...")
    
    image_files = list(input_dir.glob("*.png"))
    processed_count = 0
    
    for img_path in image_files:
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            continue
            
        height, width = img.shape[:2]
        
        # Check if image is a horizontal spread (width > height)
        if width > height:
            print(f"Splitting spread: {img_path.name}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold (invert so text is white, background is black)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # Vertical projection: sum of pixels in each column
            vertical_projection = np.sum(thresh, axis=0)
            
            # Search for the gutter in the middle 20% of the image (40% to 60%)
            search_start = int(width * 0.40)
            search_end = int(width * 0.60)
            
            middle_region = vertical_projection[search_start:search_end]
            
            # Find the index with the minimum text (the gutter)
            local_min_idx = np.argmin(middle_region) 
            
            # Calculate the exact cut coordinate in the original image
            cut_x = search_start + local_min_idx
            
            # Crop the left and right pages
            left_page = img[:, :cut_x]
            right_page = img[:, cut_x:]
            
            # Generate new filenames
            left_name = f"{img_path.stem}_left.png"
            right_name = f"{img_path.stem}_right.png"
            
            # Save the new images
            cv2.imwrite(str(input_dir / left_name), left_page)
            cv2.imwrite(str(input_dir / right_name), right_page)
            
            # Delete the original spread to keep the dataset clean
            img_path.unlink()
            processed_count += 1
            
    print(f"Successfully split {processed_count} dual-page spreads.")

if __name__ == "__main__":
    main()