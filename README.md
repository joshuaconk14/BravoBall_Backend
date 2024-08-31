# TekkAI Soccer App

TekkAI is an intelligent soccer coaching application that leverages the power of the Llama3 model to provide personalized tutorials and advice to soccer enthusiasts. The app uses FastAPI to create an API that interacts with a pre-trained Llama3 model, maintaining a stateful conversation with users to deliver context-aware responses.

## Features

- **Contextual Soccer Coaching:** TekkAI remembers the context of your conversation and provides relevant soccer advice based on your inputs.
- **Stateful Conversations:** The app uses an in-memory store to maintain the history of conversations, ensuring that each interaction builds on the last.
- **NVIDIA-Powered Llama3 Model:** The app integrates with the Llama3 model via NVIDIA's API to deliver high-quality, instructional content.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- NVIDIA API key for accessing the Llama3 model

### Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/tekkai-soccer-app.git
    cd tekkai-soccer-app
    ```

2. **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install the Required Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables:**
   - Set your NVIDIA API key as an environment variable. This key is required to interact with the Llama3 model.
   ```bash
   export NVAPI_KEY="your_nvapi_key"  # On Windows, use `set NVAPI_KEY=your_nvapi_key`
    ```

5. **Start the FastAPI Server Locally:**
    ```bash
    uvicorn main:app --reload
    ```

6. **Access the API:**

    - Once the server is running, you can interact with the API using tools like curl, Postman, or directly from a frontend application. Follow my frontend guide to use on XCode:
    ```bash
    https://github.com/jordanconklin/Tekk_frontend.git
    ```
    - The main endpoint available is /generate_tutorial/, which processes user input and generates soccer tutorials based on the Llama3 model.
    - For Swagger UI:
    ```bash
    http://127.0.0.1:8000/docs
    ```