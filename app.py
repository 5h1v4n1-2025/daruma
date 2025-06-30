from flask import Flask, request, send_file, render_template, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from io import BytesIO
import google.generativeai as genai
import wave
import tempfile
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log")],
)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Log startup information
logging.info("Starting application...")
logging.info("Checking API keys...")

ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ELEVENLABS_API_KEY:
    logging.error("ELEVEN_LABS_API_KEY not found in environment variables")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY not found in environment variables")

# Configure Gemini API
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    logging.info("Successfully configured Gemini API")
except Exception as e:
    logging.error(f"Error configuring Gemini API: {str(e)}")

# Configure CORS
CORS(app, resources={r"/generate-audio": {"origins": "http://localhost:5000"}})


def get_elevenlabs_voices():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"Accept": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["voices"]
    else:
        logging.error(f"Failed to get voices: {response.text}")
        return []


ELEVENLABS_VOICES = get_elevenlabs_voices()


def find_best_matching_voice(character_properties, elevenlabs_voices):
    best_match = None
    best_score = 0

    for voice in elevenlabs_voices:
        score = 0
        labels = voice.get("labels", {})

        if character_properties["gender"].lower() in labels.get("gender", "").lower():
            score += 1
        if character_properties["age"].lower() in labels.get("age", "").lower():
            score += 1
        if any(
            accent in labels.get("accent", "").lower()
            for accent in character_properties["accent"].lower().split()
        ):
            score += 1
        if character_properties["tone"].lower() in labels.get("style", "").lower():
            score += 1
        if character_properties["style"].lower() in labels.get("style", "").lower():
            score += 1

        if score > best_score:
            best_match = voice
            best_score = score

    return best_match["voice_id"] if best_match else elevenlabs_voices[0]["voice_id"]


def combine_audio_files(audio_files):
    """Combine multiple audio files into a single file"""
    if not audio_files:
        raise ValueError("No audio files to combine")

    logging.info(f"Combining {len(audio_files)} audio segments")

    try:
        # Create a temporary file for the combined audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as outfile:
            # Write the content of the first file
            with open(audio_files[0], "rb") as first_file:
                outfile.write(first_file.read())

            # Append the content of remaining files
            for audio_file in audio_files[1:]:
                with open(audio_file, "rb") as infile:
                    outfile.write(infile.read())

            logging.info(f"Successfully combined audio files into {outfile.name}")
            return outfile.name
    except Exception as e:
        logging.error(f"Error combining audio files: {str(e)}")
        raise


