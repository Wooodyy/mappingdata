# MappingData

MappingData is a lightweight web application that extracts and visualizes data from Excel and PDF files for customs declarations.

## Demo
Check the live version here: [mappingdata.vercel.app](https://mappingdata.vercel.app)

## Features
- Upload Excel or PDF documents.
- Process data using pre-configured algorithms.
- View parsed data as a table on the frontend.
- Easy extension: add new processors under `processors/`.

## Project Structure
```

mappingdata/
├── api/               # API routes if any
├── data/              # Sample or uploaded files
├── processors/        # Logic for parsing files (Excel, PDF, etc.)
├── templates/         # HTML templates for frontend rendering
├── main.py            # FastAPI application entrypoint
├── models.py          # Pydantic models or data structures
├── requirements.txt   # Python dependencies
└── render.yaml        # Deploy configuration for Render.com

````

## Tech Stack
- **Backend**: FastAPI + Uvicorn  
- **Frontend**: Jinja2 templates  
- **Deployment**: Render with automatic Docker build via `render.yaml`  

## Usage

1. Clone the repo:
    ```bash
    git clone https://github.com/Wooodyy/mappingdata.git
    cd mappingdata
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Run the app:
    ```bash
    uvicorn main:app --reload
    ```

4. Open your browser at `http://127.0.0.1:8000` and upload a file.

## Contributing
Want to add more processors (e.g., for different Excel formats or PDF layouts)?  
Simply create a new module in `processors/`, register it in `processors/__init__.py`, and add its name to the upload UI picker.

## License
Licensed under the MIT License.

