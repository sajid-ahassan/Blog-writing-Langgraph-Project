from __future__ import annotations

import re
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import streamlit as st

from app import workflow

APP_TITLE = "AI Blog Studio"
APP_SUBTITLE = "Generate research-aware blogs with planning, markdown, and images from a single topic."
BLOG_DIR = Path("Blog_md")
IMAGE_DIR = Path("images")


def init_session_state() -> None:
    defaults = {
        "last_topic": "",
        "run_status": "idle",
        "latest_state": {},
        "last_error": None,
        "selected_markdown": None,
        "selected_markdown_content": "",
        "last_run_at": None,
        "ui_nonce": str(int(time.time() * 1000)),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session() -> None:
    for key in [
        "last_topic",
        "run_status",
        "latest_state",
        "last_error",
        "selected_markdown",
        "selected_markdown_content",
        "last_run_at",
        "ui_nonce",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()


def normalize_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return normalize_data(value.model_dump())
    if isinstance(value, dict):
        return {k: normalize_data(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [normalize_data(v) for v in value]
    if isinstance(value, list):
        return [normalize_data(v) for v in value]
    return value


def merge_state(target: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(target)
    for key, value in updates.items():
        clean_value = normalize_data(value)
        if key in {"sections", "answers"}:
            merged[key] = (merged.get(key) or []) + (clean_value or [])
        else:
            merged[key] = clean_value
    return merged


def list_files(directory: Path, patterns: Iterable[str]) -> List[Path]:
    if not directory.exists():
        return []
    results: List[Path] = []
    for pattern in patterns:
        results.extend(directory.glob(pattern))
    return sorted(
        [path for path in results if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def slugify_title(text: str) -> str:
    safe = (text or "").lower().replace(" ", "_").replace(":", "_")
    safe = re.sub(r"[^a-z0-9_\-]+", "", safe)
    return safe.strip("_") or "blog_output"


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def estimate_reading_time(text: str, wpm: int = 200) -> int:
    words = count_words(text)
    return max(1, round(words / wpm)) if words else 0


def locate_markdown_file(latest_state: Dict[str, Any]) -> Path | None:
    plan = latest_state.get("plan") or {}
    title = plan.get("main_blog_title") if isinstance(plan, dict) else None
    if title:
        candidate = BLOG_DIR / f"{slugify_title(title)}.md"
        if candidate.exists():
            return candidate
    files = list_files(BLOG_DIR, ["*.md"])
    return files[0] if files else None


def load_markdown_content(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_selected_markdown_path() -> Path | None:
    selected = st.session_state.get("selected_markdown")
    if not selected:
        return None
    path = BLOG_DIR / selected
    return path if path.exists() else None


def parse_stream_event(event: Any) -> List[Tuple[str, Dict[str, Any]]]:
    items: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(event, dict):
        for key, value in event.items():
            if isinstance(value, dict):
                items.append((str(key), value))
    elif isinstance(event, tuple) and len(event) == 2 and isinstance(event[1], dict):
        items.append((str(event[0]), event[1]))
    return items


def run_workflow(topic: str) -> None:
    st.session_state.last_topic = topic
    st.session_state.run_status = "running"
    st.session_state.latest_state = {}
    st.session_state.last_error = None

    thread_id = f"streamlit-{int(time.time() * 1000)}"
    payload = {"topic": topic}
    config = {"configurable": {"thread_id": thread_id}}

    try:
        captured = False

        try:
            for event in workflow.stream(payload, config=config, stream_mode="updates"):
                captured = True
                for _, updates in parse_stream_event(event):
                    st.session_state.latest_state = merge_state(st.session_state.latest_state, updates)
        except TypeError:
            for event in workflow.stream(payload, config=config):
                captured = True
                for _, updates in parse_stream_event(event):
                    st.session_state.latest_state = merge_state(st.session_state.latest_state, updates)

        if not captured:
            result = workflow.invoke(payload, config=config)
            st.session_state.latest_state = merge_state(
                st.session_state.latest_state,
                normalize_data(result),
            )
        else:
            snapshot = workflow.get_state(config)
            values = getattr(snapshot, "values", None)
            if values:
                st.session_state.latest_state = merge_state(
                    st.session_state.latest_state,
                    normalize_data(values),
                )

        st.session_state.run_status = "completed"
        st.session_state.last_run_at = datetime.now()

        latest_path = locate_markdown_file(st.session_state.latest_state)
        if latest_path:
            st.session_state.selected_markdown = latest_path.name
            st.session_state.selected_markdown_content = load_markdown_content(latest_path)
        else:
            st.session_state.selected_markdown_content = st.session_state.latest_state.get("final_blog", "")

        st.toast("Blog generation completed", icon="✅")
    except Exception as exc:
        st.session_state.run_status = "failed"
        st.session_state.last_error = str(exc)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1450px;
                padding-top: 1.15rem;
                padding-bottom: 2rem;
            }
            .hero-card {
                border: 1px solid #e7eaf0;
                border-radius: 22px;
                padding: 1.25rem 1.35rem;
                background: linear-gradient(180deg, #fcfdff 0%, #f7f9fc 100%);
                min-height: 144px;
            }
            .asset-card {
                border: 1px solid #e7eaf0;
                border-radius: 22px;
                padding: 0.9rem 1rem;
                background: linear-gradient(180deg, #fcfdff 0%, #f7f9fc 100%);
                min-height: 144px;
            }
            .muted {
                color: #667085;
                font-size: 0.94rem;
            }
            .tiny-muted {
                color: #667085;
                font-size: 0.82rem;
            }
            .soft-card {
                border: 1px solid #e7eaf0;
                border-radius: 18px;
                padding: 0.95rem 1rem;
                background: #fbfcfe;
            }
            div[data-testid="stMetricValue"] {
                font-size: 1.05rem;
            }
            div[data-testid="stMetricLabel"] {
                font-size: 0.8rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.sidebar.title(APP_TITLE)
    st.sidebar.caption("Create new blogs and revisit saved markdown files")

    with st.sidebar.form("topic_form", clear_on_submit=False):
        topic = st.text_area(
            "Topic",
            value=st.session_state.last_topic,
            height=110,
            placeholder="e.g. Gen AI evolution from 2024 to today",
        )
        generate = st.form_submit_button("Generate Blog", use_container_width=True, type="primary")
        reset = st.form_submit_button("Reset Session", use_container_width=True)

    if reset:
        reset_session()
        st.rerun()

    if generate:
        if not topic.strip():
            st.sidebar.warning("Enter a topic first.")
        else:
            with st.spinner("Generating blog..."):
                run_workflow(topic.strip())
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Saved Blogs")

    markdown_files = list_files(BLOG_DIR, ["*.md"])
    markdown_names = [path.name for path in markdown_files]

    if markdown_names:
        current = st.session_state.selected_markdown if st.session_state.selected_markdown in markdown_names else markdown_names[0]
        selected = st.sidebar.radio(
            "Saved markdown files",
            options=markdown_names,
            index=markdown_names.index(current),
            key="sidebar_markdown_selector",
            label_visibility="collapsed",
        )

        if selected != st.session_state.selected_markdown:
            st.session_state.selected_markdown = selected
            st.session_state.selected_markdown_content = load_markdown_content(BLOG_DIR / selected)

        selected_path = BLOG_DIR / selected
        st.sidebar.caption(
            f"Updated: {datetime.fromtimestamp(selected_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        st.sidebar.caption("No markdown files found yet.")

    st.sidebar.divider()
    st.sidebar.subheader("Workspace Snapshot")
    latest_state = st.session_state.latest_state or {}
    plan = latest_state.get("plan") or {}
    st.sidebar.write(f"**Status:** {st.session_state.run_status.title()}")
    st.sidebar.write(f"**Topic:** {st.session_state.last_topic or '—'}")
    if plan:
        st.sidebar.write(f"**Audience:** {plan.get('audience', '—')}")
        st.sidebar.write(f"**Tone:** {plan.get('tone', '—')}")
        st.sidebar.write(f"**Kind:** {plan.get('blog_kind', '—')}")


def get_latest_image_paths(limit: int = 3) -> List[Path]:
    return list_files(IMAGE_DIR, ["*.png", "*.jpg", "*.jpeg", "*.webp"])[:limit]


def render_header(selected_markdown_path: Path | None) -> None:
    title_col, image_col, action_col = st.columns([0.3, 2.2, 1.2])


    
    with action_col:
        st.markdown("<div style='height:2.1rem'></div>", unsafe_allow_html=True)
        if selected_markdown_path and selected_markdown_path.exists():
            st.download_button(
                "Download Markdown",
                data=selected_markdown_path.read_bytes(),
                file_name=selected_markdown_path.name,
                mime="text/markdown",
                key=f"download_btn_{selected_markdown_path.name}",
                use_container_width=True,
            )
        else:
            st.button("Download Markdown", disabled=True, use_container_width=True)

        st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
        status_label = st.session_state.run_status.title()
        st.markdown(f"<p class='tiny-muted' style='text-align:center;'>Status: {status_label}</p>", unsafe_allow_html=True)

    if st.session_state.run_status == "failed":
        st.error("Blog generation failed.")
        with st.expander("Error details", expanded=True):
            st.code(st.session_state.last_error or "Unknown error")


def render_metric_row(latest_state: Dict[str, Any]) -> None:
    plan = latest_state.get("plan") or {}
    queries = latest_state.get("queries") or []
    answers = latest_state.get("answers") or []
    sections = latest_state.get("sections") or []
    images = latest_state.get("image_specs") or []

    row1 = st.columns(6)
    row1[0].metric("Research Needed", str(latest_state.get("needs_research", "—")))
    row1[1].metric("Research Mode", str(latest_state.get("research_mode", "—")))
    row1[2].metric("Queries", len(queries))
    row1[3].metric("Sources", len(answers))
    row1[4].metric("Sections", len(sections) or len(plan.get("blog_sections", [])))
    row1[5].metric("Images Planned", len(images))

    row2 = st.columns(4)
    row2[0].metric("Audience", plan.get("audience", "—"))
    row2[1].metric("Tone", plan.get("tone", "—"))
    row2[2].metric("Markdown Ready", "Yes" if latest_state.get("final_blog") or st.session_state.selected_markdown_content else "No")
    row2[3].metric("Images Ready", "Yes" if list_files(IMAGE_DIR, ["*.png", "*.jpg", "*.jpeg", "*.webp"]) else "No")


def render_overview(latest_state: Dict[str, Any], selected_markdown_content: str) -> None:
    st.subheader("Overview")
    plan = latest_state.get("plan") or {}
    title = plan.get("main_blog_title") or st.session_state.selected_markdown or "Blog output will appear here"

    top = st.columns([2.2, 1, 1])
    with top[0]:
        st.markdown(f"### {title}")
        st.caption(st.session_state.last_topic or "No topic submitted yet.")
        if selected_markdown_content:
            st.success("Markdown is available for preview and download.")
        else:
            st.caption("Generate a blog to populate planning, markdown, image assets, and preview sections.")
    with top[1]:
        st.metric("Markdown Files", len(list_files(BLOG_DIR, ["*.md"])))
    with top[2]:
        st.metric("Image Files", len(list_files(IMAGE_DIR, ["*.png", "*.jpg", "*.jpeg", "*.webp"])))

    render_metric_row(latest_state)


def render_research_section(latest_state: Dict[str, Any]) -> None:
    st.subheader("Research")
    st.write(f"**Research required:** {latest_state.get('needs_research', '—')}")
    st.write(f"**Research mode:** {latest_state.get('research_mode', '—')}")

    queries = latest_state.get("queries") or []
    answers = latest_state.get("answers") or []
    query_tab, evidence_tab = st.tabs(["Queries", "Evidence"])

    with query_tab:
        if not queries:
            st.caption("No search queries generated.")
        for idx, query in enumerate(queries, start=1):
            st.markdown(f"**{idx}.** {query}")

    with evidence_tab:
        if not answers:
            st.caption("No evidence collected.")
        for idx, item in enumerate(answers, start=1):
            with st.container(border=True):
                st.markdown(f"**Evidence {idx}**")
                st.write(f"**Query:** {item.get('query', '—')}")
                url = item.get("url")
                if url:
                    st.write(f"**URL:** {url}")
                content = item.get("content", "")
                st.text_area(
                    "Evidence content",
                    value=content,
                    height=180,
                    key=f"evidence_content_{idx}_{st.session_state.ui_nonce}",
                    label_visibility="collapsed",
                )


def render_planning_section(latest_state: Dict[str, Any]) -> None:
    st.subheader("Planning")
    plan = latest_state.get("plan") or {}
    if not plan:
        st.caption("No plan available yet.")
        return

    hero = st.columns([3, 1, 1, 1])
    hero[0].markdown(f"### {plan.get('main_blog_title', 'Untitled Blog')}")
    hero[1].metric("Audience", plan.get("audience", "—"))
    hero[2].metric("Tone", plan.get("tone", "—"))
    hero[3].metric("Kind", plan.get("blog_kind", "—"))

    for sec in plan.get("blog_sections", []):
        with st.container(border=True):
            cols = st.columns([1, 5, 1.3, 1.2])
            cols[0].markdown(f"**#{sec.get('section_id', '—')}**")
            cols[1].markdown(f"**{sec.get('section_title', 'Untitled Section')}**")
            cols[2].markdown(f"`{sec.get('target_length', '—')} words`")
            cols[3].markdown("`Code`" if sec.get("requires_code") else "`Text`")
            st.write(sec.get("section_description", ""))


def render_sections_section(latest_state: Dict[str, Any]) -> None:
    st.subheader("Sections")
    sections = latest_state.get("sections") or []
    if not sections:
        st.caption("No generated sections yet.")
        return

    ordered_sections = sorted(sections, key=lambda item: item[0])
    for idx, (section_id, content) in enumerate(ordered_sections, start=1):
        with st.expander(f"Section {section_id}", expanded=False):
            meta = st.columns(2)
            meta[0].metric("Word Count", count_words(content))
            meta[1].metric("Reading Time", f"{estimate_reading_time(content)} min")
            st.text_area(
                "Section markdown",
                value=content,
                height=240,
                key=f"section_markdown_{section_id}_{idx}_{st.session_state.ui_nonce}",
                label_visibility="collapsed",
            )


def markdown_download_widget(label: str, text: str, filename: str, key: str) -> None:
    st.download_button(
        label,
        data=text.encode("utf-8"),
        file_name=filename,
        mime="text/markdown",
        key=key,
    )


def render_markdown_pipeline(latest_state: Dict[str, Any], selected_markdown_content: str) -> None:
    st.subheader("Markdown Pipeline")
    merged = latest_state.get("merged_md", "")
    placeholders = latest_state.get("md_with_placeholders", "")
    final_blog = latest_state.get("final_blog", "") or selected_markdown_content

    tabs = st.tabs(["Merged Markdown", "With Placeholders", "Final Markdown"])
    items = [
        (tabs[0], merged, "merged_blog.md", "merged_dl"),
        (tabs[1], placeholders, "with_placeholders.md", "placeholder_dl"),
        (tabs[2], final_blog, "final_blog.md", "final_dl"),
    ]

    for idx, (tab, text, filename, key_suffix) in enumerate(items, start=1):
        with tab:
            if not text:
                st.caption("No content available.")
                continue
            markdown_download_widget(
                "Download",
                text,
                filename,
                key=f"{key_suffix}_{idx}_{st.session_state.ui_nonce}",
            )
            st.text_area(
                filename,
                value=text,
                height=420,
                key=f"markdown_textarea_{key_suffix}_{idx}_{st.session_state.ui_nonce}",
                label_visibility="collapsed",
            )


def render_markdown_with_images(markdown_text: str) -> None:
    if not markdown_text:
        st.caption("No markdown available yet.")
        return

    pattern = re.compile(r"!\[(.*?)\]\((.*?)\)(?:\n\n\*(.*?)\*)?", re.DOTALL)
    cursor = 0

    for match in pattern.finditer(markdown_text):
        before = markdown_text[cursor:match.start()]
        if before.strip():
            st.markdown(before)

        alt, raw_path, caption = match.groups()
        image_path = Path(raw_path.lstrip("/"))
        if image_path.exists():
            st.image(str(image_path), caption=caption or alt, use_container_width=True)
        else:
            st.markdown(match.group(0))

        cursor = match.end()

    remainder = markdown_text[cursor:]
    if remainder.strip():
        st.markdown(remainder)


def render_image_gallery(latest_state: Dict[str, Any]) -> None:
    st.subheader("Images")
    image_specs = latest_state.get("image_specs") or []
    existing_images = list_files(IMAGE_DIR, ["*.png", "*.jpg", "*.jpeg", "*.webp"])

    if not image_specs and not existing_images:
        st.caption("No images generated yet.")
        return

    if image_specs:
        cols = st.columns(2)
        for idx, spec in enumerate(image_specs):
            path = IMAGE_DIR / spec.get("filename", "")
            with cols[idx % 2].container(border=True):
                st.markdown(f"**{spec.get('filename', 'image')}**")
                if path.exists():
                    st.image(str(path), use_container_width=True)
                st.caption(spec.get("caption", ""))
                st.write(f"**Alt:** {spec.get('alt', '—')}")
                st.write(f"**Prompt:** {spec.get('prompt', '—')}")
                if path.exists():
                    st.download_button(
                        "Download image",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/octet-stream",
                        key=f"gallery_spec_{path.name}_{idx}_{st.session_state.ui_nonce}",
                        use_container_width=True,
                    )
    else:
        cols = st.columns(2)
        for idx, path in enumerate(existing_images):
            with cols[idx % 2].container(border=True):
                st.markdown(f"**{path.name}**")
                st.image(str(path), use_container_width=True)
                st.download_button(
                    "Download image",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/octet-stream",
                    key=f"gallery_existing_{path.name}_{idx}_{st.session_state.ui_nonce}",
                    use_container_width=True,
                )


def render_blog_preview(latest_state: Dict[str, Any], selected_markdown_content: str) -> None:
    st.subheader("Blog Preview")
    final_blog = latest_state.get("final_blog", "") or selected_markdown_content
    if not final_blog:
        st.caption("Generate or select a blog to preview it here.")
        return

    preview_mode = st.radio(
        "Preview mode",
        options=["Rendered Preview", "Raw Markdown"],
        horizontal=True,
        key=f"preview_mode_{st.session_state.ui_nonce}",
    )

    cols = st.columns(3)
    cols[0].metric("Word Count", count_words(final_blog))
    cols[1].metric("Reading Time", f"{estimate_reading_time(final_blog)} min")
    cols[2].metric("Images", len(re.findall(r"!\[.*?\]\(.*?\)", final_blog)))

    if preview_mode == "Rendered Preview":
        render_markdown_with_images(final_blog)
    else:
        st.text_area(
            "Raw markdown",
            value=final_blog,
            height=640,
            key=f"raw_markdown_preview_{st.session_state.ui_nonce}",
            label_visibility="collapsed",
        )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")
    init_session_state()
    inject_styles()

    render_sidebar()

    selected_path = get_selected_markdown_path()
    selected_content = st.session_state.selected_markdown_content or load_markdown_content(selected_path)
    latest_state = st.session_state.latest_state or {}

    render_header(selected_path)

    tabs = st.tabs(
        [
            "Overview",
            "Research",
            "Planning",
            "Sections",
            "Markdown Pipeline",
            "Images",
            "Blog Preview",
        ]
    )

    with tabs[0]:
        render_overview(latest_state, selected_content)
    with tabs[1]:
        render_research_section(latest_state)
    with tabs[2]:
        render_planning_section(latest_state)
    with tabs[3]:
        render_sections_section(latest_state)
    with tabs[4]:
        render_markdown_pipeline(latest_state, selected_content)
    with tabs[5]:
        render_image_gallery(latest_state)
    with tabs[6]:
        render_blog_preview(latest_state, selected_content)


if __name__ == "__main__":
    main()