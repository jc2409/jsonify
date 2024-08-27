# Zip File Metadata Extractor

This project is a Python script that extracts metadata from files within a zip archive and generates JSON files containing the extracted metadata. It uses Azure OpenAI's language model to analyze and extract relevant information from the file contents.

## Features

- Extracts metadata from various file types within a zip archive
- Generates JSON files for each processed file, containing structured metadata
- Handles zip file contents
- Uses Azure OpenAI's language model for intelligent metadata extraction

## Prerequisites

- Python 3.12
- pipenv

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jc2409/jsonify.git
   cd jsonify
   ```

2. Install dependencies using pipenv:
   ```
   pipenv install
   ```

3. Set up your Azure OpenAI API credentials:
   Create a `.env` file in the project root and add your Azure OpenAI API key and version:
   ```
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_API_VERSION=your_api_version_here
   ```

## Usage

1. Activate the virtual environment:
   ```
   pipenv shell
   ```

2. Place your zip file (named `contents.zip`) in the project root directory.

3. Run the script:
   ```
   python main.py
   ```

4. The script will create a folder named `metadata_json_files` containing JSON files with extracted metadata for each file in the zip archive.

## Customization

- You can modify the `FileMetadata` class in `main.py` to adjust the metadata fields extracted from each file.
- The `extract_text` function can be expanded to handle additional file types for text extraction.