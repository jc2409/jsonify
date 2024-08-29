import streamlit as st
import time
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
import magic
import mimetypes
import tempfile

load_dotenv()

# Define controlled vocabularies
SubjectASPVocab = Literal[
    "Primary computing education",
    "Primary STEM education",
    "Elementary school computing education",
    "Elementary school STEM education",
    "Middle school computing education",
    "Middle school STEM education",
    "Secondary computing education",
    "Secondary STEM education",
    "High school computing education",
    "High school STEM education",
    "K-12 computing education",
    "K12/K-12 STEM education",
    "Computer Science",
    "Python",
    "MicroPython",
    "Computer Engineering",
    "Robotics",
    "Internet of Things (IoT)",
    "Machine learning (ML)",
    "Artificial intelligence (AI)",
    "Teach with physical computing",
    "micro:bit",
    "micro:bit v1",
    "micro:bit v2",
    "Raspberry Pi",
    "Raspberry Pi Pico",
    "Arduino",
    "Computing",
    "Coding",
    "Data Science",
]

SubjectAUPVocab = Literal[
    "Computer Science",
    "Computer Engineering",
    "Electrical Engineering",
    "Robotics",
    "Internet of Things (IoT)",
    "Machine learning (ML)",
    "Artificial intelligence (AI)",
    "Embedded Systems",
    "Real Time Operating Systems (RTOS)",
    "Mobile Computing",
    "Cloud Computing",
    "Edge Computing",
    "SW Design & Development",
    "Digital System",
    "Digital Signal Processing",
    "System-on-Chip Design",
    "Computer Architecture",
    "VLSI",
    "Operating Systems",
    "Linux",
    "MVE / Helium",
    "Computing",
]

TypeVocab = Literal[
    "EdKit", "Lecture", "Lab", "Video", "Animation", "Course", "Resource"
]

FormatVocab = Literal["ppt", "doc", "zip", "mp3", "pdf"]


class FileMetadata(BaseModel):
    title: str = Field(
        description="The name given to the resource by the creator or publisher"
    )
    creator: str = Field(
        description="The person or organization primarily responsible for the intellectual content of the resource"
    )
    subject_asp: List[SubjectASPVocab] = Field(
        description="The Arm School Program subject of the resource"
    )
    subject_aup: List[SubjectAUPVocab] = Field(
        description="The Arm University Program subject of the resource"
    )
    description: str = Field(
        description="A textual description of the content of the resource"
    )
    publisher: str = Field(
        description="The entity responsible for making the resource available"
    )
    contributor: str = Field(
        description="A person or organization (other than the Creator) who is responsible for making significant contributions to the intellectual content of the resource"
    )
    date: str = Field(
        description="A date associated with the creation or availability of the resource"
    )
    type: List[TypeVocab] = Field(
        description="The nature or genre of the content of the resource"
    )
    format: List[FormatVocab] = Field(
        description="The physical or digital manifestation of the resource"
    )
    identifier: str = Field(
        description="An unambiguous reference that uniquely identifies the resource within a given context"
    )
    source: str = Field(
        description="A reference to a second resource from which the present resource is derived"
    )
    language: str = Field(
        description="The language of the intellectual content of the resource"
    )
    relation: str = Field(
        description="A reference to a related resource, and the nature of its relationship"
    )
    keywords: List[str] = Field(description="Keywords used")


llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
)

parser = JsonOutputParser(pydantic_object=FileMetadata)

prompt = PromptTemplate(
    template="Extract metadata and keywords from the following file information:\n{format_instructions}\n{context}\n",
    input_variables=["context"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

chain = prompt | llm | parser


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


def process_zip_file(zip_file):
    results = []
    temp_dir = tempfile.mkdtemp()
    output_folder = tempfile.mkdtemp()

    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            total_files = sum(1 for _ in zip_ref.infolist() if not _.is_dir())

            for i, (root, _, files) in enumerate(os.walk(temp_dir)):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, temp_dir)

                    try:
                        mime_type = magic.from_file(file_path, mime=True)
                    except magic.MagicException:
                        mime_type = "application/octet-stream"

                    context = {
                        "filename": relative_path,
                        "file_type": mimetypes.guess_extension(mime_type) or "Unknown",
                        "file_size": os.path.getsize(file_path),
                        "mime_type": mime_type,
                        "creation_date": "Not available",
                        "modification_date": str(os.path.getmtime(file_path)),
                        "extracted_text": extract_text(file_path, mime_type),
                    }

                    response = chain.invoke({"context": context})
                    results.append(response)

                    json_filename = os.path.splitext(relative_path)[0] + ".json"
                    json_path = os.path.join(output_folder, json_filename)
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)

                    with open(json_path, "w") as json_file:
                        json.dump(response, json_file, indent=2)

    finally:
        shutil.rmtree(temp_dir)

    return results, output_folder


def main():
    st.title("ZIP File Metadata Extractor")

    uploaded_file = st.file_uploader("Choose a ZIP file", type="zip")

    if uploaded_file is not None:
        if st.button("Process ZIP File"):
            with st.spinner("Processing ZIP file..."):
                results, output_folder = process_zip_file(uploaded_file)

            st.success(f"Metadata is created successfully in JSON format!")

            # Offer the ZIP file for download
            with open(zip_path, "rb") as file:
                st.download_button(
                    label="Download JSON Files",
                    data=file,
                    file_name="metadata_results.zip",
                    mime="application/zip",
                )

            # Display the first 3 examples of JSON files
            st.subheader("First 3 Examples of Generated JSON Files:")
            for i, result in enumerate(results[:3]):
                st.json(result)
                if i < 2:  # Add a separator between examples, except after the last one
                    st.markdown("---")

            # Create a ZIP file of the results
            zip_path = "metadata_results.zip"
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for root, _, files in os.walk(output_folder):
                    for file in files:
                        zipf.write(
                            os.path.join(root, file),
                            os.path.relpath(os.path.join(root, file), output_folder),
                        )

            # Clean up
            os.remove(zip_path)
            shutil.rmtree(output_folder)


if __name__ == "__main__":
    main()
