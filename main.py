import google.generativeai as genai
import PyPDF2
import os
from pathlib import Path
from typing import Tuple, List, Optional
import json
import re
from elevenlabs import ElevenLabs, VoiceSettings
from pydub import AudioSegment
import io
from dotenv import load_dotenv
import ast
from examples import example1, example2
from google.generativeai.types.file_types import File as GeminiFile

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
        self.model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")
        self.eleven_client = ElevenLabs(api_key=eleven_api_key)

        # Use provided voice IDs or fall back to defaults
        self.Akshara_voice_id = Akshara_voice_id or "21m00Tcm4TlvDq8ikWAM"
        self.Tharun_voice_id = Tharun_voice_id or "IKne3meq5aSn9XLyUdCD"

    def upload_to_gemini(
        self, path: Path, mime_type: Optional[str] = None
    ) -> GeminiFile:
        """Uploads file to Gemini."""
        try:
            file = genai.upload_file(path, mime_type=mime_type)
            print(f"Uploaded file '{file.display_name}' to Gemini")
            return file
        except Exception as e:
            print(f"Error uploading file to Gemini: {str(e)}")
            raise

    # def get_pdf_text(self, pdf_path: str) -> str:
    #     text = ""
    #     with open(pdf_path, "rb") as file:
    #         pdf_reader = PyPDF2.PdfReader(file)
    #         for page in pdf_reader.pages:
    #             text += page.extract_text()
    #     return text

    # def process_pdf(self, text: str) -> str:
    #     """Step 1: PDF Pre-processing"""

    #     # Clean up the text using Gemini
    #     prompt = """
    #     You are a world class text pre-processor, here is the raw data from a PDF, please parse and return it in a way that is crispy and usable to send to a podcast writer.

    #     The raw data is messed up with new lines, Latex math and you will see fluff that we can remove completely. Basically take away any details that you think might be useless in a podcast author's transcript.

    #     Remember, the podcast could be on any topic whatsoever so the issues listed above are not exhaustive

    #     Please be smart with what you remove and be creative ok?

    #     Remember DO NOT START SUMMARIZING THIS, YOU ARE ONLY CLEANING UP THE TEXT AND RE-WRITING WHEN NEEDED

    #     Be very smart and aggressive with removing details, you will get a running portion of the text and keep returning the processed text.

    #     PLEASE DO NOT ADD MARKDOWN FORMATTING, STOP ADDING SPECIAL CHARACTERS THAT MARKDOWN CAPATILISATION ETC LIKES

    #     ALWAYS start your response directly with processed text and NO ACKNOWLEDGEMENTS about my questions ok?

    #     PLEASE DO NOT REMOVE ANYTHING FROM THE TEXT, JUST CLEAN IT UP.

    #     DO NOT SUMMARIZE OR BRIEF THE TEXT, JUST CLEAN IT UP AND RE-WRITE WHEN NEEDED.

    #     THE PODCAST SHOULD BE ATLEAST TEN MINUTES LONG.

    #     ALSO REASON ABOUT THE CHANGES YOU MADE TO THE TEXT. Output should be in JSON format

    #     OUTPUT FORMAT:
    #     ```json

    #         "text": "processed text",
    #         "reasoning": "reasoning for the changes you made"

    #     ```
    #     Here is the text: {text}
    #     """
    #     response = self.model.generate_content(prompt.format(text=text))
    #     print(response.text)
    #     # First try to find JSON within code blocks
    #     match = re.search(r"```(?:json)?\n(.*?)\n```", response.text, re.DOTALL)
    #     if match:
    #         json_str = match.group(1)
    #     else:
    #         # If no code blocks found, try to parse the entire response
    #         json_str = response.text
    #     pre_processed_text = json.loads(json_str)["text"]
    #     reasoning = json.loads(json_str)["reasoning"]
    #     print(f"Reasoning: {reasoning}")
    #     return pre_processed_text

    def create_transcript(self, pdf_file: GeminiFile) -> str:
        """Step 2: Generate podcast transcript"""
        prompt = """
                ROLE: You are a legendary podcast ghostwriter who has secretly crafted the most iconic episodes for Joe Rogan, Lex Fridman, Ben Shapiro, and Tim Ferriss. Your writing has shaped modern podcast culture, earning multiple awards for natural dialogue and engaging narratives.

                TASK: Transform PDF content into an authentic podcast conversation between two hosts:

                1. Akshara (Lead Host):
                - Expert voice with deep subject knowledge
                - Masterfully explains complex topics through:
                * Vivid personal anecdotes
                * Relatable real-world analogies
                * Unexpected connections
                - Teaching style combines authority with approachability
                - Occasionally goes on fascinating tangents before returning to core points

                2. Tharun (Co-host/Learner):
                - Represents the audience perspective
                - Interrupts with thoughtful clarifications
                - Uses natural reaction sounds:
                * "hmm" (processing new information)
                * "ahh" (realization moments)
                * "right" (understanding)
                * "interesting" (engagement)
                - Asks follow-up questions that deepen understanding
                - Brings discussions back to main topic when needed

                CONVERSATION REQUIREMENTS:
                - Minimum 2 to 3 minute dialogue length. Maximum 5 minutes
                - The transcript should atleast have 200 words, maximum 250 words
                - Title announced naturally within Akshara's opening
                - Do not start the podcast abruptly, start with a natural conversation, then gradually build up to the title, check the examples for reference
                - Organic flow with:
                * Natural interruptions
                * Brief tangents
                * Thinking pauses ("...")
                * Reaction sounds
                * Clarification requests
                - Keep individual speaking turns concise
                - Include both hosts' personalities in every exchange
                - Weave in relevant cultural references

                FORMAT:
                - Start directly with "Akshara:" 
                - Present as continuous dialogue
                - No separate titles or chapters
                - No formatting except speaker names
                - Natural conversation markers only

                OUTPUT:
                Akshara: [dialogue]
                Tharun: [dialogue]
                [Continue alternating naturally]

                Here are some examples of how you should format the dialogue:
                ```list
                {example1} 
                ```

                ```list
                {example2}
                ```

                Input: 
                """
        response = self.model.generate_content(
            [
                prompt.format(
                    example1=example1,
                    example2=example2,
                ),
                pdf_file,
            ]
        )
        return response.text

    def dramatize_transcript(self, transcript: str) -> List[Tuple[str, str]]:
        """Step 3: Add dramatic elements and structure the conversation"""
        prompt = """
                    You are an Academy Award-winning screenwriter specializing in natural dialogue and compelling narratives. Your expertise spans across film, television, and podcasting, where you've collaborated with top-tier creators worldwide.

                    ROLE AND OBJECTIVE:
                    - Transform the provided transcript into an engaging podcast dialogue optimized for AI Text-to-Speech systems
                    - Ensure the content is educational yet conversational

                    CHARACTERS:

                    1. Akshara (Host/Expert):
                    - 32-year-old Bangalore native, lived in US for 5 years
                    - PhD in topic but speaks casually
                    - Shares personal failures openly
                    - Warm, articulate educator with expertise in the subject
                    - Uses relatable analogies and real-world examples
                    - Naturally weaves in personal experiences and case studies
                    - Sometimes forgets technical terms
                    - Uses brief pauses for emphasis and clarity
                    - Says "you know what I mean?" after complex points

                    2. Tharun (Co-host/Learner):
                    - 28-year-old from Hyderabad, India
                    - Represents the audience's perspective
                    - Asks insightful follow-up questions
                    - Helps break down complex concepts
                    - Rapid-fire questions when interested
                    - Uses "right" and "interesting" to show engagement
                    - Uses "correct ah?" for confirmation
                    - Marketing background brings fresh perspective
                    - Interrupts with real-life examples
                    - Makes pop culture references
                    - Uses thinking sounds to show processing of information

                    DIALOGUE FORMATTING:
                        - Use natural conversation markers:
                            * Pauses: "..."
                            * Thinking sounds: "hmm", "umm"
                            * Reactions: "ah", "right", "okay", "interesting"
                            * For emotion: </happy>, </sad>, </excited>, </angry>, </surprised>, </disgusted>, </anxious>, </neutral>, etc.
                            * Interruptions: [marked with appropriate timing]
                        - Use filler words.
                        - Keep individual speaking turns concise (2-4 sentences maximum)
                        - Include comfortable silences between exchanges, the pauses can be irregular
                        - Can repeat the words in the dialogue to make it more natural
                        - Each speaker should have a unique voice, do not make them sound the same
                        - The conversation should be engaging and interesting, do not make it boring
                        - The conversation should not sound like a script or series of questions or a sales pitch, it should sound like a real conversation
                        - Maintain authenticity with Indian English phrasing and expressions
                        - Use a conversational tone, concise language and avoid unnecessarily complex jargon.
                        - Use short punchy sentences. Example: "And... you enter the room. Your heart drops. The pressure is on."
                        - Use simple language. 10th grade readability or lower. Example: "Emails help businesses tell customers about their stuff."
                        - Use rhetorical fragments to improve readability. Example: "The good news? My 3-step process can be applied to any business"
                        - Use analogies or examples often. Example: "Creating an email course with Al is easier than stealing candies from a baby"
                        - Split up long sentences. Example: "Even if you make your clients an offer they decline..[break..you shouldn't give up on the deal."
                        - Include personal anecdotes. Example: "I recently asked ChatGPT to write me...
                        - Use bold and italic formatting to emphasize words.
                        - Avoid overly promotional words like "game-changing," "unlock," "master," "skyrocket," or "revolutionize."
                        - Do not over use adjectives, adverbs and other words that are not necessary.
                        - Need not to address the speaker by name, just speak naturally.
                        - Avoid AI-giveaway phrases: Don't use clichés like "dive into," "unleash your potential," etc.
                        - Avoid: "Let's dive into this game-changing solution. instead use: "Here's how it works."
                        - Keep it real: Be honest; don't force friendliness. Example: "I don't think that's the best idea."
                        - Simplify grammar: Don't stress about perfect grammar; it's fine not to capitalize "i" if that's your style. Example: "i guess we can try that."


                    INTERACTION DYNAMICS:

                    - Friendly banter
                    - Complete each other's sentences
                    - Debate respectfully
                    - Share city rivalry jokes
                    - Reference shared memories
                    - Get sidetracked with stories
                    - Help each other with tech issues

                    STRUCTURAL REQUIREMENTS:
                        - Minimum length: 2 to 3 minutes of podcast, maximum 5 minutes
                        - The podcast should be atleast 200 words, maximum 250 words
                        - Opening: Catchy, borderline clickbait introduction
                        - Title: Short, memorable, curiosity-driving
                        - Natural topic progression with clear learning outcomes
                        - Regular engagement points for listener retention

                    OUTPUT FORMAT:

                        ```list
                        [("Speaker", "Dialogue")]
                        ```
                    - Each dialogue entry must be a tuple
                    - Strict list format without additional formatting
                    - No markdown except for the list wrapper
                    - Direct start with Akshara's opening line

                    QUALITY GUIDELINES:
                    - Authenticity:
                    - Natural speech patterns
                    - Realistic hesitations
                    - Conversational flow

                    Engagement:
                    - Regular curiosity hooks
                    - Relatable examples
                    - Clear explanations

                    Here are some examples of how you should format the dialogue:
                    
                    ```list
                    {example1} 
                    ```

                    ```list
                    {example2}
                    ```

                    Input: {transcript}

        """
        response = self.model.generate_content(
            prompt.format(
                transcript=transcript,
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
                model_id="eleven_turbo_v2_5",
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
#         Akshara_voice_id="21m00Tcm4TlvDq8ikWAM",
#         Tharun_voice_id="IKne3meq5aSn9XLyUdCD",
#     )

#     # Example usage
#     pdf_path = "input.pdf"

#     # Step 1: Process PDF
#     # cleaned_text = gemini_bot.process_pdf(pdf_path)
#     # with open("cleaned_text.txt", "w", encoding="utf-8") as f:
#     #     f.write(cleaned_text)
#     pdf_file = gemini_bot.upload_to_gemini(Path(pdf_path))

#     # Step 2: Create transcript
#     transcript = gemini_bot.create_transcript(pdf_file)
#     with open("transcript.txt", "w", encoding="utf-8") as f:
#         f.write(transcript)

#     # Step 3: Dramatize transcript
#     speaker_lines = gemini_bot.dramatize_transcript(transcript)
#     with open("final_transcript.txt", "w", encoding="utf-8") as f:
#         f.write(str(speaker_lines))

#     # Step 4: Generate and stitch audio
#     # gemini_bot.generate_audio(speaker_lines, "podcast_output.mp3")


# if __name__ == "__main__":
#     main()
