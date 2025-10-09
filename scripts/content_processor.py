"""Content Processing Utility

A utility script for processing and importing text content into the Educational AI Assistant.
This can be used to batch process content from various sources including web scraping,
text files, or other content sources.
"""

import trafilatura
import os
import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.core.document_processor import DocumentProcessor

def scrape_url_content(url: str, user_id: int, api_keys: dict):
    """
    Scrape content from a URL and store it in the vector database.
    
    Args:
        url (str): The URL to scrape
        user_id (int): The user ID to associate with the content
        api_keys (dict): Dictionary containing user's API keys
    """
    try:
        # Download and extract content from URL
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded)
        
        if not content:
            print(f"Could not extract content from {url}")
            return False
        
        # Initialize document processor with user credentials
        processor = DocumentProcessor(user_id=user_id, api_keys=api_keys)
        
        # Create a temporary file to store the content
        temp_filename = f"scraped_content_{hash(url)}.txt"
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Processing content from {url}...")
        
        # Process and store the content
        with open(temp_filename, "rb") as f:
            result = processor.process_pdf(f)  # This works for text files too
            
        # Clean up
        os.remove(temp_filename)
        
        if result == "stored_in_pinecone":
            print(f"✅ Successfully processed and stored content from {url}")
            return True
        else:
            print(f"❌ Failed to store content from {url}: {result}")
            return False
            
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return False

def process_text_file(file_path: str, user_id: int, api_keys: dict):
    """
    Process a text file and store it in the vector database.
    
    Args:
        file_path (str): Path to the text file
        user_id (int): The user ID to associate with the content
        api_keys (dict): Dictionary containing user's API keys
    """
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
            
        print(f"Processing file: {file_path}")
        
        # Initialize document processor with user credentials
        processor = DocumentProcessor(user_id=user_id, api_keys=api_keys)
        
        # Process the file
        with open(file_path, "rb") as f:
            result = processor.process_pdf(f)
            
        if result == "stored_in_pinecone":
            print(f"✅ Successfully processed and stored {file_path}")
            return True
        else:
            print(f"❌ Failed to store {file_path}: {result}")
            return False
            
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return False

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Content Processing Utility for Educational AI Assistant"
    )
    parser.add_argument("--url", help="URL to scrape and process")
    parser.add_argument("--file", help="Text file to process")
    parser.add_argument("--user-id", type=int, required=True, help="User ID to associate content with")
    parser.add_argument("--openai-key", required=True, help="OpenAI API key")
    parser.add_argument("--pinecone-key", required=True, help="Pinecone API key")
    parser.add_argument("--pinecone-env", help="Pinecone environment (deprecated, no longer needed)")
    
    args = parser.parse_args()
    
    # Prepare API keys dictionary
    api_keys = {
        'openai_key': args.openai_key,
        'pinecone_key': args.pinecone_key,
        'pinecone_environment': args.pinecone_env  # Deprecated but kept for backward compatibility
    }
    
    success = False
    
    if args.url:
        success = scrape_url_content(args.url, args.user_id, api_keys)
    elif args.file:
        success = process_text_file(args.file, args.user_id, api_keys)
    else:
        print("Please provide either --url or --file argument")
        parser.print_help()
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
