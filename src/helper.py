from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

from typing import List
from langchain.schema import Document


#Extract Data From the PDF File
def load_pdf_file(data):
    loader= DirectoryLoader(data,
                            glob="*.pdf",
                            loader_cls=PyPDFLoader)

    documents=loader.load()

    return documents
  
  
# Get the current file's directory and construct the Data path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(os.path.dirname(current_dir), "Data")
extracted_data = load_pdf_file(data=data_dir)

from typing import List
from langchain.schema import Document

def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects
    containing only 'source' in metadata and the original page_content.
    """
    minimal_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={"source": src}
            )
        )
    return minimal_docs
  
  
minimal_docs = filter_to_minimal_docs(extracted_data)

#Split the Data into Text Chunks
def text_split(minimal_docs):
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    text_chunks=text_splitter.split_documents(minimal_docs)
    return text_chunks
  
text_chunks=text_split(minimal_docs)
print("Length of Text Chunks", len(text_chunks))
from langchain.embeddings import HuggingFaceEmbeddings

#Download the Embeddings from Hugging Face
def download_hugging_face_embeddings():
    embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    return embeddings

embeddings = download_hugging_face_embeddings()