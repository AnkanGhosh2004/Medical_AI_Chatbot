from flask import Flask, render_template, request
from src.helper import embeddings, text_chunks
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain_together import ChatTogether
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import system_prompt
import os

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
TOGETHER_API_KEY = os.environ.get('TOGETHER_API_KEY')

# Check if required environment variables are set
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is not set. Please create a .env file with your API keys.")
if not TOGETHER_API_KEY:
    raise ValueError("TOGETHER_API_KEY is not set. Please create a .env file with your API keys.")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY

index_name = "medical-bot"

# Initialize Pinecone vector store (assumes you have already upserted your text_chunks)
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 5})


# Custom system prompt to instruct the model to be concise and focus on main points
concise_system_prompt = system_prompt + "\n\nPlease answer as concisely as possible, focusing only on the main essential points. Limit your response to 3-5 sentences."

chatModel = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="meta-llama/Llama-3-8b-chat-hf",
    temperature=0.1,
    max_tokens=300,  # Reduce max tokens for shorter answers
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", concise_system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/test")
def test():
    return "Flask is working!"

# --- Simple intent detection (stub functions, you can expand) ---
def is_greeting(message):
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    return any(greet in message.lower() for greet in greetings)

def is_farewell(message):
    farewells = ["bye", "goodbye", "see you", "take care"]
    return any(farewell in message.lower() for farewell in farewells)

def is_small_talk(message):
    small_talks = ["how are you", "what's up", "how's it going"]
    return any(st in message.lower() for st in small_talks)

def get_greeting_response():
    return "Hello! How can I assist you with your health today?"

def get_farewell_response():
    return "Goodbye! Stay healthy and feel free to return if you have more questions."

def get_small_talk_response(message):
    return "I'm here to help you with your health-related questions!"

@app.route("/get", methods=["POST"])
def chat():
    msg = request.form["msg"]
    input_text = msg.strip()
    print("User input:", input_text)

    # Intent handling
    if is_small_talk(input_text):
        return get_small_talk_response(input_text)
    if is_farewell(input_text):
        return get_farewell_response()
    if is_greeting(input_text):
        return get_greeting_response()

    # Medical Q&A via RAG
    try:
        response = rag_chain.invoke({"input": input_text})
        # Handle different possible response formats
        if isinstance(response, dict):
            if "answer" in response:
                return response["answer"]
            elif "output" in response:
                return response["output"]
        return str(response)
    except Exception as e:
        import traceback
        print("Error in RAG chain:", e)
        traceback.print_exc()
        return "Sorry, I couldn't process your request at the moment. Please try again later."


    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)