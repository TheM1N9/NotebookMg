import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from pathlib import Path
from main import NotebookMg
from dotenv import load_dotenv
import logging
from pydub import AudioSegment
from drive_manager import DriveManager
import httpx
import time
from datetime import datetime

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

# Initialize DriveManager
drive_mgr = DriveManager()


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
    pdf_path = None
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Please upload a PDF")
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Save the uploaded PDF temporarily
        pdf_path = UPLOAD_DIR / file.filename
        try:
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Upload to Drive
            pdf_id = drive_mgr.upload_file(str(pdf_path), "uploads")

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
            # text = gemini_bot.get_pdf_text(str(pdf_path))
            # cleaned_text = gemini_bot.process_pdf(text)
            # with open(cleaned_text_path, "w", encoding="utf-8") as f:
            #     f.write(cleaned_text)
            gemini_file = gemini_bot.upload_to_gemini(Path(pdf_path))

            logger.info("Creating transcript...")
            transcript = gemini_bot.create_transcript(gemini_file)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            logger.info("Dramatizing transcript...")
            speaker_lines = gemini_bot.dramatize_transcript(transcript)

            # Save transcript
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            # Process segments and generate audio
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

                # Upload segment to Drive
                segment_id = drive_mgr.upload_file(str(segment_path), "outputs")
                segment_files.append(
                    {
                        "file": segment_path.name,
                        "speaker": speaker,
                        "text": line,
                        "drive_id": segment_id,
                    }
                )

            # Generate and upload final podcast
            gemini_bot.generate_audio(speaker_lines, str(podcast_path))
            podcast_id = drive_mgr.upload_file(str(podcast_path), "outputs")

            # Save to library
            try:
                drive_mgr.save_generation(
                    title=base_name,
                    pdf_path=str(pdf_path),
                    podcast_path=str(podcast_path),
                    transcript=transcript,
                )
            except Exception as e:
                logger.error(f"Failed to save to library: {str(e)}")

            return {
                "message": "Podcast generated successfully",
                "podcast_url": f"/download/{podcast_id}",
                "segments": [
                    {**segment, "audio_url": f"/download/{segment['drive_id']}"}
                    for segment in segment_files
                ],
                "drive_ids": {
                    "pdf": pdf_id,
                    "podcast": podcast_id,
                    "segments": [s["drive_id"] for s in segment_files],
                },
            }

        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    finally:
        # Clean up temporary files
        if pdf_path and pdf_path.exists():
            try:
                os.remove(pdf_path)
            except Exception as e:
                logger.error(f"Failed to clean up uploaded file: {str(e)}")


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download a file from Drive"""
    try:
        # Get file stream directly instead of using download link
        file_stream = drive_mgr.get_file_stream(file_id)

        # Get file metadata to determine filename and type
        file = drive_mgr._execute_with_retry(
            drive_mgr.service.files().get(fileId=file_id, fields="name, mimeType")
        )

        return StreamingResponse(
            file_stream,
            media_type=file.get("mimeType", "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename={file.get('name', 'download')}"
            },
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Check API status"""
    return {"status": "running"}


# TODO: Check which audios were playing and regenerate only those
@app.post("/regenerate-segment/{segment_index}")
async def regenerate_segment(
    segment_index: int,
    speaker: str = Form(...),
    text: str = Form(...),
    tharun_voice_id: str = Form(...),
    akshara_voice_id: str = Form(...),
):
    """Regenerate a specific segment with new text"""
    try:
        # Select the appropriate voice ID based on speaker name
        voice_id = akshara_voice_id if speaker == "Akshara" else tharun_voice_id
        print(f"Using voice ID {voice_id} for speaker {speaker}")  # Debug log

        # Generate new audio using ElevenLabs
        audio_data = gemini_bot.eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text or "No text provided",  # Fallback if text is undefined
            model_id="eleven_multilingual_v2",
        )

        # Get the base name from existing segments
        base_name = next(OUTPUT_DIR.glob("*_segment_0.mp3")).stem.rsplit(
            "_segment_0", 1
        )[0]
        segment_path = OUTPUT_DIR / f"{base_name}_segment_{segment_index}.mp3"

        # Save the regenerated segment
        audio_bytes = b"".join(audio_data)
        with open(segment_path, "wb") as f:
            f.write(audio_bytes)

        # Upload to Drive and get new file ID
        file_id = drive_mgr.upload_file(str(segment_path), "outputs")

        return {
            "success": True,
            "segment_file": segment_path.name,
            "download_url": f"/download/{file_id}",
        }

    except Exception as e:
        logger.error(f"Regeneration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Regeneration error: {str(e)}")


