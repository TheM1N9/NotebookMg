# NotebookMg

This project converts PDF documents into engaging podcast conversations using AI. It leverages Google's Gemini Pro for text processing and ElevenLabs for voice synthesis.

## Features

- PDF text extraction and cleaning
- Conversion of academic/technical content into natural dialogue
- Dynamic conversation generation between two hosts (Alex and Jamie)
- High-quality text-to-speech synthesis
- Web interface for easy interaction
- API endpoints for programmatic access

## Prerequisites

- Python 3.8+
- Google Gemini API key
- ElevenLabs API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-to-podcast
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create a .env file
touch .env

# Add your API keys
echo "GEMINI_API_KEY=your_gemini_api_key" >> .env
echo "ELEVEN_API_KEY=your_elevenlabs_api_key" >> .env
```

## Project Structure

```
pdf-to-podcast/
├── main.py           # Core conversion logic
├── app.py           # FastAPI application
├── run.py           # Server startup script
├── templates/       # HTML templates
│   └── index.html   # Web interface
├── uploads/         # Temporary PDF storage
└── outputs/         # Generated files
```

## Usage

### Web Interface

1. Start the server:
```bash
python run.py
```

2. Open your browser and navigate to `http://localhost:8000`
3. Upload a PDF file
4. Download the generated files:
   - Cleaned text version
   - Conversation transcript
   - MP3 podcast file

### API Endpoints

- `POST /upload-pdf/`: Upload PDF and generate podcast
- `GET /download/{filename}`: Download generated files
- `GET /status`: Check API status

## API Examples

```python
import requests

# Upload PDF
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload-pdf/',
        files={'file': f}
    )
    
# Download generated podcast
response = requests.get(
    'http://localhost:8000/download/document_podcast.mp3'
)
```

## Configuration

Voice IDs can be configured in `main.py`:
```python
self.alex_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
self.jamie_voice_id = "IKne3meq5aSn9XLyUdCD"  # Adam voice
```

## Dependencies

- `google-generativeai`: Gemini Pro API
- `elevenlabs`: Text-to-speech synthesis
- `PyPDF2`: PDF processing
- `fastapi`: Web API framework
- `pydub`: Audio processing
- `python-multipart`: File upload handling
- `uvicorn`: ASGI server
- `jinja2`: Template engine

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini for AI text processing
- ElevenLabs for voice synthesis
- FastAPI team for the excellent web framework

## Support

For support, please open an issue in the GitHub repository or contact [your-email]. 