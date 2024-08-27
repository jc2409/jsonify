import os
import zipfile
import json
from dotenv import load_dotenv
from langchain.prompts.prompt import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from langchain_core.prompts import PromptTemplate
import magic
import mimetypes

load_dotenv()

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

class FileMetadata(BaseModel):
    title: str = Field(description="The name given to the resource by the creator or publisher")
    creator: str = Field(description="The person or organization primarily responsible for the intellectual content of the resource")
    subject: str = Field(description="The topic of the resource")
    description: str = Field(description="A textual description of the content of the resource")
    publisher: str = Field(description="The entity responsible for making the resource available")
    contributor: str = Field(description="A person or organization (other than the Creator) who is responsible for making significant contributions to the intellectual content of the resource")
    date: str = Field(description="A date associated with the creation or availability of the resource")
    type: str = Field(description="The nature or genre of the content of the resource")
    format: str = Field(description="The physical or digital manifestation of the resource")
    identifier: str = Field(description="An unambiguous reference that uniquely identifies the resource within a given context")
    source: str = Field(description="A reference to a second resource from which the present resource is derived")
    language: str = Field(description="The language of the intellectual content of the resource")
    relation: str = Field(description="A reference to a related resource, and the nature of its relationship")
    keywords: List[str] = Field(description="Keywords used")

parser = JsonOutputParser(pydantic_object=FileMetadata)

prompt = PromptTemplate(
    template="Extract metadata and keywords from the following file information:\n{format_instructions}\n{context}\n",
    input_variables=["context"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

def extract_text(file_path, mime_type):
    if mime_type.startswith('text/'):
        with open(file_path, 'r', errors='ignore') as f:
            return f.read(1000)  # Read first 1000 characters
    elif mime_type == 'application/pdf':
        # Use PyPDF2 or a similar library to extract text from PDF
        pass
    return "Text extraction not supported for this file type"

def process_zip_file(zip_path, output_folder):
    results = []
    os.makedirs(output_folder, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall('temp_extracted')
        for filename in zip_ref.namelist():
            # Skip __MACOSX directory and hidden files
            if filename.startswith('__MACOSX') or '/.' in filename:
                continue
            
            file_path = os.path.join('temp_extracted', filename)
            if os.path.isfile(file_path):
                file_info = zip_ref.getinfo(filename)
                mime_type = magic.from_file(file_path, mime=True)

                context = {
                    "filename": filename,
                    "file_type": mimetypes.guess_extension(mime_type) or "Unknown",
                    "file_size": file_info.file_size,
                    "mime_type": mime_type,
                    "creation_date": "Not available in zip file",
                    "modification_date": str(file_info.date_time),
                    "extracted_text": extract_text(file_path, mime_type)
                }

                response = chain.invoke({"context": context})
                results.append(response)
                
                # Create subdirectories if necessary
                json_filename = os.path.splitext(filename)[0] + '.json'
                json_path = os.path.join(output_folder, json_filename)
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                
                with open(json_path, 'w') as json_file:
                    json.dump(response, json_file, indent=2)

    # Clean up
    for root, dirs, files in os.walk('temp_extracted', topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir('temp_extracted')

    return results

chain = prompt | llm | parser

# Usage
zip_file_path = "contents.zip"
output_folder = "metadata_json_files"
metadata_results = process_zip_file(zip_file_path, output_folder)

print(f"Metadata JSON files have been created in the '{output_folder}' directory.")