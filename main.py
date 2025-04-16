import os
import csv
import random
from datetime import datetime
import sqlite3
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

app = FastAPI(title="Tattoo Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("tattoo_appointments.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        city TEXT NOT NULL,
        description TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

def load_tattoo_types():
    tattoo_types = {}
    try:
        with open("tattoo_type.csv", "r") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if len(row) >= 2:
                    tattoo_type, price = row[0], row[1]
                    tattoo_types[tattoo_type.lower()] = price
    except FileNotFoundError:
        print("Warning: tattoo_type.csv not found. Creating sample data.")
        tattoo_types = {
            "tribal": "$150",
            "traditional": "$200",
            "japanese": "$300",
            "watercolor": "$250",
            "geometric": "$180",
            "portrait": "$400",
            "blackwork": "$220",
            "arrow path": "$70",
            "minimalist": "$100",
            "neo-traditional": "$250",
            "realism": "$350",
            "dotwork": "$200",
            "mandala": "$230",
            "biomechanical": "$380"
        }
    return tattoo_types

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class AppointmentRequest(BaseModel):
    username: str
    city: str
    description: str
    appointment_date: str
    tattoo_type: str

init_db()
TATTOO_TYPES = load_tattoo_types()

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o")

# Store conversation history
conversations = {}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat(request: ChatRequest):
    message = request.message
    conversation_id = request.conversation_id

    # Initialize conversation if it doesn't exist
    if conversation_id not in conversations:
        conversations[conversation_id] = {
            "messages": [],
            "booking_data": {},
            "booking_stage": None
        }

    conv = conversations[conversation_id]
    
    # Add user message to history
    conv["messages"].append({"role": "user", "content": message})
    
    # Check if we're in a booking flow
    if conv["booking_stage"] and conv["booking_stage"] != "completed":
        result = await handle_booking_flow(message, conv)
        # Add assistant message to history
        conv["messages"].append({"role": "assistant", "content": result["response"]})
        return result
    
    # Construct system message with tattoo knowledge
    tattoo_info = "\n".join([f"- {t.title()}: {p}" for t, p in TATTOO_TYPES.items()])
    random_tattoos = random.sample(list(TATTOO_TYPES.keys()), min(5, len(TATTOO_TYPES)))
    
    system_message = f"""You are a friendly and knowledgeable tattoo studio assistant who helps customers learn about tattoo styles, 
    prices, and book appointments. Be conversational, helpful, and provide accurate information.

    Here are the tattoo styles we offer and their prices:
    {tattoo_info}

    If the user is interested in booking an appointment, guide them through the process by asking for:
    - Their name
    - Their city
    - Description of the tattoo they want
    - Preferred appointment date (in YYYY-MM-DD format)

    If the user asks about tattoo-related topics like books, movies, tattoo care, or tattoo history, provide 
    informative and helpful responses. Feel free to suggest resources for tattoo inspiration or aftercare.

    If the user seems undecided about a tattoo style, suggest these options: {', '.join(random_tattoos)}

    Remember to be friendly, professional, and supportive of the user's choices.
    """
    
    # Prepare conversation history for the API call
    messages = [
        SystemMessage(content=system_message)
    ]
    
    # Only include the last 10 messages in history to avoid token limits
    for msg in conv["messages"][-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"], name="assistant"))
    
    # Check for booking intent
    booking_intent = detect_booking_intent(message)
    if booking_intent:
        conv["booking_stage"] = "username"
        booking_response = "I'd be happy to help you book an appointment! Could you please tell me your name?"
        conv["messages"].append({"role": "assistant", "content": booking_response})
        return {"response": booking_response, "conversation_id": conversation_id}
    
    # Get response from LLM
    try:
        response = llm.invoke(messages)
        assistant_response = response.content
        
        # Add to conversation history
        conv["messages"].append({"role": "assistant", "content": assistant_response})
        
        return {"response": assistant_response, "conversation_id": conversation_id}
    except Exception as e:
        print(f"Error with LLM: {str(e)}")
        error_response = "I apologize, but I'm having trouble processing your request. Could you try again?"
        return {"response": error_response, "conversation_id": conversation_id}

async def handle_booking_flow(message: str, conv: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the booking flow process"""
    stage = conv["booking_stage"]
    booking_data = conv["booking_data"]
    
    if stage == "username":
        booking_data["username"] = message
        conv["booking_stage"] = "city"
        return {"response": f"Nice to meet you, {message}! Which city are you located in?"}
    
    elif stage == "city":
        booking_data["city"] = message
        conv["booking_stage"] = "description"
        return {"response": "Great! Please describe the tattoo you're interested in getting:"}
    
    elif stage == "description":
        booking_data["description"] = message
        conv["booking_stage"] = "date"
        return {"response": "That sounds fantastic! When would you like to book your appointment? (Please use YYYY-MM-DD format)"}
    
    elif stage == "date":
        try:
            appointment_date = datetime.strptime(message, "%Y-%m-%d")
            today = datetime.now()
            
            if appointment_date < today:
                return {"response": "That date is in the past. Please choose a future date (YYYY-MM-DD format)."}
            
            booking_data["appointment_date"] = message
            
            # Extract the tattoo type from the description or use "custom" as default
            tattoo_type = "custom"
            for t_type in TATTOO_TYPES.keys():
                if t_type in booking_data["description"].lower():
                    tattoo_type = t_type
                    break
            
            booking_data["tattoo_type"] = tattoo_type
            
            # Save to database
            try:
                conn = sqlite3.connect("tattoo_appointments.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO appointments (username, city, description, appointment_date, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        booking_data["username"],
                        booking_data["city"],
                        booking_data["description"],
                        booking_data["appointment_date"],
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
                conn.commit()
                conn.close()
                
                # Format date nicely
                formatted_date = appointment_date.strftime("%A, %B %d, %Y")
                conv["booking_stage"] = "completed"
                
                return {"response": f"Perfect! Your appointment has been confirmed for {formatted_date}. We're looking forward to seeing you! Is there anything else you'd like to know about preparing for your tattoo?"}
            except Exception as e:
                print(f"Database error: {str(e)}")
                return {"response": "I'm sorry, there was an error booking your appointment. Please try again or contact the studio directly."}
        except ValueError:
            return {"response": "I need a valid date in YYYY-MM-DD format (for example, 2025-05-15). When would you like to come in?"}
    
    return {"response": "I'm not sure what happened. Let's start over with your booking. What's your name?"}

def detect_booking_intent(message: str) -> bool:
    """Detect if the user wants to book an appointment"""
    booking_phrases = [
        "book", "appointment", "schedule", "reservation", "book a", "make a", 
        "set up", "arrange", "when can i", "available", "booking"
    ]
    message_lower = message.lower()
    
    return any(phrase in message_lower for phrase in booking_phrases)

@app.post("/appointments")
async def create_appointment(appointment: AppointmentRequest):
    try:
        datetime.strptime(appointment.appointment_date, "%Y-%m-%d")
        conn = sqlite3.connect("tattoo_appointments.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO appointments (username, city, description, appointment_date, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                appointment.username,
                appointment.city,
                appointment.description,
                appointment.appointment_date,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Appointment created successfully"}
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/appointments")
async def get_appointments():
    conn = sqlite3.connect("tattoo_appointments.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments ORDER BY appointment_date DESC")
    appointments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"appointments": appointments}

@app.get("/tattoo-types")
async def get_tattoo_types():
    return {"tattoo_types": TATTOO_TYPES}

@app.get("/random-tattoos")
async def get_random_tattoos(count: int = 5):
    tattoo_types = list(TATTOO_TYPES.keys())
    random_selection = random.sample(tattoo_types, min(count, len(tattoo_types)))
    return {"tattoos": random_selection}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"An error occurred: {str(exc)}"}
    )

def create_mock_csv():
    with open("tattoo_type.csv", "w") as file:
        file.write("type,price\n")
        file.write("tribal,$150\n")
        file.write("traditional,$200\n")
        file.write("japanese,$300\n")
        file.write("watercolor,$250\n")
        file.write("geometric,$180\n")
        file.write("portrait,$400\n")
        file.write("blackwork,$220\n")
        file.write("arrow path,$70\n")
        file.write("minimalist,$100\n")
        file.write("neo-traditional,$250\n")
        file.write("realism,$350\n")
        file.write("dotwork,$200\n")
        file.write("mandala,$230\n")
        file.write("biomechanical,$380\n")
        file.write("old school,$190\n")
        file.write("new school,$240\n")
        file.write("celtic,$210\n")
        file.write("fine line,$170\n")
        file.write("trash polka,$310\n")

if not os.path.exists("tattoo_type.csv"):
    create_mock_csv()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)