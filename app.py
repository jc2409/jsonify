import os
import zipfile
import json
import shutil
from dotenv import load_dotenv
from langchain.prompts.prompt import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Literal
from langchain_core.prompts import PromptTemplate
import magic
import mimetypes
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

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
    temp_dir = 'temp_extracted'

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue

                # Normalize the filename to use OS-specific path separator
                filename = os.path.normpath(file_info.filename)

                # Skip hidden files and directories (including __MACOSX)
                if any(part.startswith('.') for part in filename.split(os.sep)):
                    continue

                # Extract the file
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

                    # Create subdirectories if necessary
                    json_filename = os.path.splitext(filename)[0] + '.json'
                    json_path = os.path.join(output_folder, json_filename)
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)

                    with open(json_path, 'w') as json_file:
                        json.dump(response, json_file, indent=2)

                # Clean up extracted file
                os.remove(file_path)

    finally:
        # Clean up temp directory
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
            metadata_results = process_zip_file(temp_zip_path, output_folder)
            return jsonify({
                "message": f"Processed {len(metadata_results)} files",
                "results": metadata_results
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            os.remove(temp_zip_path)
    else:
        return jsonify({"error": "Invalid file type. Please upload a ZIP file."}), 400

if __name__ == '__main__':
    app.run(debug=True)