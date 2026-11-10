# UG-Scripts (AI UGC Script Writer)

Script Assistant is an AI-powered UGC (User-Generated Content) video ad script generator inspired by platforms like Billo. Given a single product photo and basic product information, it generates three distinct, phone-ready creator scripts tailored to auto-generated customer segments, backed by verifiable packaging facts and psychological reasoning.

---

## The Concept

Direct-to-consumer (DTC) brands and UGC creators spend hours brainstorming hooks, identifying customer pain points, and pacing video ads for TikTok, Instagram Reels, and YouTube Shorts.

Script Assistant automates this creative workflow through a two-stage generative AI pipeline:

1. **Packaging Analysis & Verifiable Claims**: Evaluates the product photo alongside the product description to extract 5–8 verifiable facts (e.g., active ingredients, packaging format, cruelty-free claims). This prevents model hallucinations and ensures creator claims adhere to what the packaging actually states.
2. **Customer Segmentation**: Auto-generates three distinct customer personas tailored to the target market and product category, identifying their core pain points, demographics, and high-performing social platforms.
3. **Paced, Persuasive UGC Scripts**: Concurrently drafts three production-ready video scripts—one per segment—employing dedicated hook styles (Curiosity Question, Problem Callout, Demo / Before-After). Each script includes:
   - Second-by-second pacing calibrated to natural creator speech (~2.5 spoken words per second).
   - A strict 3-second hook window indicator to evaluate scroll-stopping potential.
   - Persuasion technique rationales explaining why specific lines are structured to convert.

---

## Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Creator as User / Creator
    participant Web as React Web App
    participant API as FastAPI Backend
    participant Vertex as Gemini 3.5 Flash (Vertex AI)

    Creator->>Web: Input product info & upload photo
    Web->>API: POST /generate-stream (Multipart Form + X-API-Key)
    Note over Web: Status: Loading (0-4s)
    API->>Vertex: Stage 1: Multimodal analysis (Image + Details)
    Vertex-->>API: Facts + 3 Customer Segments (~4s)
    API-->>Web: SSE Event: 'segments'
    Note over Web: Status: Streaming<br/>Staggered reveal of Facts & Segment tabs
    par Parallel Script Generation
        API->>Vertex: Script 1 (Curiosity Hook)
        API->>Vertex: Script 2 (Problem Callout Hook)
        API->>Vertex: Script 3 (Demo Hook)
    and Progressive Delivery
        Vertex-->>API: Script 1 ready
        API-->>Web: SSE Event: 'script' (index 0)
        Note over Web: Tab 1 unlocks interactive ScriptCard
        Vertex-->>API: Script 2 ready
        API-->>Web: SSE Event: 'script' (index 1)
        Note over Web: Tab 2 unlocks
        Vertex-->>API: Script 3 ready
        API-->>Web: SSE Event: 'script' (index 2)
        Note over Web: Tab 3 unlocks
    end
    API-->>Web: SSE Event: 'done'
    Note over Web: Status: Success (All scripts ready)
```

### Key Technical Pillars
- **FastAPI & Async Streaming**: The backend uses Starlette's `StreamingResponse` over Server-Sent Events (`text/event-stream`). Proxy buffering is disabled via `X-Accel-Buffering: no` and `Cache-Control: no-cache`.
- **Parallel LLM Execution**: Stage 2 executes concurrent script calls via `asyncio.create_task` and yields each script chunk as soon as it resolves using `asyncio.as_completed`.
- **Progressive Frontend Hydration**: The frontend hook reads the SSE `ReadableStream` via `TextDecoder` without external stream parsing libraries, staging UI elements progressively so users never face a blank waiting screen.
- **Contract-Driven Type Safety**: FastAPI exports an OpenAPI 3.1 specification, which is compiled into TypeScript interfaces using `openapi-typescript`, guaranteeing zero drift between frontend contracts and backend schemas.

---

## Setup & Getting Started

### Prerequisites
- **[Bun](https://bun.sh/)** (v1.2+)
- **[Python](https://www.python.org/)** (v3.11+)
- **Google Cloud Project** with the Vertex AI API enabled and billing linked.

---

### 1. Clone the Repository and Install Dependencies

```bash
git clone <repository-url>
cd ug-script-writer
bun install
```

---

### 2. Configure the Python Backend

Create and activate a virtual environment inside the API service, then install requirements:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

---

### 3. Configure Environment Variables

#### Root Configuration (`.env`)
Create a `.env` file in the project root by copying `.env.example`:

```bash
cp .env.example .env
```

Configure your parameters:
```env
# Google Cloud Vertex AI & Firestore Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-3.5-flash

