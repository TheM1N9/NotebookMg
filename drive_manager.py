from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import os
import json
from datetime import datetime
from pathlib import Path
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import io

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveManager:
    def __init__(self):
        self.creds = None
        self.FOLDERS = {
            "root": "NotebookMg",
            "uploads": "Uploads",
            "outputs": "Outputs",
            "library": "Library",
        }
        self.folder_ids = {}
        self.initialize_drive()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _execute_with_retry(self, request):
        """Execute a Drive API request with retry logic"""
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status in [403, 429, 500, 503]:  # Rate limit or server errors
                print(f"Drive API error {e.resp.status}: {str(e)}")
                time.sleep(2)  # Add a small delay before retry
                raise  # Let retry handle it
            raise  # Other errors
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

    def initialize_drive(self):
        """Initialize Drive API with stored tokens"""
        try:
            # Create credentials from environment variables
            self.creds = Credentials(
                token=os.getenv("DRIVE_TOKEN"),
                refresh_token=os.getenv("DRIVE_REFRESH_TOKEN"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("DRIVE_CLIENT_ID"),
                client_secret=os.getenv("DRIVE_CLIENT_SECRET"),
                scopes=SCOPES,
            )

            self.service = build("drive", "v3", credentials=self.creds)
            self._ensure_folder_structure()
        except Exception as e:
            print(f"Failed to initialize Drive: {str(e)}")
            raise

    def _ensure_folder_structure(self):
        """Create or get the folder structure with retry logic"""
        # Create root folder if it doesn't exist
        root_query = f"name='{self.FOLDERS['root']}' and mimeType='application/vnd.google-apps.folder'"
        results = self._execute_with_retry(
            self.service.files().list(q=root_query, spaces="drive")
        )
        items = results.get("files", [])

        if not items:
            root_metadata = {
                "name": self.FOLDERS["root"],
                "mimeType": "application/vnd.google-apps.folder",
            }
            root_folder = self._execute_with_retry(
                self.service.files().create(body=root_metadata, fields="id")
            )
            self.folder_ids["root"] = root_folder.get("id")
        else:
            self.folder_ids["root"] = items[0]["id"]

        # Create subfolders
        for folder_key in ["uploads", "outputs", "library"]:
            folder_query = f"name='{self.FOLDERS[folder_key]}' and '{self.folder_ids['root']}' in parents"
            results = self._execute_with_retry(
                self.service.files().list(q=folder_query)
            )
            items = results.get("files", [])

            if not items:
                folder_metadata = {
                    "name": self.FOLDERS[folder_key],
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [self.folder_ids["root"]],
                }
                folder = self._execute_with_retry(
                    self.service.files().create(body=folder_metadata, fields="id")
                )
                self.folder_ids[folder_key] = folder.get("id")
            else:
                self.folder_ids[folder_key] = items[0]["id"]

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def upload_file(self, file_path: str, file_type: str = "uploads") -> str:
        """Upload a file to the specified folder type with retry logic"""
        if file_type not in self.folder_ids:
            raise ValueError(f"Invalid file type: {file_type}")

        try:
            file_metadata = {
                "name": Path(file_path).name,
                "parents": [self.folder_ids[file_type]],
            }

            # Ensure the file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            media = MediaFileUpload(
                file_path, resumable=True  # Enable resumable uploads
            )

            file = self._execute_with_retry(
                self.service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                )
            )
            return file.get("id")
        except Exception as e:
            print(f"Error uploading file {file_path}: {str(e)}")
            raise

    def save_generation(
        self, title: str, pdf_path: str, podcast_path: str, transcript: str
    ):
        """Save a new generation to Drive"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{title}_{timestamp}"

            # Create generation folder in library
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.folder_ids["library"]],
            }
            folder = self._execute_with_retry(
                self.service.files().create(body=folder_metadata, fields="id")
            )
            folder_id = folder.get("id")

            # Save metadata
            metadata = {
                "title": title,
                "timestamp": timestamp,
                "pdf_name": Path(pdf_path).name,
                "podcast_name": Path(podcast_path).name,
            }

            # Create temporary files
            metadata_path = Path("temp_metadata.json")
            transcript_path = Path("temp_transcript.txt")

            try:
                # Save metadata and transcript to temporary files
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(transcript)

                # Upload all files to the generation folder
                self._upload_file(pdf_path, folder_id)
                self._upload_file(podcast_path, folder_id)
                self._upload_file(str(metadata_path), folder_id)
                self._upload_file(str(transcript_path), folder_id)

            finally:
                # Cleanup temporary files
                if metadata_path.exists():
                    metadata_path.unlink()
                if transcript_path.exists():
                    transcript_path.unlink()

            return folder_id

        except Exception as e:
            print(f"Error saving generation: {str(e)}")
            raise

    def get_file_content(self, file_id: str) -> bytes:
        """Download and return the content of a file"""
        request = self.service.files().get_media(fileId=file_id)
        return request.execute()

    def get_file_download_link(self, file_id: str):
        """Get a direct download link for a file"""
        try:
            if not self.creds:
                raise ValueError("Credentials not initialized")

            # Get file metadata to ensure it exists and get its MIME type
            file = self._execute_with_retry(
                self.service.files().get(fileId=file_id, fields="id, mimeType")
            )

            # Generate download URL
            download_url = (
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            )

            # Add authorization header
            headers = {
                "Authorization": f"Bearer {self.creds.token}",
            }

            return download_url, headers
        except Exception as e:
            print(f"Error getting download link: {e}")
            raise

    def delete_file(self, file_id: str):
        """Delete a file from Drive"""
        self.service.files().delete(fileId=file_id).execute()

    def get_library_items(self):
        """Get all generations from the library"""
        try:
            # Query folders in the library folder
            query = f"'{self.folder_ids['library']}' in parents and mimeType='application/vnd.google-apps.folder'"
            results = (
                self.service.files()
                .list(q=query, spaces="drive", fields="files(id, name, createdTime)")
                .execute()
            )

            items = []
            for folder in results.get("files", []):
                # Parse the folder name which should be in format: title_timestamp
                folder_parts = folder["name"].split("_")
                if len(folder_parts) >= 2:
                    title = "_".join(
                        folder_parts[:-1]
                    )  # Everything except the last part
                    timestamp = folder_parts[-1]  # Last part is the timestamp

                    items.append(
                        {
                            "folder_id": folder["id"],
                            "title": title,
                            "timestamp": timestamp,
                            "created_time": folder["createdTime"],
                        }
                    )

            return sorted(items, key=lambda x: x["created_time"], reverse=True)
        except Exception as e:
            print(f"Error getting library items: {e}")
            return []

    def _upload_file(self, file_path: str, folder_id: str) -> str:
        """Upload a file to a specific folder"""
        file_metadata = {"name": Path(file_path).name, "parents": [folder_id]}
        media = MediaFileUpload(file_path)
        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file.get("id")

    def delete_generation(self, folder_id: str):
        """Delete a generation folder and all its contents"""
        try:
            # First, list all files in the folder
            query = f"'{folder_id}' in parents"
            results = self.service.files().list(q=query, fields="files(id)").execute()

            # Delete all files in the folder
            for file in results.get("files", []):
                self.service.files().delete(fileId=file["id"]).execute()

            # Delete the folder itself
            self.service.files().delete(fileId=folder_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting generation: {e}")
            raise

    def create_share_link(self, folder_id: str) -> str:
        """Create a shareable link for a folder"""
        try:
            # Update sharing settings to anyone with the link can view
            file_metadata = {"role": "reader", "type": "anyone"}
            self._execute_with_retry(
                self.service.permissions().create(fileId=folder_id, body=file_metadata)
            )

            # Get the web view link
            file = self._execute_with_retry(
                self.service.files().get(fileId=folder_id, fields="webViewLink")
            )

            return file.get("webViewLink")
        except Exception as e:
            print(f"Error creating share link: {e}")
            raise

    def verify_file(self, file_id: str) -> bool:
        """Verify that a file exists in Drive"""
        try:
            self._execute_with_retry(self.service.files().get(fileId=file_id))
            return True
        except Exception as e:
            print(f"File verification failed for ID {file_id}: {e}")
            raise

    def list_folder_files(self, folder_id: str) -> list:
        """List all files in a folder"""
        try:
            query = f"'{folder_id}' in parents"
            results = self._execute_with_retry(
                self.service.files().list(
                    q=query, fields="files(id, name, mimeType)", spaces="drive"
                )
            )
            files = results.get("files", [])

            # Add download URLs for each file
            for file in files:
                file["download_url"] = f"/download/{file['id']}"
                # Determine file type
                if file["name"].endswith(".pdf"):
                    file["type"] = "pdf"
                elif file["name"].endswith(".mp3"):
                    file["type"] = "audio"
                elif file["name"].endswith(".json"):
                    file["type"] = "metadata"
                elif file["name"].endswith(".txt"):
                    file["type"] = "transcript"
                else:
                    file["type"] = "other"

            return files
        except Exception as e:
            print(f"Error listing folder files: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(HttpError),
    )
    def rename_generation(self, folder_id: str, new_title: str):
        """Rename a generation folder"""
        try:
            # Get current folder details to preserve timestamp
            folder = self._execute_with_retry(
                self.service.files().get(fileId=folder_id, fields="name")
            )

            # Extract timestamp from current name if it exists
            current_name = folder.get("name", "")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if "_" in current_name:
                timestamp = current_name.split("_")[-1]

            # Create new name with preserved timestamp
            new_name = f"{new_title}_{timestamp}"

            # Update folder metadata
            file_metadata = {"name": new_name}
            updated_folder = self._execute_with_retry(
                self.service.files().update(
                    fileId=folder_id, body=file_metadata, fields="id, name"
                )
            )

            return {
                "id": updated_folder["id"],
                "name": updated_folder["name"],
                "title": new_title,
                "timestamp": timestamp,
            }
        except Exception as e:
            print(f"Error renaming generation: {e}")
            raise

    def list_library_items(self):
        """List all items in the library folder"""
        try:
            items = []
            library_id = self.folder_ids.get("library")

            if not library_id:
                return items

            results = self._execute_with_retry(
                self.service.files().list(
                    q=f"'{library_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                    fields="files(id, name, createdTime)",
                    orderBy="createdTime desc",
                )
            )

            for folder in results.get("files", []):
                # Parse the name and timestamp
                name_parts = folder["name"].split("_")
                if len(name_parts) > 1:
                    title = " ".join(name_parts[:-1])
                    # Parse the timestamp from createdTime
                    created_time = datetime.fromisoformat(
                        folder["createdTime"].replace("Z", "+00:00")
                    )
                    # Format as "Generated at HH:MM"
                    timestamp = created_time.strftime("Generated at %H:%M")
                else:
                    title = folder["name"]
                    timestamp = "Generated at unknown time"

                items.append(
                    {"folder_id": folder["id"], "title": title, "timestamp": timestamp}
                )

            return items
        except Exception as e:
            print(f"Error listing library items: {e}")
            raise

    def get_file_stream(self, file_id: str):
        """Get a file stream from Google Drive"""
        try:
            # Get the file metadata with mimeType
            file = self._execute_with_retry(
                self.service.files().get(fileId=file_id, fields="mimeType")
            )

            # Get the file content with the correct mimeType
            request = self.service.files().get_media(
                fileId=file_id,
                acknowledgeAbuse=True,  # Add this to handle potential warnings
            )

            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            file_stream.seek(0)
            return file_stream
        except Exception as e:
            print(f"Error getting file stream: {e}")
            raise

    # Consider adding caching for frequently accessed files
    # Add batch operations for multiple file uploads
    # Implement pagination for library items
