from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from pathlib import Path
from main import NotebookMg
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize the NotebookGemini instance
try:
    gemini_bot = NotebookMg(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "dude, wth enter your key"),
        eleven_api_key=os.getenv("ELEVEN_API_KEY", "dude, wth enter your key"),
        Tharun_voice_id="21m00Tcm4TlvDq8ikWAM",
        Monica_voice_id="IKne3meq5aSn9XLyUdCD",
    )
except Exception as e:
    logger.error(f"Failed to initialize NotebookMg: {str(e)}")
    raise


# @app.get("/", response_class=HTMLResponse)
# async def read_root(request):
#     return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...),
    tharun_voice_id: str = Form(...),
    monica_voice_id: str = Form(...),
):
    """Upload PDF and generate podcast"""
    pdf_path = None  # Initialize pdf_path before try block
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Please upload a PDF")
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        logger.info(f"Processing file: {file.filename}")

        # Save the uploaded PDF
        pdf_path = UPLOAD_DIR / file.filename
        try:
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        try:
            # Update the gemini_bot instance with user-provided voice IDs
            gemini_bot.Tharun_voice_id = tharun_voice_id
            gemini_bot.Monica_voice_id = monica_voice_id

            # Generate unique output filenames
            base_name = pdf_path.stem
            cleaned_text_path = OUTPUT_DIR / f"{base_name}_cleaned.txt"
            transcript_path = OUTPUT_DIR / f"{base_name}_transcript.txt"
            podcast_path = OUTPUT_DIR / f"{base_name}_podcast.mp3"

            # Process the PDF
            logger.info("Processing PDF...")
            cleaned_text = gemini_bot.process_pdf(str(pdf_path))
            with open(cleaned_text_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)

            logger.info("Creating transcript...")
            transcript = gemini_bot.create_transcript(cleaned_text)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            logger.info("Dramatizing transcript...")
            speaker_lines = gemini_bot.dramatize_transcript(transcript)

            logger.info("Generating audio...")
            gemini_bot.generate_audio(speaker_lines, str(podcast_path))

            return {
                "message": "Podcast generated successfully",
                "podcast_file": podcast_path.name,
            }

        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Clean up uploaded PDF
        if pdf_path and pdf_path.exists():
            try:
                os.remove(pdf_path)
            except Exception as e:
                logger.error(f"Failed to clean up uploaded file: {str(e)}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


@app.get("/status")
async def get_status():
    """Check API status"""
    return {"status": "running"}