# Shared Secret API Key for client authorization & admin bypass
API_KEY=your-secure-random-api-key

# Optional: CORS allowed origins (comma-separated, defaults to localhost:5173)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://localhost:8080

# Service Port
PORT=8080
```

Authenticate your local environment with Google Cloud Application Default Credentials (ADC):
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project your-gcp-project-id
```

#### Frontend Local Dev Override (`apps/web/.env.local`)
When running `vite dev` against an external API server:

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your-secure-random-api-key
```

---

### 4. Running the Development Servers

Start both services locally:

**Terminal 1 — Backend (FastAPI)**:
```bash
cd apps/api
.venv/bin/uvicorn main:app --reload --port 8000
```
*API documentation and Swagger UI will be available at [http://localhost:8000/docs](http://localhost:8000/docs).*

**Terminal 2 — Frontend (Vite + React)**:
```bash
bun run dev:web
```
*The web application will open at [http://localhost:5173](http://localhost:5173).*

---

## Containerization & Local Docker

The repository includes a multi-stage [`Dockerfile`](Dockerfile) that builds the React client using Bun and packages the FastAPI backend into a lean Python 3.12 production container with static single-page application serving.

The Docker build automatically packages root `.env` into the image runtime, so you do not need to manually pass environment variables in `docker run`:

```bash
# Build the unified container image
docker build -t ug-scripts:local .

# Run the container
docker run -d --name ug-scripts -p 8080:8080 ug-scripts:local
```

Access the application:
- Web App: [http://localhost:8080](http://localhost:8080)
- API Health Check: [http://localhost:8080/health](http://localhost:8080/health)
- Swagger Docs: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## Deployment to Google Cloud Run

The production stack deploys to Google Cloud Run as a serverless container with keyless Vertex AI, Firestore, and Cloud Storage authentication via Application Default Credentials (ADC).

### 1. GCP Prerequisites & IAM Setup

Enable the required Google Cloud APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  --project your-gcp-project-id
```

Create a dedicated runtime service account and grant it the necessary IAM roles:
```bash
# Create service account
gcloud iam service-accounts create ug-scripts-runner \
  --display-name="UG-Scripts Cloud Run Service Account" \
  --project your-gcp-project-id

# Grant Vertex AI Gemini invocation
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:ug-scripts-runner@your-gcp-project-id.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Firestore database read/write
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:ug-scripts-runner@your-gcp-project-id.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Grant Cloud Storage object creator/viewer for image audit archiving
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="serviceAccount:ug-scripts-runner@your-gcp-project-id.iam.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

### 2. Seed Initial Firestore Access Codes & Demo Catalog
Run the seeding script to populate initial 5-character demo access codes (`DEMO1`, `DHAKA`, `BETA1`, `UG001`) and the 12-item demo product shelf:

```bash
apps/api/.venv/bin/python apps/api/scripts/seed_firestore.py
```

### 3. Deploy to Cloud Run
Deploy the application directly from source code using Google Cloud Build:

```bash
gcloud run deploy ug-scripts \
  --source . \
  --project your-gcp-project-id \
  --region asia-southeast1 \
  --service-account ug-scripts-runner@your-gcp-project-id.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-gcp-project-id,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.5-flash,API_KEY=your-secure-random-api-key \
  --allow-unauthenticated
```

---

## Useful Commands

| Command | Action |
| :--- | :--- |
| `bun run dev:web` | Starts the Vite React development server |
| `bun run build:web` | Type-checks (`tsc`) and builds the production web bundle |
| `bun run lint:web` | Runs Oxlint linter on the web application |
| `bun run test:api` | Runs Pytest suite (34 tests covering health, auth, validation, rate limiting, and SSE streaming) |
| `bun run gen:types` | Generates TypeScript interfaces from FastAPI OpenAPI schema |
| `python apps/api/scripts/seed_firestore.py` | Seeds Firestore with demo products and access codes |
