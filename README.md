# Zip File Metadata Extractor

This project is a Python application that extracts metadata from files within a zip archive and generates JSON files containing the extracted metadata. It uses Azure OpenAI's language model to analyze and extract relevant information from the file contents.

## Features

- Extracts metadata from various file types within a zip archive
- Generates JSON files for each processed file, containing structured metadata
- Handles zip file contents efficiently
- Uses Azure OpenAI's language model for intelligent metadata extraction
- Provides two user interface options:
  1. Custom HTML UI (app.py)
  2. Streamlit-based UI (test.py)

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

2. Choose your preferred UI option:

   ### Option 1: Custom HTML UI (app.py)
   
   Run the Flask application:
   ```
   python app.py
   ```
   Access the application by navigating to `http://localhost:5000` in your web browser.

   ### Option 2: Streamlit UI (test.py)
   
   Run the Streamlit application:
   ```
   streamlit run test.py
   ```
   Your default web browser should open automatically to the Streamlit app. If not, access it at the URL provided in the terminal.

3. Upload a zip file through the web interface.

4. Process the zip file and view the extracted metadata.

5. Download the generated JSON files containing the metadata.

## Customization

- You can modify the `FileMetadata` class in the Python scripts to adjust the metadata fields extracted from each file.
- The `extract_text` function can be expanded to handle additional file types for text extraction.
- To customize the Custom HTML UI, edit the HTML templates in the `templates` folder and update `app.py` accordingly.
- For Streamlit UI modifications, edit `test.py` directly.