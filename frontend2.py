import os
from pathlib import Path
from datetime import date

import streamlit as st

from app import workflow


st.set_page_config(
    page_title="Blog Writing Agent",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
:root {
    --bg: #0b1220;
    --panel: #111827;
    --panel-2: #1f2937;
    --border: rgba(255,255,255,0.08);
    --text: #f3f4f6;
    --muted: #9ca3af;
    --accent: #ef4444;
    --accent-2: #1d4ed8;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1f2430 0%, #171b24 100%);
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stDateInput input {
    background: #0f172a !important;
    color: var(--text) !important;
    border: 1px solid rgba(239, 68, 68, 0.35) !important;
    border-radius: 10px !important;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.main-shell {
    background: transparent;
    border-radius: 20px;
}

.hero-title {
    font-size: 3rem;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 0.25rem;
}

.hero-subtitle {
    color: var(--muted);
    margin-bottom: 1.5rem;
}

.status-box {
    background: rgba(29, 78, 216, 0.22);
    border: 1px solid rgba(96, 165, 250, 0.2);
    color: #dbeafe;
    padding: 0.95rem 1rem;
    border-radius: 12px;
    margin: 0.75rem 0 1.25rem 0;
}

.panel-card {
    background: rgba(17, 24, 39, 0.95);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1rem;
}

.past-blog-item {
    padding: 0.45rem 0;
    color: #d1d5db;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 0.95rem;
}

.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #ef4444, #f97316) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 0.7rem 1rem !important;
}

.stDownloadButton > button {
    border-radius: 10px !important;
}

div[data-testid="stTabs"] button {
    color: #d1d5db;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #fca5a5;
}
</style>
"""


st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "past_blogs" not in st.session_state:
    st.session_state.past_blogs = []


def add_log(message: str) -> None:
    st.session_state.logs.append(message)


def render_sidebar() -> tuple[str, date, bool]:
    with st.sidebar:
        st.markdown("## Generate New Blog")
        topic = st.text_area("Topic", height=120, placeholder="Self Attention")
        as_of_date = st.date_input("As-of date", value=date.today())
        generate = st.button("🚀 Generate Blog", use_container_width=True)

        st.markdown("---")
        st.markdown("## Past blogs")
        if st.session_state.past_blogs:
            for item in st.session_state.past_blogs[-8:][::-1]:
                st.markdown(f'<div class="past-blog-item">• {item}</div>', unsafe_allow_html=True)
        else:
            st.caption("No blogs generated yet.")

    return topic, as_of_date, generate


def extract_plan_text(plan) -> str:
    if not plan:
        return "No plan available yet."

    lines = [
        f"# {getattr(plan, 'main_blog_title', 'Untitled')}",
        f"**Audience:** {getattr(plan, 'audience', '-')}",
        f"**Tone:** {getattr(plan, 'tone', '-')}",
        f"**Type:** {getattr(plan, 'blog_kind', '-')}",
        "",
        "## Sections",
    ]
    for sec in getattr(plan, "blog_sections", []):
        lines.extend(
            [
                f"### {sec.section_id}. {sec.section_title}",
                f"- Target length: {sec.target_length} words",
                f"- Requires code: {sec.requires_code}",
                f"- Brief: {sec.section_description}",
                "",
            ]
        )
    return "\n".join(lines)


def extract_evidence_text(answers) -> str:
    if not answers:
        return "No evidence collected."

    blocks = []
    for idx, ans in enumerate(answers, start=1):
        query = getattr(ans, "query", "") if not isinstance(ans, dict) else ans.get("query", "")
        url = getattr(ans, "url", "") if not isinstance(ans, dict) else ans.get("url", "")
        content = getattr(ans, "content", "") if not isinstance(ans, dict) else ans.get("content", "")
        blocks.append(
            f"### Evidence {idx}\n"
            f"**Query:** {query or '-'}\n\n"
            f"**URL:** {url or '-'}\n\n"
            f"{content or 'No extracted notes.'}"
        )
    return "\n\n---\n\n".join(blocks)


def extract_images(result_dict: dict) -> list[dict]:
    return result_dict.get("image_specs", []) or []


def run_workflow(topic: str):
    st.session_state.logs = []
    add_log("Starting workflow")

    initial_state = {
        "topic": topic,
        "needs_research": False,
        "research_mode": "closed_book",
        "queries": [],
        "answers": [],
        "sections": [],
        "final_blog": "",
        "merged_md": "",
        "md_with_placeholders": "",
        "image_specs": [],
    }

    result = workflow.invoke(initial_state)
    add_log("Workflow completed")
    st.session_state.run_result = result

    plan = result.get("plan")
    title = getattr(plan, "main_blog_title", topic) if plan else topic
    st.session_state.past_blogs.append(title)


def render_main() -> None:
    st.markdown('<div class="main-shell">', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Blog Writing Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Generate a full blog plan, research notes, markdown, and image plan from a single topic.</div>', unsafe_allow_html=True)

    result = st.session_state.run_result
    if not result:
        st.markdown('<div class="status-box">Enter a topic and click Generate Blog.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    tabs = st.tabs(["🪄 Plan", "🔎 Evidence", "📝 Markdown Preview", "🖼️ Images", "📄 Logs"])

    plan = result.get("plan")
    answers = result.get("answers", [])
    final_blog = result.get("final_blog", "")
    images = extract_images(result)

    with tabs[0]:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown(extract_plan_text(plan))
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown(extract_evidence_text(answers))
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown(final_blog or "No markdown generated.")
        if final_blog:
            st.download_button(
                label="Download Markdown",
                data=final_blog,
                file_name="blog_output.md",
                mime="text/markdown",
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if not images:
            st.info("No images were planned for this blog.")
        else:
            for img in images:
                st.json(img)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[4]:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if st.session_state.logs:
            for log in st.session_state.logs:
                st.write(f"- {log}")
        else:
            st.write("No logs yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    topic, as_of_date, generate = render_sidebar()

    if generate:
        if not topic.strip():
            st.warning("Please enter a topic first.")
        else:
            with st.spinner(f"Generating blog for {as_of_date}..."):
                run_workflow(topic.strip())

    render_main()


if __name__ == "__main__":
    main()
