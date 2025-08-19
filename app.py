from flask import Flask, render_template, jsonify, request
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain_together import ChatTogether
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os
import random
import re

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
TOGETHER_API_KEY=os.environ.get('TOGETHER_API_KEY')

# Check if required environment variables are set
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is not set. Please create a .env file with your API keys.")
if not TOGETHER_API_KEY:
    raise ValueError("TOGETHER_API_KEY is not set. Please create a .env file with your API keys.")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY

embeddings = download_hugging_face_embeddings()

index_name = "medical-bot" 
# Embed each chunk and upsert the embeddings into your Pinecone index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)


retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})



chatModel = ChatTogether(
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    model="meta-llama/Llama-3-8b-chat-hf", 
)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


@app.route("/")
def index():
    return render_template('chat.html')


def is_greeting(message):
    """Check if the message is a greeting"""
    greetings = [
        'hello', 'hi', 'hey', 'hii', 'hiii', 'hiiii',
        'good morning', 'good afternoon', 'good evening', 
        'morning', 'afternoon', 'evening',
        'hola', 'namaste', 'salaam', 'greetings',
        'howdy', 'yo', 'sup', "what's up", "whats up"
    ]
    message_lower = message.lower().strip()
    return any(greeting in message_lower for greeting in greetings) or len(message_lower) <= 10

def is_farewell(message):
    """Check if the message is a farewell"""
    farewells = [
        'bye', 'goodbye', 'good bye', 'see you', 'see ya', 'cya',
        'thanks', 'thank you', 'thank u', 'ty', 'thx',
        "that's all", "that's it", 'exit', 'quit', 'end',
        'take care', 'farewell', 'adios', 'hasta la vista',
        'have a good day', 'have a nice day', 'ttyl', 'gotta go',
        'see you later'
    ]
    message_lower = message.lower().strip()
    return any(farewell in message_lower for farewell in farewells)

def is_small_talk(message):
    """Check if the message is small talk"""
    message_lower = message.lower().strip()
    small_talk_patterns = [
        'how are you', 'how r u', 'how do you do',
        'what is your name', 'whats your name', "what's your name",
        'are you a bot', 'are you ai', 'are you artificial intelligence',
        'who are you', 'what are you'
    ]
    return any(pattern in message_lower for pattern in small_talk_patterns)

def get_time_based_greeting():
    """Get time-appropriate greeting"""
    import datetime
    current_hour = datetime.datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 17:
        return "Good afternoon"
    elif 17 <= current_hour < 21:
        return "Good evening"
    else:
        return "Hello"

def get_greeting_response():
    """Return a random friendly greeting response"""
    greeting_responses = [
        "Hello! 👋 How can I help you today?",
        "Hi there! 😊 What's on your mind?",
        "Hey! I'm here to assist you. What would you like to know?",
        f"{get_time_based_greeting()}! How can I support you today?",
        "Welcome! Ready to get your health questions answered? 🏥"
    ]
    return random.choice(greeting_responses)

def get_farewell_response():
    """Return a random friendly farewell response"""
    farewell_responses = [
        "You're welcome! Have a great day ahead 🌸",
        "Glad I could help! Goodbye 👋",
        "Take care and feel free to come back anytime 🚀",
        "It was nice chatting with you. See you soon! 😊",
        "Thanks for chatting! Wishing you all the best 🌟"
    ]
    return random.choice(farewell_responses)

def get_small_talk_response(message):
    """Handle small talk conversations"""
    message_lower = message.lower().strip()
    
    if any(phrase in message_lower for phrase in ['how are you', 'how r u', 'how do you do']):
        return "I'm doing great, thanks for asking! How about you? 😊 Is there anything health-related I can help you with?"
    
    elif any(phrase in message_lower for phrase in ['what is your name', 'whats your name', "what's your name"]):
        return "I'm your AI Medical Assistant 🤖, here to help you with health and medical questions!"
    
    elif any(phrase in message_lower for phrase in ['are you a bot', 'are you ai', 'are you artificial intelligence']):
        return "Yes, I'm an AI chatbot built to assist you with medical information and health questions! 🤖💙"
    
    elif any(phrase in message_lower for phrase in ['who are you', 'what are you']):
        return "I'm your friendly AI Medical Assistant! 🏥 I'm here to provide health information and answer your medical questions. How can I help you today?"
    
    return None

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    print(input)
    
    # Check for small talk first
    if is_small_talk(msg):
        small_talk_response = get_small_talk_response(msg)
        if small_talk_response:
            return small_talk_response

    # Check for farewells next
    if is_farewell(msg):
        return get_farewell_response()

    # Check for greetings
    if is_greeting(msg):
        return get_greeting_response()

    # Process medical queries
    response = rag_chain.invoke({"input": msg})
    print("Response : ", response["answer"])
    return str(response["answer"])



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)