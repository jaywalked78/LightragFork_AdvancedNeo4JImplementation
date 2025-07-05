#!/usr/bin/env python3
"""
Script to extract documents from PostgreSQL tll_lightrag_doc_status table
and save them as markdown files in the inputs folder.
"""

import os
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def get_postgres_connection():
    """Create PostgreSQL connection using environment variables."""
    return await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DATABASE')
    )

async def extract_documents() -> List[Tuple[str, str]]:
    """
    Extract file_path and content from tll_lightrag_doc_status table.
    Returns list of tuples (file_path, content).
    """
    conn = await get_postgres_connection()
    try:
        # Query to get file_path and content from the table
        query = """
        SELECT file_path, content 
        FROM public.tll_lightrag_doc_status 
        WHERE file_path IS NOT NULL AND content IS NOT NULL
        """
        
        rows = await conn.fetch(query)
        documents = [(row['file_path'], row['content']) for row in rows]
        
        print(f"Found {len(documents)} documents in the database")
        return documents
        
    finally:
        await conn.close()

async def save_documents_to_inputs(documents: List[Tuple[str, str]]):
    """
    Save documents to the inputs folder as markdown files.
    
    Args:
        documents: List of tuples (file_path, content)
    """
    # Get the inputs directory path
    script_dir = Path(__file__).parent.parent
    inputs_dir = script_dir / "inputs"
    
    # Create inputs directory if it doesn't exist
    inputs_dir.mkdir(exist_ok=True)
    
    saved_count = 0
    
    for file_path, content in documents:
        # Remove quotes if present
        file_path = file_path.strip('"\'')
        
        # Add .md extension if not already present
        if not file_path.endswith('.md'):
            file_path = f"{file_path}.md"
        
        # Create full path
        output_path = inputs_dir / file_path
        
        try:
            # Write content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            saved_count += 1
            print(f"Saved: {file_path}")
            
        except Exception as e:
            print(f"Error saving {file_path}: {str(e)}")
    
    print(f"\nSuccessfully saved {saved_count} documents to {inputs_dir}")

async def main():
    """Main function to orchestrate the extraction and saving process."""
    print("Starting document extraction from PostgreSQL...")
    
    try:
        # Extract documents from database
        documents = await extract_documents()
        
        if documents:
            # Save documents to inputs folder
            await save_documents_to_inputs(documents)
        else:
            print("No documents found in the database.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure your .env file contains the following PostgreSQL credentials:")
        print("POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DATABASE")

if __name__ == "__main__":
    asyncio.run(main())