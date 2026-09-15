# 🧠 Psydekik

### A self-hosted family platform powered by Chappie

**Psydekik** is a self-hosted family command center built around **Chappie**, a conversational AI assistant designed to connect system intelligence, voice interaction, automation, media, and family services through a single interface.

Built primarily with **Python**, **FastAPI**, **MCP**, and **Raspberry Pi**, Psydekik explores what happens when an AI assistant isn't just a chatbot, but becomes an active part of the infrastructure it helps manage.

> **Project Status:** 🚧 Active Development

---

## 🤖 Meet Chappie

Chappie is the intelligence at the center of Psydekik.

Rather than sending every request directly to a cloud LLM, Chappie uses a **hybrid local/cloud architecture**. Requests can be classified and routed to local system services, tools, or cloud intelligence depending on what the user is asking.

This allows Psydekik to answer questions such as:

* "How's the Pi doing?"
* "How much memory am I using?"
* "How much storage is left?"
* "What's the CPU temperature?"

...without requiring a cloud model to retrieve information the system already knows locally.

For broader conversational and knowledge-based requests, Chappie can route the request to cloud intelligence.

The long-term goal is a responsive assistant that understands not only conversation, but also the environment in which it operates.

---

## ✨ Current Features

### 🧠 Hybrid AI Routing

Psydekik can distinguish between requests that can be handled locally and those requiring broader AI intelligence.

This architecture reduces unnecessary API calls while allowing Chappie to remain conversational and capable.

### 🎙️ Voice Interaction

Psydekik includes an experimental local voice pipeline supporting:

**Microphone → Speech Detection → Speech-to-Text → Chappie → Text-to-Speech → Speakers**

The system currently supports:

* Local microphone input
* Automatic speech detection
* Offline speech recognition
* Conversational response generation
* Local text-to-speech
* Audio playback
* Voice-aware system responses

The eventual goal is hands-free interaction through a wake phrase such as:

> **"Hey Chappie."**

### 📊 Live System Intelligence

Chappie can retrieve real-time information from the Raspberry Pi, including:

* CPU usage
* CPU temperature
* Memory utilization
* Available memory
* Disk utilization
* Available storage
* System uptime

System information is exposed through backend services and API endpoints rather than being hardcoded into the assistant.

### 🖥️ Live Frontend Dashboard

Psydekik includes a developing console-style frontend for viewing live system information and interacting with the platform.

The dashboard is designed to become the central interface for:

* Chappie
* System monitoring
* Family services
* Media
* Storage
* Automation
* Network services

### 🔌 MCP Integration

Psydekik includes a custom **Model Context Protocol (MCP)** server that exposes local capabilities to Chappie through structured tools.

Current MCP experimentation includes system-status tooling, with the architecture intended to expand into additional Psydekik services over time.

---

## 🏗️ Architecture

At a high level, Psydekik currently follows this flow:

```text
                         ┌─────────────────┐
                         │      User       │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                  Voice                       UI/API
                    │                           │
                    ▼                           │
          ┌───────────────────┐                 │
          │ Speech Recognition│                 │
          └─────────┬─────────┘                 │
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                         ┌─────────────────┐
                         │     Chappie     │
                         │  Orchestrator   │
                         └────────┬────────┘
                                  │
                         Semantic Routing
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
                 ▼                                 ▼
        ┌─────────────────┐               ┌─────────────────┐
        │ Local Services  │               │ Cloud AI / Web  │
        └────────┬────────┘               └─────────────────┘
                 │
          ┌──────┴───────┐
          │              │
          ▼              ▼
     MCP Tools      System Services
```

This separation allows Chappie to use deterministic local tools when possible while retaining access to more powerful external intelligence when necessary.

---

## 🛠️ Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* WebSockets

### AI & Intelligence

* Cloud LLM integration
* Semantic request routing
* Model Context Protocol (MCP)
* Local system tools

### Voice

* `sounddevice`
* Offline speech recognition
* `sherpa-onnx`
* Local text-to-speech
* ALSA audio integration

### Frontend

* Python-based console/dashboard interface
* Live API-backed system state
* Real-time system monitoring

### Infrastructure

* Raspberry Pi 5
* Ubuntu Server
* Linux
* Git / GitHub

---

## 📁 Project Structure

```text
psydekik/
│
├── api/
│   ├── main.py
│   ├── websocket.py
│   └── events.py
│
├── chappie/
│   ├── mcp_client.py
│   ├── orchestrator.py
│   │
│   └── voice/
│       ├── listen.py
│       ├── recorder.py
│       ├── stt.py
│       └── tts.py
│
├── frontend_console/
│   ├── api/
│   ├── state/
│   └── app.py
│
├── mcp_server/
│   ├── server.py
│   └── tools/
│
├── services/
│   └── system_service.py
│
├── tests/
│
└── README.md
```

> The project structure is evolving as Psydekik moves from experimentation toward a more modular application architecture.

---

## 🎯 Project Goals

Psydekik is ultimately intended to become a unified, self-hosted platform for the household.

Planned areas of expansion include:

* 🧠 More capable Chappie orchestration
* 🎙️ Reliable wake-word voice interaction
* 🏠 Household automation
* 📁 Family file and cloud-storage access
* 🎬 Media integration
* 🌐 Home-network monitoring
* 📅 Family services and scheduling
* 💬 Family communication
* 🔧 Expanded MCP tooling
* 📊 Richer dashboards
* 🔐 User authentication and permissions
* 📱 Mobile-friendly access
* ⚡ Background services and proactive events

The larger goal is to make Chappie capable of **using the services around it**, rather than simply talking about them.

---

## 🧪 Development Philosophy

Psydekik is intentionally being built as a modular system.

Instead of constructing one enormous AI application where every capability depends directly on the language model, functionality is separated into services and tools.

Chappie acts as the intelligence and orchestration layer connecting those systems.

This provides several advantages:

* Local operations remain local
* API usage can be reduced
* Individual services can be tested independently
* AI models can be replaced without rebuilding the application
* New tools can be introduced incrementally
* The system remains useful even when some external services are unavailable

---

## 🗺️ Roadmap

Psydekik is under active development.

### Current Focus

* [x] FastAPI backend foundation
* [x] System-status API
* [x] Chappie conversational orchestration
* [x] Local system routing
* [x] MCP server foundation
* [x] MCP system-status tool
* [x] Offline speech-to-text experimentation
* [x] Local text-to-speech
* [x] Live frontend system dashboard
* [ ] Wake-word detection
* [ ] Improved voice latency
* [ ] Expanded MCP toolset
* [ ] Chappie dashboard integration
* [ ] Family services
* [ ] Storage and media integration
* [ ] Authentication and user profiles
* [ ] Production deployment

---

## 🧑‍💻 Why I Built Psydekik

Psydekik began as an experiment in building an AI assistant around my own Raspberry Pi and home infrastructure.

The project quickly grew into a larger question:

**What if an AI assistant could actually understand and interact with the systems around it?**

Instead of building another chat interface wrapped around an API, Psydekik is an attempt to create an assistant with tools, local awareness, voice interaction, and access to real services.

Chappie is the conversational layer.

Psydekik is the world around him.

---

## ⚠️ Development Notice

Psydekik is currently an experimental personal project under active development.

Interfaces, dependencies, architecture, configuration, and installation procedures may change substantially as development continues.

It is **not currently intended as a production-ready application**.

---

## 👨‍💻 Author

**Josh Bruton**

Python Programmer • AI Integration • Automation • Backend Development • Raspberry Pi / Linux

Built as part of **Brutopia Design & Development Studio**.

---

## 📜 License

Licensing information will be added as the project approaches a public release.
