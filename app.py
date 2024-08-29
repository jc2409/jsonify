import os
import zipfile
import json
import shutil
from dotenv import load_dotenv
from langchain.prompts.prompt import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.document_loaders import PyPDFLoader
from typing import List, Literal
from langchain_core.prompts import PromptTemplate
import magic
import mimetypes
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import threading

load_dotenv()

app = Flask(__name__)

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    temperature=0
)

# Define controlled vocabularies
SubjectASPVocab = Literal[
    "Primary computing education", "Primary STEM education",
    "Elementary school computing education", "Elementary school STEM education",
    "Middle school computing education", "Middle school STEM education",
    "Secondary computing education", "Secondary STEM education",
    "High school computing education", "High school STEM education",
    "K-12 computing education", "K12/K-12 STEM education",
    "Computer Science", "Python", "MicroPython", "Computer Engineering",
    "Robotics", "Internet of Things (IoT)", "Machine learning (ML)",
    "Artificial intelligence (AI)", "Teach with physical computing",
    "micro:bit", "micro:bit v1", "micro:bit v2",
    "Raspberry Pi", "Raspberry Pi Pico", "Arduino",
    "Computing", "Coding", "Data Science"
]

SubjectAUPVocab = Literal[
    "Computer Science", "Computer Engineering", "Electrical Engineering",
    "Robotics", "Internet of Things (IoT)", "Machine learning (ML)",
    "Artificial intelligence (AI)", "Embedded Systems",
    "Real Time Operating Systems (RTOS)", "Mobile Computing",
    "Cloud Computing", "Edge Computing", "SW Design & Development",
    "Digital System", "Digital Signal Processing", "System-on-Chip Design",
    "Computer Architecture", "VLSI", "Operating Systems", "Linux",
    "MVE / Helium", "Computing"
]

TypeVocab = Literal[
    "EdKit", "Lecture", "Lab", "Video", "Animation", "Course", "Resource"
]

FormatVocab = Literal["ppt", "doc", "zip", "mp3", "pdf"]

class FileMetadata(BaseModel):
    title: str = Field(description="The name given to the resource by the creator or publisher")
    creator: str = Field(description="The person or organization primarily responsible for the intellectual content of the resource")
    subject_asp: List[SubjectASPVocab] = Field(description="The Arm School Program subject of the resource")
    subject_aup: List[SubjectAUPVocab] = Field(description="The Arm University Program subject of the resource")
    description: str = Field(description="A textual description of the content of the resource")
    publisher: str = Field(description="The entity responsible for making the resource available")
    contributor: str = Field(description="A person or organization (other than the Creator) who is responsible for making significant contributions to the intellectual content of the resource")
    date: str = Field(description="A date associated with the creation or availability of the resource")
    type: List[TypeVocab] = Field(description="The nature or genre of the content of the resource")
    format: List[FormatVocab] = Field(description="The physical or digital manifestation of the resource")
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

def clean_metadata_folder(output_folder):
    folder = output_folder
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def extract_text(file_path, mime_type):
    if mime_type.startswith("text/"):
        with open(file_path, "r", errors="ignore") as f:
            return f.read()  # Read first 1000 characters
    elif mime_type == "application/pdf":
        from langchain.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        pages = loader.load()

        # Concatenate text from all pages and limit to first 1000 characters
        full_text = " ".join(page.page_content for page in pages)
        return full_text

    return "Text extraction not supported for this file type"

def process_zip_file(zip_path, output_folder):

    results = []
    clean_metadata_folder(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    temp_dir = 'temp_extracted'

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:

            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue

                filename = os.path.normpath(file_info.filename)

                if any(part.startswith('.') for part in filename.split(os.sep)):
                    continue

                zip_ref.extract(file_info, temp_dir)
                file_path = os.path.join(temp_dir, filename)

                if os.path.isfile(file_path):
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

                    json_filename = os.path.splitext(filename)[0] + '.json'
                    json_path = os.path.join(output_folder, json_filename)
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)

                    with open(json_path, 'w') as json_file:
                        json.dump(response, json_file, indent=2)

                os.remove(file_path)

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    return results

chain = prompt | llm | parser

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'zipFile' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['zipFile']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.zip'):
        filename = secure_filename(file.filename)
        temp_zip_path = os.path.join('temp_uploads', filename)
        os.makedirs('temp_uploads', exist_ok=True)
        file.save(temp_zip_path)
        
        output_folder = "metadata_json_files"
        
        try:
            results = process_zip_file(temp_zip_path, output_folder)
            return jsonify({
                "message": f"Processed {len(results)} files",
                "results": results
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            os.remove(temp_zip_path)
    else:
        return jsonify({"error": "Invalid file type. Please upload a ZIP file."}), 400

@app.route('/download')
def download_files():
    output_folder = "metadata_json_files"
    if not os.path.exists(output_folder) or not os.listdir(output_folder):
        return jsonify({"error": "No JSON files available for download"}), 404
    
    zip_path = "metadata_results.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(output_folder):
            for file in files:
                zipf.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), output_folder))
    
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)