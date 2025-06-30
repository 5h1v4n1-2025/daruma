# daruma: AI-Powered Text-to-Speech Application

Daruma is a Flask-based web application that converts text into natural-sounding speech using AI technologies. It leverages Google's Gemini AI for character analysis and Eleven Labs for high-quality voice synthesis.

## Features

- **Intelligent Character Analysis**: Automatically identifies characters and their properties from input text using Google's Gemini AI
- **Dynamic Voice Assignment**: Matches characters with appropriate voices based on their characteristics
- **Multi-Character Speech Generation**: Generates distinct voices for different characters in the text
- **Audio Concatenation**: Combines multiple audio segments into a cohesive narrative
- **Error Handling**: Robust error handling and logging throughout the application

## Prerequisites

- Python 3.x
- Eleven Labs API key
- Google Gemini API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pringlesinghal/daruma.git
cd daruma
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your API keys:
```
ELEVEN_LABS_API_KEY=your_eleven_labs_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Enter your text in the input field and click "Generate Audio"

4. The application will:
   - Analyze the text for characters
   - Generate appropriate voices for each character
   - Create audio segments
   - Combine them into a single audio file
   - Download the final audio file

## Technical Details

- **Frontend**: HTML/JavaScript
- **Backend**: Flask (Python)
- **APIs**:
  - Google Gemini AI for text analysis
  - Eleven Labs for text-to-speech conversion

## Error Handling

The application includes comprehensive error handling:
- Input validation
- API response validation
- Audio processing error handling
- Fallback to default narrator when needed

## Logging

Detailed logging is implemented throughout the application:
- API responses
- Processing steps
- Error messages
- Audio generation status

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Eleven Labs](https://elevenlabs.io/) for the text-to-speech API
- [Google Gemini](https://ai.google.dev/) for the AI text analysis
- Flask team for the web framework
