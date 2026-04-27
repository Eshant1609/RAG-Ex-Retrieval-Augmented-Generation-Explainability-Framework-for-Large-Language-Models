# Local Run Instructions

## Prerequisites

- Python 3.11
- Node.js 16+ and npm
- Ollama installed

## 1. Backend Setup

```bash
cd backend
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

## 2. Frontend Setup

```bash
cd frontend
npm install
```

## 3. Start Ollama

```bash
ollama serve
```

In another terminal, pull/check model (default backend model is `llama3.2`):

```bash
ollama pull llama3.2
ollama list
```

## 4. Run Backend

```bash
cd backend
python app.py
```

Backend URL: `http://localhost:5511`

## 5. Run Frontend

```bash
cd frontend
npm start
```

Frontend URL: `http://localhost:3311`

## 6. Open App

- Visit `http://localhost:3311`