@app.get("/library")
async def library_page(request: Request):
    """Serve the library page"""
    try:
        items = drive_mgr.get_library_items()
        # For each item, get the file details
        for item in items:
            folder_id = item["folder_id"]
            # Get all files in the folder
            files = drive_mgr.list_folder_files(folder_id)
            item["files"] = files
        return templates.TemplateResponse(
            "library.html", {"request": request, "items": items}
        )
    except Exception as e:
        logger.error(f"Error getting library items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-generation/{folder_id}")
async def delete_generation(folder_id: str):
    """Delete a generation"""
    try:
        drive_mgr.delete_generation(folder_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/share-generation/{folder_id}")
async def share_generation(folder_id: str):
    """Create a shareable link for a generation"""
    try:
        share_link = drive_mgr.create_share_link(folder_id)
        return {"share_link": share_link}
    except Exception as e:
        logger.error(f"Error creating share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save-to-library")
async def save_to_library(
    title: str = Form(...),
    pdf_file: UploadFile = File(...),
    podcast_file: UploadFile = File(...),
    transcript: str = Form(...),
):
    """Save a generation to the library"""
    pdf_path = None
    podcast_path = None
    try:
        # Check if filenames exist
        if not pdf_file.filename or not podcast_file.filename:
            raise HTTPException(status_code=400, detail="Missing filename")

        # Save files temporarily
        pdf_path = UPLOAD_DIR / str(pdf_file.filename)
        podcast_path = OUTPUT_DIR / str(podcast_file.filename)

        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf_file.file, f)
        with open(podcast_path, "wb") as f:
            shutil.copyfileobj(podcast_file.file, f)

        # Save to Drive
        drive_mgr.save_generation(title, str(pdf_path), str(podcast_path), transcript)

        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving to library: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temporary files
        if pdf_path and pdf_path.exists():
            pdf_path.unlink()
        if podcast_path and podcast_path.exists():
            podcast_path.unlink()


@app.put("/rename-generation/{folder_id}")
async def rename_generation(folder_id: str, title: str = Form(...)):
    """Rename a generation"""
    try:
        result = drive_mgr.rename_generation(folder_id, title)
        return {
            "success": True,
            "folder_id": result["id"],
            "new_title": title,
            "new_name": result["name"],
        }
    except Exception as e:
        logger.error(f"Error renaming generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate-podcast")
async def regenerate_podcast(request: Request):
    """Regenerate the full podcast from updated segments"""
    try:
        data = await request.json()
        segments = data.get("segments", [])
        speaker_lines = [(seg["speaker"], seg["text"]) for seg in segments]

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        podcast_path = OUTPUT_DIR / f"podcast_{timestamp}.mp3"

        # Generate the audio
        gemini_bot.generate_audio(speaker_lines, str(podcast_path))

        # Upload to Drive
        podcast_id = drive_mgr.upload_file(str(podcast_path), "outputs")

        # Clean up the local file
        if podcast_path.exists():
            podcast_path.unlink()

        return {
            "success": True,
            "podcast_url": f"/download/{podcast_id}",
            "message": "Podcast regenerated successfully",
        }
    except Exception as e:
        logger.error(f"Error regenerating podcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/view-pdf/{folder_id}")
async def view_pdf(folder_id: str):
    """Stream PDF file for viewing in browser"""
    try:
        # List files in the folder and find the PDF
        files = drive_mgr.list_folder_files(folder_id)
        pdf_file = next((file for file in files if file["type"] == "pdf"), None)

        if not pdf_file:
            raise HTTPException(status_code=404, detail="PDF file not found")

        # Get the file stream using the PDF file's ID
        file_stream = drive_mgr.get_file_stream(pdf_file["id"])

        return StreamingResponse(
            file_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        logger.error(f"Error viewing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
