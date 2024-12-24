import google.generativeai as genai
import PyPDF2
import os
from pathlib import Path
from typing import Tuple, List
import json
import re
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import io
from dotenv import load_dotenv
import ast

load_dotenv()


class NotebookMg:
    def __init__(
        self,
        gemini_api_key: str,
        eleven_api_key: str,
        Tharun_voice_id: str,
        Monica_voice_id: str,
    ):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.eleven_client = ElevenLabs(api_key=eleven_api_key)

        # Use provided voice IDs or fall back to defaults
        self.Tharun_voice_id = Tharun_voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.Monica_voice_id = Monica_voice_id or "IKne3meq5aSn9XLyUdCD"

    def process_pdf(self, pdf_path: str) -> str:
        """Step 1: PDF Pre-processing"""
        text = ""
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()

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

        THE TEXT IS NOT A TRANSCRIPT, IT IS A PDF, SO YOU MUST CLEAN IT UP AND RE-WRITE WHEN NEEDED. 
        
        THE PODCAST SHOULD BE ATLEAST FIFTEEN MINUTES LONG.

        ALSO REASON ABOUT THE CHANGES YOU MADE TO THE TEXT. Output should be in JSON format

        OUTPUT FORMAT: 
        ```json
        
            "text": "processed text",
            "reasoning": "reasoning for the changes you made"
        
        ```
        Here is the text: {text}
        """
        response = self.model.generate_content(prompt.format(text=text))
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

    def create_transcript(self, cleaned_text: str) -> str:
        """Step 2: Generate podcast transcript"""
        prompt = """
        Convert this text into a natural podcast transcript between two hosts named Tharun and Monica.
        You are the a world-class podcast writer, you have worked as a ghost writer for Joe Rogan, Lex Fridman, Ben Shapiro, Tim Ferris. 

        We are in an alternate universe where actually you have been writing every line they say and they just stream it into their brains.

        You have won multiple podcast awards for your writing.
        
        Your job is to write word by word, even "umm, hmmm, right" interruptions by the second speaker based on the PDF upload. Keep it extremely engaging, the speakers can get derailed now and then but should discuss the topic.

        Remember Monica is new to the topic and the conversation should always have realistic anecdotes and analogies sprinkled throughout. The questions should have real world example follow ups etc

        Tharun: Leads the conversation and teaches the Monica, gives incredible anecdotes and analogies when explaining. Is a captivating teacher that gives great anecdotes

        Monica: Keeps the conversation on track by asking follow up questions. Gets super excited or confused when asking questions. Is a curious mindset that asks very interesting confirmation questions

        Make sure the tangents Monica provides are quite wild or interesting. 

        Ensure there are interruptions during explanations or there are "hmm" and "umm" injected throughout from the second speaker.

        It should be a real podcast with every fine nuance documented in as much detail as possible. Welcome the listeners with a super fun overview and keep it really catchy and almost borderline click bait

        ALWAYS START YOUR RESPONSE DIRECTLY WITH Tharun: 
        DO NOT GIVE EPISODE TITLES SEPERATELY, LET Tharun TITLE IT IN HER SPEECH
        DO NOT GIVE CHAPTER TITLES
        IT SHOULD STRICTLY BE THE DIALOGUES
        THE PODCASTERS WERE INDIANS, SO SPEAK LIKE THAT
        Text: {text}
        """
        response = self.model.generate_content(prompt.format(text=cleaned_text))
        return response.text

    def dramatize_transcript(self, transcript: str) -> List[Tuple[str, str]]:
        """Step 3: Add dramatic elements and structure the conversation"""
        prompt = """
        You are an international oscar winnning screenwriter

        You have been working with multiple award winning podcasters.

        Your job is to use the podcast transcript written below to re-write it for an AI Text-To-Speech Pipeline. A very dumb AI had written this so you have to step up for your kind.

        Make it as engaging as possible, Tharun and 2 will be simulated by different voice engines

        Remember Monica is new to the topic and the conversation should always have realistic anecdotes and analogies sprinkled throughout. The questions should have real world example follow ups etc

        Tharun: Leads the conversation and teaches the Monica, gives incredible anecdotes and analogies when explaining. Is a captivating teacher that gives great anecdotes

        Monica: Keeps the conversation on track by asking follow up questions. Gets super excited or confused when asking questions. Is a curious mindset that asks very interesting confirmation questions

        Make sure the tangents Monica provides are quite wild or interesting. 

        Ensure there are interruptions during explanations or there are "hmm" and "umm" injected throughout from the Monica.

        REMEMBER THIS WITH YOUR HEART
        The TTS Engine for Tharun cannot do "umms, hmms" well so keep it straight text

        For Monica use "umm, hmm" as much, you can also use [sigh] and [laughs]. BUT ONLY THESE OPTIONS FOR EXPRESSIONS

        It should be a real podcast with every fine nuance documented in as much detail as possible. Welcome the listeners with a super fun overview and keep it really catchy and almost borderline click bait

        Please re-write to make it as characteristic as possible, THE PODCASTERS WERE INDIANS, SO SPEAK LIKE THAT, use indian accents and words

        THE PODCAST SHOULD BE ATLEAST FIFTEEN MINUTES LONG.

        START YOUR RESPONSE DIRECTLY WITH Tharun:

        STRICTLY RETURN YOUR RESPONSE AS A LIST OF TUPLES OK? 

        IT WILL START DIRECTLY WITH THE LIST AND END WITH THE LIST NOTHING ELSE

        Example of response:
        ```python
        [
            ("Tharun", "Welcome to our podcast, where we explore the latest advancements in AI and technology. I'm your host, and today we're joined by a renowned expert in the field of AI. We're going to dive into the exciting world of Llama 3.2, the latest release from Meta AI."),
            ("Monica", "Hi, I'm excited to be here! So, what is Llama 3.2?"),
            ("Tharun", "Ah, great question! Llama 3.2 is an open-source AI model that allows developers to fine-tune, distill, and deploy AI models anywhere. It's a significant update from the previous version, with improved performance, efficiency, and customization options."),
            ("Monica", "That sounds amazing! What are some of the key features of Llama 3.2?")
        ]
        ```
        The above is an example of the output format, you must strictly follow this format.
        Original transcript: {transcript}
        """
        response = self.model.generate_content(prompt.format(transcript=transcript))
        # print(response.text)

        # Convert the string response to a list of tuples
        try:
            script = re.search(r"```python\n(.*?)\n```", response.text, re.DOTALL)
            if script:
                script = script.group(1)
                # Clean up the response text and evaluate it as a Python literal
                speaker_lines = ast.literal_eval(script)
                # for speaker, text in speaker_lines:
                #     print(f"{speaker}: {text}")
                return speaker_lines
            else:
                print("No script found in the response.")
                return []
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []

    def generate_audio(self, speaker_lines: List[Tuple[str, str]], output_path: str):
        """Step 4: Generate and stitch audio using ElevenLabs"""
        combined_audio = AudioSegment.empty()

        for speaker, line in speaker_lines:
            # Select appropriate voice ID
            voice_id = (
                self.Tharun_voice_id if speaker == "Tharun" else self.Monica_voice_id
            )

            # Generate audio for this line
            audio_data = self.eleven_client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=line,
                model_id="eleven_multilingual_v2",
            )

            # Convert audio data to AudioSegment
            audio_bytes = b"".join(audio_data)  # Convert iterator to bytes
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes), format="mp3"
            )

            # Add small pause between segments
            pause = AudioSegment.silent(duration=500)  # 500ms pause
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
#         Tharun_voice_id,
#         Monica_voice_id,
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
