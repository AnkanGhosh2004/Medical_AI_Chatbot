import random
import datetime
import re
from flask import Flask, render_template, request, jsonify
from src.helper import embeddings, text_chunks
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
import google.generativeai as genai
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import system_prompt
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Check if required environment variables are set
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is not set. Please create a .env file with your API keys.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Please create a .env file with your API keys.")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

index_name = "medical-bot"

# Initialize Pinecone vector store
try:
    docsearch = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=embeddings 
    )
    retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    logger.info("Pinecone vector store initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Pinecone: {e}")
    raise

# Enhanced system prompt with medical disclaimers
enhanced_system_prompt = system_prompt + """

IMPORTANT GUIDELINES:
- Provide helpful medical information while being clear about limitations
- Always include appropriate disclaimers for serious conditions
- Suggest consulting healthcare professionals when necessary
- Be empathetic and supportive in your responses
- Keep responses concise (3-5 sentences) but comprehensive
- If asked about emergency symptoms, prioritize safety

MEDICAL DISCLAIMER: This information is for educational purposes only and should not replace professional medical advice, diagnosis, or treatment.
"""

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
logger.info("Available Gemini models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        logger.info(f"Model: {m.name}")

gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")

def chat_gemini_func(messages):
    """Enhanced Gemini chat function with better error handling"""
    try:
        # Extract user input from messages
        if isinstance(messages, dict) and "input" in messages:
            user_input = messages["input"]
        elif isinstance(messages, list) and len(messages) > 0:
            user_input = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        else:
            user_input = str(messages)
        
        response = gemini_model.generate_content(
            user_input,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 400,
                "top_p": 0.8,
                "top_k": 40
            }
        )
        
        return response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again or consult a healthcare professional for urgent matters."

# Create prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", enhanced_system_prompt),
    ("human", "{input}"),
])