def generate_character_list(text):
    """Helper function to generate and validate character list from text"""
    try:
        gemini_prompt_characters = f"""
        Analyze the following text and identify the key characters, including the narrator. For each character, provide the following properties:

        - Gender
        - Age (young, middle-aged, elderly)
        - Accent (e.g., British, American, Australian)
        - Tone (e.g., formal, casual, excited)
        - Style (narrating or acting)
        - Urgency (low, medium, high)

        Make sure to include a narrator with the best properties for this text.
        
        Input Text:
        {text}

        Return ONLY the Python code below with your character analysis (no other text):
        [
            {{
                "name": "Character Name",
                "properties": {{
                    "gender": "Male/Female",
                    "age": "Young/Middle-aged/Elderly",
                    "accent": "British/American/Australian/etc",
                    "tone": "Formal/Casual/Excited/etc",
                    "style": "Narrating/Acting",
                    "urgency": "Low/Medium/High"
                }}
            }}
        ]
        """
        gemini_response_characters = model.generate_content(gemini_prompt_characters)
        response_text = gemini_response_characters.text.strip()

        # Log the raw response for debugging
        logging.info(f"Raw Gemini API Response: {response_text}")

        # Clean up the response text
        if "```python" in response_text:
            response_text = response_text.split("```python")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()

        # Remove any 'characters = ' prefix if present
        if "characters = " in response_text:
            response_text = response_text.split("characters = ")[1].strip()

        logging.info(f"Cleaned Response: {response_text}")

        try:
            # Safely evaluate the string as Python literal
            import ast

            characters = ast.literal_eval(response_text)

            # Validate the structure
            if not isinstance(characters, list):
                raise ValueError("Response is not a list")

            if len(characters) == 0:
                raise ValueError("No characters found in the text")

            # Validate each character's structure
            for char in characters:
                if not isinstance(char, dict):
                    raise ValueError("Character entry is not a dictionary")
                if "name" not in char:
                    raise ValueError("Character missing name field")
                if "properties" not in char:
                    raise ValueError("Character missing properties field")

                required_props = ["gender", "age", "accent", "tone", "style", "urgency"]
                props = char.get("properties", {})
                missing_props = [prop for prop in required_props if prop not in props]

                if missing_props:
                    # If properties are missing, set default values
                    for prop in missing_props:
                        if prop == "gender":
                            props[prop] = "Unknown"
                        elif prop == "age":
                            props[prop] = "Middle-aged"
                        elif prop == "accent":
                            props[prop] = "Neutral"
                        elif prop == "tone":
                            props[prop] = "Neutral"
                        elif prop == "style":
                            props[prop] = "Narrating"
                        elif prop == "urgency":
                            props[prop] = "Medium"
                    char["properties"] = props
                    logging.warning(
                        f"Added default properties for character {char['name']}: {missing_props}"
                    )

            logging.info(f"Successfully parsed {len(characters)} characters")
            return characters

        except Exception as e:
            logging.error(f"Error parsing character response: {str(e)}")
            # Create a default narrator if parsing fails
            default_narrator = [
                {
                    "name": "Narrator",
                    "properties": {
                        "gender": "Neutral",
                        "age": "Middle-aged",
                        "accent": "Neutral",
                        "tone": "Formal",
                        "style": "Narrating",
                        "urgency": "Medium",
                    },
                }
            ]
            logging.warning("Using default narrator due to parsing error")
            return default_narrator

    except Exception as e:
        logging.error(f"Error in character generation: {str(e)}")
        raise


