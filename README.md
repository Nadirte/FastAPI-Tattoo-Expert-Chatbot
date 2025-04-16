# Tattoo Chatbot API

A FastAPI-based web service for a tattoo studio that provides information about tattoo styles, pricing, and appointment booking through a conversational AI interface.

## Features

- **AI-Powered Chatbot**: Engage with customers using GPT-4o to answer questions about tattoos and guide the booking process
- **Appointment Management**: Book and track tattoo appointments with database storage
- **Tattoo Style Information**: Provide details about various tattoo styles and their pricing
- **User-Friendly Interface**: Simple web interface for customer interaction

## Prerequisites

- Python 3.8+
- OpenAI API key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/tattoo-chatbot-api.git
   cd tattoo-chatbot-api
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

1. Start the server:
   ```
   python main.py
   ```

2. Access the web interface at `http://localhost:8000/`

3. The API will be available at the following endpoints:
   - `/chat` - POST request to interact with the chatbot
   - `/appointments` - GET to list appointments, POST to create a new appointment
   - `/tattoo-types` - GET available tattoo styles and pricing
   - `/random-tattoos` - GET random tattoo style suggestions

## API Endpoints

### POST /chat
Interact with the tattoo studio assistant chatbot.

Request:
```json
{
  "message": "Can you tell me about Japanese style tattoos?",
  "conversation_id": "optional_conversation_id"
}
```

Response:
```json
{
  "response": "Japanese style tattoos, also known as Irezumi, are characterized by bold outlines, vibrant colors, and traditional Japanese imagery such as koi fish, dragons, and cherry blossoms. Our Japanese style tattoos start at $300.",
  "conversation_id": "generated_conversation_id"
}
```

### POST /appointments
Book a new tattoo appointment.

Request:
```json
{
  "username": "John Doe",
  "city": "Seattle",
  "description": "Small Japanese dragon on forearm",
  "appointment_date": "2023-07-15",
  "tattoo_type": "japanese"
}
```

Response:
```json
{
  "status": "success",
  "message": "Appointment created successfully"
}
```

### GET /appointments
Retrieve all booked appointments.

Response:
```json
{
  "appointments": [
    {
      "id": 1,
      "username": "John Doe",
      "city": "Seattle",
      "description": "Small Japanese dragon on forearm",
      "appointment_date": "2023-07-15",
      "created_at": "2023-06-01 14:30:45"
    }
  ]
}
```

### GET /tattoo-types
Get information about available tattoo styles and pricing.

Response:
```json
{
  "tattoo_types": {
    "tribal": "$150",
    "traditional": "$200",
    "japanese": "$300",
    "watercolor": "$250"
    // ... additional styles
  }
}
```

### GET /random-tattoos
Get random tattoo style suggestions.

Response:
```json
{
  "tattoos": ["tribal", "geometric", "minimalist", "blackwork", "dotwork"]
}
```

## Tattoo Style Pricing

The application loads tattoo style pricing from a CSV file (`tattoo_type.csv`). If the file is not found, it will create a sample file with default pricing.

## Database

The application uses SQLite to store appointment information. The database file (`tattoo_appointments.db`) will be created automatically when the application runs for the first time.

## Booking Flow

The chatbot guides users through a conversational booking flow:
1. Ask for the user's name
2. Ask for the user's city
3. Ask for a description of the desired tattoo
4. Ask for the preferred appointment date
5. Confirm the appointment

## Customization

- Edit `tattoo_type.csv` to modify available styles and pricing
- Modify the system prompt in the `chat` endpoint to change the assistant's behavior and knowledge

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
