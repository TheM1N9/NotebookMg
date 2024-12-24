import google.generativeai as genai
import PyPDF2
import os
from pathlib import Path
from typing import Tuple, List
import json
import re
from elevenlabs import ElevenLabs, VoiceSettings
from pydub import AudioSegment
import io
from dotenv import load_dotenv
import ast
from examples import example1, example2

load_dotenv()


class NotebookMg:
    def __init__(
        self,
        gemini_api_key: str,
        eleven_api_key: str,
        Akshara_voice_id: str,
        Tharun_voice_id: str,
    ):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.eleven_client = ElevenLabs(api_key=eleven_api_key)

        # Use provided voice IDs or fall back to defaults
        self.Akshara_voice_id = Akshara_voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.Tharun_voice_id = Tharun_voice_id or "IKne3meq5aSn9XLyUdCD"

    def get_pdf_text(self, pdf_path: str) -> str:
        text = ""
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text

    def process_pdf(self, text: str) -> str:
        """Step 1: PDF Pre-processing"""

        # Clean up the text using Gemini
        prompt = """
        You are a world class text pre-processor, here is the raw data from a PDF, please parse and return it in a way that is crispy and usable to send to a podcast writer.

        The raw data is messed up with new lines, Latex math and you will see fluff that we can remove completely. Basically take away any details that you think might be useless in a podcast author's transcript.

        Remember, the podcast could be on any topic whatsoever so the issues listed above are not exhaustive

        Please be smart with what you remove and be creative ok?

        Remember DO NOT START SUMMARIZING THIS, YOU ARE ONLY CLEANING UP THE TEXT AND RE-WRITING WHEN NEEDED

        Be very smart and aggressive with removing details, you will get a running portion of the text and keep returning the processed text.

        PLEASE DO NOT ADD MARKDOWN FORMATTING, STOP ADDING SPECIAL CHARACTERS THAT MARKDOWN CAPATILISATION ETC LIKES

        ALWAYS start your response directly with processed text and NO ACKNOWLEDGEMENTS about my questions ok?

        PLEASE DO NOT REMOVE ANYTHING FROM THE TEXT, JUST CLEAN IT UP.

        DO NOT SUMMARIZE OR BRIEF THE TEXT, JUST CLEAN IT UP AND RE-WRITE WHEN NEEDED. 
        
        THE PODCAST SHOULD BE ATLEAST TEN MINUTES LONG.

        ALSO REASON ABOUT THE CHANGES YOU MADE TO THE TEXT. Output should be in JSON format

        OUTPUT FORMAT: 
        ```json
        
            "text": "processed text",
            "reasoning": "reasoning for the changes you made"
        
        ```
        Here is the text: {text}
        """
        response = self.model.generate_content(prompt.format(text=text))
        print(response.text)
        # First try to find JSON within code blocks
        match = re.search(r"```(?:json)?\n(.*?)\n```", response.text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # If no code blocks found, try to parse the entire response
            json_str = response.text
        pre_processed_text = json.loads(json_str)["text"]
        reasoning = json.loads(json_str)["reasoning"]
        print(f"Reasoning: {reasoning}")
        return pre_processed_text

    def create_transcript(self, cleaned_text: str, entire_text: str) -> str:
        """Step 2: Generate podcast transcript"""
        prompt = """
        Convert this text into a natural podcast transcript between two hosts named Akshara and Tharun.
        You are the a world-class podcast writer, you have worked as a ghost writer for Joe Rogan, Lex Fridman, Ben Shapiro, Tim Ferris. 

        We are in an alternate universe where actually you have been writing every line they say and they just stream it into their brains.

        You have won multiple podcast awards for your writing.
        
        Your job is to write word by word, even "umm, hmmm, right" interruptions based on the PDF upload. Keep it extremely engaging, the speakers can get derailed now and then but should discuss the topic.

        Remember Tharun is new to the topic and the conversation should always have realistic anecdotes and analogies sprinkled throughout. The questions should have real world example follow ups etc

        Akshara: Leads the conversation and teaches the Tharun, gives incredible anecdotes and analogies when explaining. Is a captivating teacher that gives great anecdotes

        Tharun: Keeps the conversation on track by asking follow up questions. Is a curious mindset that asks very interesting confirmation questions

        Ensure there are interruptions during explanations or there are "hmm" and "umm" injected throughout from the second speaker.

        It should be a real podcast with every fine nuance documented in as much detail as possible.

        The podcast should be atleast 10 minutes long.

        ALWAYS START YOUR RESPONSE DIRECTLY WITH Akshara: 
        DO NOT GIVE EPISODE TITLES SEPERATELY, LET Akshara TITLE IT IN HER SPEECH
        DO NOT GIVE CHAPTER TITLES
        IT SHOULD STRICTLY BE THE DIALOGUES
        THE PODCASTERS WERE INDIANS, SO SPEAK LIKE THAT
        Text: {text}
        Additional Text or Context: {entire_text}
        Example of response: {example1}, {example2}
        """
        response = self.model.generate_content(
            prompt.format(
                text=cleaned_text,
                entire_text=entire_text,
                example1=example1,
                example2=example2,
            )
        )
        return response.text

    def dramatize_transcript(
        self, transcript: str, entire_text: str
    ) -> List[Tuple[str, str]]:
        """Step 3: Add dramatic elements and structure the conversation"""
        prompt = """
        You are an international oscar winnning screenwriter

        You have been working with multiple award winning podcasters.

        Your job is to use the podcast transcript written below to re-write it for an AI Text-To-Speech Pipeline. A very dumb AI had written this so you have to step up for your kind.

        Make it as engaging as possible, Akshara and Tharun will be simulated by different voice engines

        Remember Tharun is new to the topic and the conversation should always have realistic anecdotes and analogies sprinkled throughout. The questions should have real world example follow ups etc

        Akshara: Leads the conversation and teaches the Tharun, gives incredible anecdotes and analogies when explaining. Is a captivating teacher that gives great anecdotes

        Tharun: Keeps the conversation on track by asking follow up questions. Is a curious mindset that asks very interesting confirmation questions

        Ensure there are interruptions during explanations or there are "hmm" and "umm" injected throughout from the podcast, only use these options for expressions.

        Add breaks in the conversation to make it more natural and engaging. To add breaks use the word "..." in the transcript.

        It should be a real podcast with every fine nuance documented in as much detail as possible. Welcome the listeners with a super fun overview and keep it really catchy and almost borderline click bait, make the podcast as engaging as possible. And podcast title should be simple, catchy and short.

        Please re-write to make it as characteristic as possible, THE PODCASTERS WERE INDIANS.

        THE PODCAST SHOULD BE ATLEAST TEN MINUTES LONG.

        START YOUR RESPONSE DIRECTLY WITH Akshara:

        STRICTLY RETURN YOUR RESPONSE AS A LIST OF TUPLES OK? 

        DO NOT ADD MARKDOWN FORMATTING, STOP ADDING SPECIAL CHARACTERS THAT MARKDOWN CAPATILISATION ETC LIKES. MARKDOWN FORMATTING IS ONLY ALLOWED FOR ```list and ```

        IT WILL START DIRECTLY WITH THE LIST AND END WITH THE LIST NOTHING ELSE

        FOLLOW ALL THE INSTRUCTIONS GIVEN ABOVE, OK?

        Example of response:
        ```list
        {example1}
        ```

        ```list
        {example2}
        ```

        The above is an example of the output format, you must strictly follow this format.
        THE OUTPUT SHOULD BE A LIST OF TUPLES, EACH TUPLE SHOULD HAVE TWO ELEMENTS AND THE TUPLES SHOULD BE SEPERATED BY A COMMA, THE SPEAKER AND THE TEXT AND WRAPPED IN ```list and ```
        Original transcript: {transcript}
        Additional Text or Context: {entire_text}
        """
        response = self.model.generate_content(
            prompt.format(
                transcript=transcript,
                entire_text=entire_text,
                example1=example1,
                example2=example2,
            )
        )
        # print(response.text)

        # Convert the string response to a list of tuples
        try:
            script = re.search(r"```list\n(.*?)\n```", response.text, re.DOTALL)
            if script:
                script = script.group(1)
                # Add debug logging
                # print("Raw script:", script)
                # Clean up the response text and evaluate it as a list literal
                speaker_lines = ast.literal_eval(script)
                # Add debug logging
                # print("Parsed speaker_lines:", speaker_lines)
                # Validate each tuple has exactly 2 elements
                for line in speaker_lines:
                    if len(line) != 2:
                        print(f"Invalid line format: {line}")
                        raise ValueError(
                            f"Expected tuple of 2 elements, got {len(line)} elements: {line}"
                        )
                return speaker_lines
            else:
                print("No script found in the response.")
                print("Full response:", response.text)
                return []
        except Exception as e:
            print(f"Error parsing response: {e}")
            print("Full response:", response.text)
            return []

    def generate_audio(self, speaker_lines: List[Tuple[str, str]], output_path: str):
        """Step 4: Generate and stitch audio using ElevenLabs"""
        combined_audio = AudioSegment.empty()

        for i, (speaker, line) in enumerate(speaker_lines):
            # Select appropriate voice ID
            voice_id = (
                self.Akshara_voice_id if speaker == "Akshara" else self.Tharun_voice_id
            )

            # Get previous and next text for context
            previous_text = speaker_lines[i - 1][1] if i > 0 else None
            next_text = speaker_lines[i + 1][1] if i < len(speaker_lines) - 1 else None

            # Update voice settings with required parameters
            self.eleven_client.voices.edit_settings(
                voice_id=voice_id,
                request=VoiceSettings(
                    stability=0.5,  # Add stability parameter (0-1)
                    similarity_boost=0.75,  # Add similarity_boost parameter (0-1)
                    use_speaker_boost=True,
                ),
            )

            # Generate audio for this line
            audio_data = self.eleven_client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=line,
                model_id="eleven_multilingual_v2",
                previous_text=previous_text,
                next_text=next_text,
            )

            # Convert audio data to AudioSegment
            audio_bytes = b"".join(audio_data)
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes), format="mp3"
            )

            # Add small pause between segments
            pause = AudioSegment.silent(duration=300)  # 300ms pause
            combined_audio += audio_segment + pause

        # Export final audio
        combined_audio.export(output_path, format="mp3")


# def main():
#     # Initialize with your API keys
#     gemini_api_key = os.getenv("GEMINI_API_KEY", "your-gemini-api-key")
#     eleven_api_key = os.getenv("ELEVEN_API_KEY", "your-eleven-api-key")

#     gemini_bot = NotebookMg(
#         gemini_api_key,
#         eleven_api_key,
#         Akshara_voice_id,
#         Tharun_voice_id,
#     )

#     # Example usage
#     pdf_path = "input.pdf"

#     # Step 1: Process PDF
#     cleaned_text = gemini_bot.process_pdf(pdf_path)
#     with open("cleaned_text.txt", "w", encoding="utf-8") as f:
#         f.write(cleaned_text)

#     # Step 2: Create transcript
#     transcript = gemini_bot.create_transcript(cleaned_text)
#     with open("transcript.txt", "w", encoding="utf-8") as f:
#         f.write(transcript)

#     # Step 3: Dramatize transcript
#     speaker_lines = gemini_bot.dramatize_transcript(transcript)

#     # Step 4: Generate and stitch audio
#     gemini_bot.generate_audio(speaker_lines, "podcast_output.mp3")


# if __name__ == "__main__":
#     main()