# Create chains
question_answer_chain = create_stuff_documents_chain(chat_gemini_func, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/test")
def test():
    return jsonify({"status": "Flask medical bot is working!", "timestamp": datetime.datetime.now().isoformat()})

# --- Enhanced Intent Detection ---
def is_greeting(message):
    """Enhanced greeting detection with more patterns"""
    greeting_patterns = [
        r'\b(hi|hello|hey|hiya|howdy)\b',
        r'\b(good\s+(morning|afternoon|evening|day))\b',
        r'\b(greetings|salutations)\b',
        r'^\s*(hi|hello|hey)[\s!.]*$'
    ]
    msg = message.lower().strip()
    return any(re.search(pattern, msg) for pattern in greeting_patterns)

def is_farewell(message):
    """Enhanced farewell detection"""
    farewell_patterns = [
        r'\b(bye|goodbye|see\s+you|farewell|take\s+care|later)\b',
        r'\b(thanks?\s+(and\s+)?bye|bye\s+thanks?)\b',
        r'\b(have\s+a\s+(good|great|nice)\s+(day|evening|night))\b'
    ]
    msg = message.lower().strip()
    return any(re.search(pattern, msg) for pattern in farewell_patterns)

def is_small_talk(message):
    """Enhanced small talk detection"""
    small_talk_patterns = [
        r'\b(how\s+are\s+you|how\s+you\s+doing|what\'?s\s+up)\b',
        r'\b(how\'?s\s+it\s+going|how\'?s\s+everything)\b',
        r'\b(nice\s+to\s+meet\s+you|pleased\s+to\s+meet)\b',
        r'\b(thank\s*you|thanks|no\s+thank\s*you|no\s+thanks|nope|nah)\b',
        r'\b(ok|okay|alright|fine|cool)\b'
    ]
    msg = message.lower().strip()
    return any(re.search(pattern, msg) for pattern in small_talk_patterns)

def is_emergency_keywords(message):
    """Detect emergency-related keywords"""
    emergency_patterns = [
        r'\b(emergency|urgent|critical|severe\s+pain)\b',
        r'\b(can\'?t\s+breathe|difficulty\s+breathing|chest\s+pain)\b',
        r'\b(heart\s+attack|stroke|seizure|overdose)\b',
        r'\b(bleeding\s+heavily|unconscious|not\s+responding)\b'
    ]
    msg = message.lower().strip()
    return any(re.search(pattern, msg) for pattern in emergency_patterns)

# --- Enhanced Response Functions ---
def get_medical_greeting_response():
    """Professional medical bot greetings with time awareness"""
    current_hour = datetime.datetime.now().hour
    
    if 5 <= current_hour < 12:
        responses = [
            "Good morning! I'm your medical AI assistant. I hope you're feeling well today. How can I help you with your health concerns?",
            "Morning! I'm here to provide medical information and support. What brings you here today?",
            "Good morning! I'm ready to help answer your health-related questions. How are you feeling?"
        ]
    elif 12 <= current_hour < 17:
        responses = [
            "Good afternoon! I'm your healthcare AI companion. How can I assist you with your medical concerns today?",
            "Afternoon! I'm here to help with health questions and provide medical information. What's on your mind?",
            "Good afternoon! I'm your medical assistant, ready to help. How are you feeling today?"
        ]
    elif 17 <= current_hour < 21:
        responses = [
            "Good evening! I'm here to help with your health questions. How can I assist you tonight?",
            "Evening! I'm your medical AI assistant. What health concerns can I help you with?",
            "Good evening! I hope you're feeling well. How can I support your health today?"
        ]
    else:
        responses = [
            "Hello! I'm available 24/7 for your health questions. How can I help you tonight?",
            "Hi there! Even at this late hour, I'm here to assist with your medical concerns. What's keeping you up?",
            "Hello! I'm your round-the-clock medical assistant. How can I help you?"
        ]
    
    return random.choice(responses)

def get_farewell_response():
    """Professional medical farewell responses"""
    responses = [
        "Take care of yourself! Remember, I'm here whenever you need health information. Stay healthy! 🏥",
        "Goodbye! Thank you for trusting me with your health questions. Feel free to return anytime. Wishing you good health! 💙",
        "Take care! Remember to consult healthcare professionals for serious concerns. I'm always here to help! 🩺",
        "Stay healthy and safe! Don't hesitate to reach out if you have more health questions. Goodbye! 🌟",
        "Farewell! Remember that your health is precious. I'm here 24/7 if you need more information. Take care! ❤️"
    ]
    return random.choice(responses)

def get_small_talk_response():
    """Friendly but professional small talk responses"""
    responses = [
        "I'm doing well and ready to help! As your medical AI assistant, I'm here to support your health journey. What can I help you with? 😊",
        "Thank you for asking! I'm functioning perfectly and excited to help with your health questions. How are you feeling today? 🤖",
        "I'm great, thank you! I'm designed to be your reliable health companion. What medical concerns can I assist you with? 💪",
        "All systems are working well! I'm here to provide medical information and support. How can I help improve your health today? 🌟",
        "You're welcome! If you have any more questions, feel free to ask. Wishing you good health!",
        "No problem! If you need anything else, just let me know.",
        "Alright! If you have more questions later, I'm here to help.",
        "Glad I could assist. Take care!"
    ]
    return random.choice(responses)

def get_emergency_response():
    """Emergency response with clear instructions"""
    return """⚠️ MEDICAL EMERGENCY DETECTED ⚠️

If this is a life-threatening emergency:
🚨 CALL 911 (US) or your local emergency number IMMEDIATELY
🚨 Go to the nearest emergency room
🚨 Don't delay seeking immediate professional medical help

For urgent but non-emergency situations, please contact:
📞 Your doctor's office
📞 Urgent care center
📞 Nurse hotline

I can provide general health information, but I cannot replace emergency medical care. Your safety is the top priority!"""

def sanitize_response(response_text):
    """Clean and format the response"""
    if not response_text:
        return "I apologize, but I couldn't generate a proper response. Please try rephrasing your question or consult a healthcare professional."
    
    # Remove any potential harmful content or excessive technical jargon
    response_text = response_text.strip()
    
    # Add medical disclaimer for medical advice
    medical_keywords = ['diagnosis', 'treatment', 'medication', 'disease', 'condition', 'symptoms']
    if any(keyword in response_text.lower() for keyword in medical_keywords):
        if "consult" not in response_text.lower() and "healthcare professional" not in response_text.lower():
            response_text += "\n\n⚠️ Please consult with a healthcare professional for personalized medical advice."
    
    return response_text

@app.route("/get", methods=["POST"])
def chat():
    """Enhanced chat endpoint with better error handling"""
    try:
        msg = request.form.get("msg", "").strip()
        if not msg:
            return jsonify({"error": "Please enter a message"}), 400
        
        logger.info(f"User input: {msg}")
        
        # Check for emergency keywords first
        if is_emergency_keywords(msg):
            return get_emergency_response()
        
        # Handle different intents
        if is_greeting(msg):
            return get_medical_greeting_response()
        
        if is_farewell(msg):
            return get_farewell_response()
        
        if is_small_talk(msg):
            return get_small_talk_response()
        
        # Medical Q&A via RAG
        try:
            response = rag_chain.invoke({"input": msg})
            
            # Handle different response formats
            if isinstance(response, dict):
                if "answer" in response:
                    answer = response["answer"]
                elif "output" in response:
                    answer = response["output"]
                else:
                    answer = str(response)
            else:
                answer = str(response)
            
            # Sanitize and format the response
            final_response = sanitize_response(answer)
            logger.info(f"Generated response length: {len(final_response)}")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in RAG chain: {e}")
            return "I apologize, but I'm experiencing technical difficulties with my medical knowledge base. For urgent health matters, please consult a healthcare professional directly."
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error. Please try again later."}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting medical bot server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)