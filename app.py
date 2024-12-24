import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from pathlib import Path
from main import NotebookMg
from dotenv import load_dotenv
import logging
from pydub import AudioSegment

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)  # Disable Swagger UI  # Disable ReDoc

# Mount static directory - make sure this comes before other routes
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create necessary directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
STATIC_DIR = Path("static")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Make sure styles.css exists in static directory
if not (STATIC_DIR / "styles.css").exists():
    logger.warning("styles.css not found in static directory")

# Initialize the NotebookGemini instance
try:
    gemini_bot = NotebookMg(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "dude, wth enter your key"),
        eleven_api_key=os.getenv("ELEVEN_API_KEY", "dude, wth enter your key"),
        Tharun_voice_id="21m00Tcm4TlvDq8ikWAM",
        Akshara_voice_id="IKne3meq5aSn9XLyUdCD",
    )
except Exception as e:
    logger.error(f"Failed to initialize NotebookMg: {str(e)}")
    raise


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the index page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...),
    tharun_voice_id: str = Form(...),
    akshara_voice_id: str = Form(...),
):
    """Upload PDF and generate podcast"""
    pdf_path = None  # Initialize pdf_path before try block
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Please upload a PDF")
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        logger.info(f"Processing file: {file.filename}")

        # Clean up old files before processing new upload
        try:
            # Clean up old segments and podcast files
            for old_file in OUTPUT_DIR.glob("*"):
                try:
                    os.remove(old_file)
                    logger.info(f"Cleaned up old file: {old_file}")
                except Exception as e:
                    logger.error(f"Failed to remove old file {old_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

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
            gemini_bot.Akshara_voice_id = akshara_voice_id

            # Generate unique output filenames
            base_name = pdf_path.stem
            cleaned_text_path = OUTPUT_DIR / f"{base_name}_cleaned.txt"
            transcript_path = OUTPUT_DIR / f"{base_name}_transcript.txt"
            podcast_path = OUTPUT_DIR / f"{base_name}_podcast.mp3"

            # Process the PDF
            logger.info("Processing PDF...")
            text = gemini_bot.get_pdf_text(str(pdf_path))
            cleaned_text = gemini_bot.process_pdf(text)
            with open(cleaned_text_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)

            logger.info("Creating transcript...")
            transcript = gemini_bot.create_transcript(cleaned_text, text)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            logger.info("Dramatizing transcript...")
            speaker_lines = gemini_bot.dramatize_transcript(transcript, text)

            # Save individual audio segments
            segment_files = []
            for i, (speaker, line) in enumerate(speaker_lines):
                segment_path = OUTPUT_DIR / f"{base_name}_segment_{i}.mp3"
                voice_id = (
                    gemini_bot.Akshara_voice_id
                    if speaker == "Akshara"
                    else gemini_bot.Tharun_voice_id
                )

                # Generate individual segment audio
                audio_data = gemini_bot.eleven_client.text_to_speech.convert(
                    voice_id=voice_id,
                    output_format="mp3_44100_128",
                    text=line,
                    model_id="eleven_multilingual_v2",
                )

                # Save segment
                audio_bytes = b"".join(audio_data)
                with open(segment_path, "wb") as f:
                    f.write(audio_bytes)

                segment_files.append(
                    {"file": segment_path.name, "speaker": speaker, "text": line}
                )

            # Generate final combined audio as before
            gemini_bot.generate_audio(speaker_lines, str(podcast_path))

            return {
                "message": "Podcast generated successfully",
                "podcast_file": podcast_path.name,
                "segments": segment_files,
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


@app.post("/regenerate-segment/{index}")
async def regenerate_segment(
    index: int,
    speaker: str = Form(...),
    text: str = Form(...),
    tharun_voice_id: str = Form(...),
    akshara_voice_id: str = Form(...),
):
    try:
        # Select the appropriate voice ID based on speaker
        voice_id = akshara_voice_id if speaker == "Akshara" else tharun_voice_id

        # Generate new audio using ElevenLabs
        audio_data = gemini_bot.eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2",
        )

        # Get the base name from existing segments
        base_name = next(OUTPUT_DIR.glob("*_segment_0.mp3")).stem.rsplit(
            "_segment_0", 1
        )[0]
        segment_path = OUTPUT_DIR / f"{base_name}_segment_{index}.mp3"

        # Delete the existing segment file if it exists
        if segment_path.exists():
            try:
                os.remove(segment_path)
                logger.info(f"Deleted existing segment file: {segment_path}")
            except Exception as e:
                logger.error(f"Error deleting existing segment file: {str(e)}")
                # Continue anyway as we'll overwrite the file

        # Save the regenerated segment
        audio_bytes = b"".join(audio_data)
        with open(segment_path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"Saved new segment file: {segment_path}")

        # Delete existing podcast file if it exists
        podcast_path = OUTPUT_DIR / f"{base_name}_podcast.mp3"
        if podcast_path.exists():
            try:
                os.remove(podcast_path)
                logger.info(f"Deleted existing podcast file: {podcast_path}")
            except Exception as e:
                logger.error(f"Error deleting existing podcast file: {str(e)}")

        # Combine all segments into a new complete podcast
        combined_audio = AudioSegment.empty()

        # Get all segment files and sort them correctly
        segment_files = sorted(
            [f for f in OUTPUT_DIR.glob(f"{base_name}_segment_*.mp3")],
            key=lambda x: int(x.stem.split("_")[-1]),
        )

        logger.info(f"Found {len(segment_files)} segments to combine")

        # Add each segment to the combined audio
        for segment_file in segment_files:
            try:
                logger.info(f"Processing segment: {segment_file}")
                audio_segment = AudioSegment.from_file(segment_file, format="mp3")
                pause = AudioSegment.silent(duration=300)  # 300ms pause
                combined_audio += audio_segment + pause
            except Exception as e:
                logger.error(f"Error processing segment {segment_file}: {str(e)}")
                raise

        # Save the new complete podcast
        combined_audio.export(str(podcast_path), format="mp3")
        logger.info(
            f"Successfully generated new podcast with {len(segment_files)} segments"
        )

        return {
            "success": True,
            "segment_file": segment_path.name,
            "podcast_file": podcast_path.name,
        }

    except Exception as e:
        logger.error(f"Regeneration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Regeneration error: {str(e)}")


# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