def generate_script(text, characters):
    """Helper function to generate script from text and characters"""
    try:
        gemini_prompt_script = f"""
        Using the following character list, generate a complete script with added context for the story. Create suitable dialogues where they are missing. Lines that are not spoken by characters should be spoken by the narrator. Return ONLY a Python list containing dialogue entries (no other text).

        Characters:
        {characters}

        Story Text:
        {text}

        Return the script in this EXACT format (no other text):
        [
            {{
                "speaker_name": "Character Name",
                "speaker_text": "The text they speak",
                "voice_id": "voice_id_from_character"
            }}
        ]
        """

        gemini_response_script = model.generate_content(gemini_prompt_script)
        response_text = gemini_response_script.text.strip()

        # Log the raw response for debugging
        logging.info(f"Raw Script Response: {response_text}")

        # Clean up the response text
        if "```python" in response_text:
            response_text = response_text.split("```python")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()

        # Remove any script = prefix if present
        if "script = " in response_text:
            response_text = response_text.split("script = ")[1].strip()

        logging.info(f"Cleaned Script Response: {response_text}")

        try:
            # Safely evaluate the string as Python literal
            import ast

            script = ast.literal_eval(response_text)

            # Validate the structure
            if not isinstance(script, list):
                raise ValueError("Script response is not a list")

            if len(script) == 0:
                raise ValueError("No dialogue entries found in the script")

            # Validate each dialogue entry
            for entry in script:
                if not isinstance(entry, dict):
                    raise ValueError("Script entry is not a dictionary")

                required_fields = ["speaker_name", "speaker_text"]
                missing_fields = [
                    field for field in required_fields if field not in entry
                ]

                if missing_fields:
                    raise ValueError(
                        f"Script entry missing required fields: {missing_fields}"
                    )

                if not entry["speaker_text"].strip():
                    raise ValueError("Empty speaker text found in script")

            logging.info(f"Successfully parsed script with {len(script)} entries")
            return script

        except Exception as e:
            logging.error(f"Error parsing script response: {str(e)}")
            # Create a default script with the entire text as narration
            default_script = [
                {
                    "speaker_name": "Narrator",
                    "speaker_text": text,
                    "voice_id": None,  # Will be assigned later
                }
            ]
            logging.warning("Using default script due to parsing error")
            return default_script

    except Exception as e:
        logging.error(f"Error in script generation: {str(e)}")
        raise


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    # log that we are receiving a request
    logging.info("Received a request for audio generation")
    try:
        # Validate input
        if not request.is_json:
            return {"error": "Request must be JSON"}, 400
        text = request.json.get("text")
        if not text:
            return {"error": "Text is required"}, 400

        logging.info(f"Starting audio generation for text: {text[:100]}...")

        # Step 1: Generate character list with properties
        logging.info("Step 1: Generating character list with Gemini API")
        try:
            characters = generate_character_list(text)
        except Exception as e:
            return {"error": f"Failed to analyze text characters: {str(e)}"}, 500

        # Step 2: Assign voice IDs to characters
        logging.info("Step 2: Assigning voice IDs to characters")
        try:
            for character in characters:
                character["voice_id"] = find_best_matching_voice(
                    character["properties"], ELEVENLABS_VOICES
                )
                logging.info(
                    f"Assigned voice {character['voice_id']} to character {character['name']}"
                )
        except Exception as e:
            return {"error": f"Failed to assign voices: {str(e)}"}, 500

        # Step 3: Generate script
        logging.info("Step 3: Generating script with Gemini API")
        try:
            script = generate_script(text, characters)
        except Exception as e:
            return {"error": f"Failed to generate script: {str(e)}"}, 500

        # Step 4: Generate audio for each script entry
        logging.info("Step 4: Generating audio segments")
        audio_files = []
        for i, entry in enumerate(script):
            try:
                logging.info(f"\nGenerating audio for segment {i+1}/{len(script)}")
                logging.info(f"Character: {entry['speaker_name']}")
                logging.info(f"Text: {entry['speaker_text'][:50]}...")

                # Find the character's voice_id
                voice_id = next(
                    (
                        char["voice_id"]
                        for char in characters
                        if char["name"] == entry["speaker_name"]
                    ),
                    characters[0]["voice_id"],  # fallback to first character's voice
                )

                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY,
                }

                data = {
                    "text": entry["speaker_text"],
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5,
                        "style": 0,
                    },
                }

                response = requests.post(url, json=data, headers=headers)

                if response.status_code == 200:
                    # Save the audio segment to a temporary file
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp3", delete=False
                    ) as temp_file:
                        temp_file.write(response.content)
                        audio_files.append(temp_file.name)
                    logging.info(f"Successfully generated audio segment {i+1}")
                else:
                    error_msg = (
                        f"ElevenLabs API error for segment {i+1}: {response.text}"
                    )
                    logging.error(error_msg)
                    return {"error": error_msg}, response.status_code

            except Exception as e:
                error_msg = f"Error generating audio segment {i+1}: {str(e)}"
                logging.error(error_msg)
                return {"error": error_msg}, 500

        # Step 5: Combine audio files
        logging.info("Step 5: Combining audio segments")
        try:
            combined_audio_path = combine_audio_files(audio_files)
            logging.info("Successfully combined all audio segments")

            return send_file(
                combined_audio_path,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name="generated_audio.mp3",
            )

        except Exception as e:
            logging.error(f"Error combining audio files: {str(e)}")
            return {"error": f"Failed to combine audio files: {str(e)}"}, 500

    except Exception as e:
        logging.error(f"Unexpected error in generate_audio: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}, 500


if __name__ == "__main__":
    app.run(debug=True)
