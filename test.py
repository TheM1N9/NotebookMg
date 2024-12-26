import os
from drive_manager import DriveManager
from pathlib import Path
import shutil


def create_test_files():
    """Create test PDF and MP3 files"""
    # Create test directories if they don't exist
    test_dirs = ["uploads", "outputs"]
    for dir_name in test_dirs:
        os.makedirs(dir_name, exist_ok=True)

    # Create a dummy PDF file
    pdf_path = Path("uploads/test.pdf")
    with open(pdf_path, "w") as f:
        f.write("This is a test PDF content")

    # Create a dummy MP3 file
    mp3_path = Path("outputs/test.mp3")
    with open(mp3_path, "w") as f:
        f.write("This is a test MP3 content")

    return pdf_path, mp3_path


def test_drive_operations():
    """Test all Drive operations"""
    try:
        # Initialize DriveManager
        print("Initializing DriveManager...")
        drive_mgr = DriveManager()
        print("✓ DriveManager initialized successfully")

        # Create test files
        print("\nCreating test files...")
        pdf_path, mp3_path = create_test_files()
        print("✓ Test files created")

        # Test file upload
        print("\nTesting file upload...")
        pdf_id = drive_mgr.upload_file(str(pdf_path), "uploads")
        print(f"✓ PDF uploaded successfully (ID: {pdf_id})")
        mp3_id = drive_mgr.upload_file(str(mp3_path), "outputs")
        print(f"✓ MP3 uploaded successfully (ID: {mp3_id})")

        # Test saving to library
        print("\nTesting library save...")
        test_transcript = "This is a test transcript"
        drive_mgr.save_generation(
            title="Test Generation",
            pdf_path=str(pdf_path),
            podcast_path=str(mp3_path),
            transcript=test_transcript,
        )
        print("✓ Generation saved to library")

        # Test retrieving library items
        print("\nTesting library retrieval...")
        items = drive_mgr.get_library_items()
        print(f"✓ Retrieved {len(items)} items from library")

        # Print library items
        print("\nLibrary contents:")
        for item in items:
            print(f"- {item['title']} (Created: {item['created_time']})")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

    finally:
        # Cleanup test files
        print("\nCleaning up test files...")
        try:
            if pdf_path.exists():
                pdf_path.unlink()
            if mp3_path.exists():
                mp3_path.unlink()
            print("✓ Test files cleaned up")
        except Exception as e:
            print(f"Warning: Could not clean up test files: {str(e)}")


def main():
    print("=== Starting Drive Integration Test ===\n")
    success = test_drive_operations()
    print("\n=== Test Complete ===")
    print("Status:", "✓ Passed" if success else "❌ Failed")


if __name__ == "__main__":
    main()
