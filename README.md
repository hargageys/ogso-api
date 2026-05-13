# Ogso API — National Knowledge Infrastructure for the Horn of Africa

**Ogso** is a state-of-the-art, AI-powered intelligence platform designed to democratize access to high-impact scientific research. By leveraging Large Language Models (LLMs) and Generative AI, Ogso transforms over 36,000 scattered academic papers into a unified, multimodal discovery engine for researchers, clinical health workers, and national policy-makers.

### 🚀 Frontier Tech & Impact Features

- **Cross-Lingual Semantic Intelligence:** Utilizing `pgvector` and Deep Learning embeddings to enable "Cross-Lingual Information Retrieval." Users execute complex technical queries in Somali to surface high-relevance English-language research via Vector Similarity Search.

- **Multimodal AI Pipeline (Oral-First):** Integrating advanced Text-to-Speech (TTS) and Neural Voice Synthesis to generate Somali-language audio summaries. This respects local oral traditions and bridges the communication gap for populations in rural and last-mile settings.

- **Generative AI Video Awareness:** A proprietary pipeline to transform scientific abstracts into **AI-generated Video Content**. Using GenAI, Ogso creates visual awareness campaigns for social media to disseminate life-saving health data at scale.

- **Automated Policy Synthesis (RAG):** Powered by Anthropic Claude (LLM), the platform uses Retrieval-Augmented Generation (RAG) to cluster research data into actionable, evidence-based policy briefs for government decision-making.

- **Researcher Sovereignty:** Automated Metadata Analysis and ML-based tagging to identify and highlight locally-led research, fostering regional academic capacity and visibility.

---

### 🦟 Case Study: Tackling Climate-Driven Malaria Crises

Ogso is a specialized tool for **Anticipatory Action** and **Healthcare Readiness** during climate-sensitive health emergencies.

**The Challenge:** The invasive *Anopheles stephensi* mosquito is migrating across the region due to shifting climate patterns. Most surveillance data and mitigation strategies are currently locked in English-language academic PDFs, inaccessible to front-line responders.

**The Ogso Solution:**

1.  **Real-time Ingestion:** Automated scrapers ingest global research on vector-borne disease outbreaks and climate-health correlations.

2.  **AI Translation & Audio:** The LLM summarizes findings, and the TTS engine generates **Audio Alerts** in Somali for community health workers.

3.  **GenAI Video Awareness:** The platform automatically generates short **AI-driven Videos** for social media, visually demonstrating how to identify and destroy urban mosquito breeding sites.

4.  **Strategic Forecasting:** Generates a unified policy brief for ministries to transition from rural to urban-specific malaria intervention strategies based on real-time data.

---

## 🛠 Frontier Tech Stack

- **Backend:** FastAPI + uvicorn (High-performance Async ASGI)

- **Vector Database:** PostgreSQL 16 + `pgvector` (Semantic Intelligence & RAG)

- **Neural Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`)

- **Generative AI:** Anthropic Claude (LLM) & Neural TTS Engines

- **Video Generation:** GenAI Media Pipeline

- **Task Orchestration:** APScheduler for real-time ingestion and embedding

- **Storage:** Cloudflare R2 (Distributed Object Storage)

---

## 💻 Technical Setup

### 1. Vector Database Initialization

**Ubuntu / Debian:**
```bash
sudo apt install postgresql-16 postgresql-16-pgvector
sudo -u postgres createuser -s $USER
createdb ogso

### 2. Neural Environment Configuration

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


3. Migrations & Schema Deployment
```bash
alembic upgrade head


## 📂 Research Migration (ogso.db)

To migrate localized SQLite datasets to the high-performance Vector instance:

```bash
# Data Ingestion
python scripts/migrate_sqlite.py --db ogso.db

# Trigger Neural Embedding Pipeline
python -c "import asyncio; from app.workers.embedder import run_embedder; asyncio.run(run_embedder())"


### 📡 Core Intelligence Endpoints

* **Discovery**
    `POST /search/semantic`
    Powered by **Vector Similarity** and **Deep Learning** embeddings.

* **Synthesis**
    `POST /search/policy`
    Powered by **LLM (Anthropic Claude)** using **Retrieval-Augmented Generation (RAG)**.

* **Oral-First**
    `GET /papers/{id}/audio`
    Powered by **Neural TTS** and **Local Voice Synthesis** for Somali-language delivery.

* **Visuals**
    `GET /papers/{id}/video`
    Powered by the **GenAI Video Awareness Pipeline** for automated social media dissemination.

---

### 🤝 Join the Mission

We are currently scaling our **Frontend & Mobile team** to finalize the multimodal interface (Audio/Video/Web). If you are an expert in building AI-integrated interfaces for social impact, join us in making science accessible to everyone.

**License:** MIT (Digital Public Good)

