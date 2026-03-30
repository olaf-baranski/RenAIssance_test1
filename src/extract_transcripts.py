import os
from pathlib import Path
import docx

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    transcripts_dir = base_dir / "data" / "original_transcripts"
    
    print(f"Scanning {transcripts_dir} for .docx files")
    
    docx_files = list(transcripts_dir.glob("*.docx"))
    
    if not docx_files:
        print("No .docx files found.")
        return
        
    for doc_path in docx_files:
        print(f"Processing: {doc_path.name}")
        try:
            doc = docx.Document(doc_path)
            full_text = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    full_text.append(text)
                    
            output_name = f"{doc_path.stem}_clean.txt"
            output_path = transcripts_dir / output_name
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(full_text))
                
            print(f"Saved clean text to: {output_name}")
            
        except Exception as e:
            print(f"Error processing {doc_path.name}: {e}")

    print("All transcripts converted successfully.")

if __name__ == "__main__":
    main()