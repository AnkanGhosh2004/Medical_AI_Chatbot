from dotenv import load_dotenv
import os
from src.helper import load_pdf_file, filter_to_minimal_docs, text_split, download_hugging_face_embeddings
from pinecone import Pinecone
from pinecone import ServerlessSpec 
from langchain_pinecone import PineconeVectorStore


load_dotenv()



PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY



extracted_data = load_pdf_file(r"C:\Users\hp\Desktop\PROJECT\Medical_AI_Chatbot\Data")
filter_data = filter_to_minimal_docs(extracted_data)
text_chunks=text_split(filter_data)

embeddings = download_hugging_face_embeddings()



api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)





index_name = "medical-bot"  # change if desired

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)



docsearch = PineconeVectorStore.from_documents(
    documents=text_chunks,
    index_name=index_name,
    embedding=embeddings,
)
