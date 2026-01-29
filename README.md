# BG Remover Pro

Professional tool for automatic background removal from photos, optimized for objects with fine details (e.g., weapons, accessories). It utilizes the state-of-the-art **BiRefNet** AI model.

## Key Features
- **Privacy**: All processing is done locally on your computer.
- **BiRefNet Model**: Exceptional precision in detecting gaps (e.g., in weapon straps) and maintaining sharp edges.
- **Batch Processing**: Ability to upload multiple photos simultaneously with performance optimization (parallel processing).
- **Built-in Editor**: Basic cropping and rotation functions before and after background removal.
- **Modern UI**: Aesthetic and responsive user interface.

## Requirements
- Python 3.12 (tested on version 3.12.12)
- Virtual environment (recommended)

## Installation

1. Clone the repository or download the project files.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - **MacOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
4. Install required libraries:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

To run the application in development mode (with auto-reload):

```bash
python -m uvicorn app:app --reload --port 8001
```

The application will be available at: [http://127.0.0.1:8001](http://127.0.0.1:8001)

## Technologies
- **Backend**: FastAPI, Uvicorn
- **AI**: Rembg (BiRefNet engine)
- **Frontend**: Tailwind CSS, Cropper.js, JavaScript (Vanilla)
