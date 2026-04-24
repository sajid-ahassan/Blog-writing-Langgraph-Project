# AI Blog Studio (LangGraph Multi-Agent System)

AI-powered blog generation workflow built with **LangGraph**, **LangChain**, **OpenAI**, **Tavily**, and **Streamlit**.

This project turns a single blog topic into a structured writing pipeline that:

- decides whether the topic needs research
- creates a blog plan with audience, tone, format, and sections
- generates each section in parallel
- merges the sections into one markdown article
- optionally plans and generates a supporting image
- saves the final blog as a Markdown file

## Overview

The core application is a multi-step graph workflow defined in `app.py`. The graph starts with a router, optionally runs a research step, creates a plan, fans out section-writing work to worker nodes, then runs a reducer subgraph that merges markdown, inserts image placeholders, generates an image, and writes the final blog file.

The repository also includes a Streamlit UI (`frontend2.py`) for entering a topic and viewing the generated plan, evidence, markdown output, image specs, and logs.

## Features

- **Topic-to-blog workflow** using LangGraph state transitions
- **Structured planning** with Pydantic schemas
- **Parallel section generation** using LangGraph fan-out
- **Markdown assembly** for final blog output
- **Optional image planning and generation** using `gpt-image-1`
- **Streamlit interface** for interactive use
- **Saved blog output** as Markdown files in a local folder

## Project Structure

```text
.
├── app.py           # Core LangGraph workflow and nodes
├── frontend.py      # Older/incomplete Streamlit frontend draft
├── blog.ipynb       # Notebook version used for development/prototyping
├── requirements.txt # Python dependencies
└── README.md
```

## Architecture

### 1. Router
The router analyzes the incoming topic and decides:

- whether research is needed
- what research mode to use
- which queries should be generated

### 2. Research
If research is required, the workflow enters a research node intended to gather supporting context.

### 3. Planner
The planner creates a structured blog plan with:

- final blog title
- target audience
- writing tone
- blog type
- 4 to 6 sections with section-specific instructions

### 4. Section Workers
Each section is sent to a worker node. Workers generate markdown for only their assigned section while staying aligned with the global plan.

### 5. Reducer Subgraph
A subgraph then:

1. combines all sections in order
2. decides whether an image is useful
3. inserts image placeholders
4. generates the image
5. replaces placeholders with markdown image links
6. saves the final markdown file

## State Design

The graph uses a shared state object that carries data such as:

- `topic`
- `needs_research`
- `research_mode`
- `queries`
- `answers`
- `plan`
- `sections`
- `merged_md`
- `md_with_placeholders`
- `image_specs`
- `final_blog`

This makes the workflow easy to extend with additional steps like SEO scoring, citation checking, or publishing.

## Tech Stack

- **Python**
- **LangGraph**
- **LangChain**
- **OpenAI API**
- **Tavily**
- **Pydantic**
- **Streamlit**
- **python-dotenv**

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sajid-ahassan/Blog-writing-Langgraph-Project.git
cd Blog-writing-Langgraph-Project
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root and add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

## Running the App

Run the Streamlit frontend:

```bash
streamlit run frontend2.py
```

Then:

1. Enter a topic in the sidebar
2. Click **Generate Blog**
3. Review the generated plan, evidence, markdown, image specs, and logs

## How It Works

### Planning Schema
The project uses Pydantic models to define a strict planning format. Each section includes:

- section id
- section title
- target length
- whether code is required
- a detailed writing brief

### Parallel Section Generation
After planning, the graph fans out each section to a worker node. This is a good design choice because it allows section-level generation to scale cleanly and keeps responsibilities separated.

### Image Planning
After the article is merged, the reducer decides whether an image would actually improve the post. If yes, it generates a single image specification and inserts the final image into the markdown.

## Current Strengths

- clear graph-based workflow
- strong use of structured outputs with Pydantic
- modular section writing design
- practical Streamlit UI for demo and experimentation
- notebook and app versions available for iteration

## Current Limitations

- The `research()` node initializes Tavily search but does not actually use retrieved search results yet.
- The workflow currently uses in-memory checkpointing only.
- `frontend.py` appears incomplete and should likely be removed or replaced.
- Error handling is minimal for API failures and malformed outputs.
- The generated markdown is saved locally, but there is no publishing/export pipeline beyond file download.

## Suggested Improvements

### Retrieval and grounding
- Actually execute Tavily queries and pass retrieved content into the structured `answer` objects.
- Add citation support so generated blogs can reference sources transparently.

### Reliability
- Add retries and exception handling around LLM calls and image generation.
- Validate section outputs before merge.
- Add logging for node-by-node execution timing.

### Product improvements
- Allow selecting blog style, audience, and tone from the UI.
- Add export options such as HTML or DOCX.
- Add persistent storage for generated blogs and images.
- Show generated images directly inside the Streamlit app.

### Engineering improvements
- Split `app.py` into modules such as `nodes.py`, `schemas.py`, and `graph.py`.
- Add unit tests for routing, planning, and markdown merge behavior.
- Add a sample `.env.example`.
- Clean up unused imports and legacy frontend code.

## Example Use Cases

- technical blog drafting
- explainer article generation
- tutorial outline and first-draft creation
- AI-assisted content ideation
- research-backed markdown article generation


## Future Roadmap

Potential next steps for the project:

- real retrieval-augmented research
- source-aware blog writing with citations
- multi-image support
- richer UI for editing and regeneration
- publishing to CMS platforms
- evaluation pipeline for blog quality


## Author

Created by **Sajid Ahasan**.

