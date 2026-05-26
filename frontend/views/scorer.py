from typing import Optional

import requests
import streamlit as st

from frontend.services import api_client
from frontend.components.dashboard import display_results_dashboard


def _read_jd(jd_file, jd_text: str) -> str:
    """
    Turn whatever the user provided into a plain JD string for the backend.

    For .txt files we decode in-process — that's a trivial operation, no need
    for a backend round-trip. For PDF/DOCX, we'd need the backend's parser;
    we don't have a public endpoint for that, so we ask the user to paste text
    instead for non-txt JDs.
    """
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning(
        "Job description files must be `.txt` for now — paste the JD text instead "
        "if you have a PDF or DOCX."
    )
    return ""


def _show_backend_error(exc: Exception) -> None:
    """Translate a `requests` exception into a friendly Streamlit error."""
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is `uvicorn backend.main:app` running on port 8000?")
    elif isinstance(exc, requests.Timeout):
        st.error("The backend took too long to respond. Try a smaller resume or check the server logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _summary_text(analysis: dict) -> str:
    """Readable text export built from the full backend analysis response."""
    def _score_value(value, default=0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _section(lines: list[str], title: str) -> None:
        lines.extend(["", title, "-" * len(title)])

    def _items(values, limit: int = 12) -> list[str]:
        return [str(value) for value in values[:limit]] if isinstance(values, list) else []

    score = _score_value(analysis.get("ATS_score", analysis.get("ats_score", 0)))
    component_scores = analysis.get("component_scores") or {}
    detailed_feedback = analysis.get("detailed_feedback") or []
    jd = analysis.get("jd_match_analysis") or analysis.get("jd_comparison") or {}
    skill_details = analysis.get("skill_validation_details") or {}

    lines = [
        "ATS RESUME ANALYSIS SUMMARY",
        "===========================",
        f"Overall ATS Score: {score:.0f}/100",
    ]

    interpretation = analysis.get("interpretation")
    if interpretation:
        lines.extend(["", "Interpretation:", str(interpretation)])

    if component_scores:
        _section(lines, "Score Breakdown")
        max_scores = {
            "formatting": 20,
            "keywords": 25,
            "content": 25,
            "skill_validation": 15,
            "ats_compatibility": 15,
        }
        for key, max_score in max_scores.items():
            value = _score_value(component_scores.get(key))
            label = key.replace("_", " ").title()
            pct = round((value / max_score) * 100) if max_score else 0
            lines.append(f"- {label}: {value:g}/{max_score} ({pct}%)")

    issues = _items(analysis.get("issues_summary") or analysis.get("critical_issues") or [], 15)
    if issues:
        _section(lines, "Top Issues")
        lines.extend(f"- {issue}" for issue in issues)

    if jd:
        _section(lines, "Job Description Match")
        lines.append(f"- Match Percentage: {jd.get('match_percentage', 0)}%")
        lines.append(f"- Semantic Similarity: {jd.get('semantic_similarity', 0)}")
        matched = _items(jd.get("matched_keywords") or [], 20)
        missing = _items(jd.get("missing_keywords") or [], 20)
        gaps = _items(jd.get("skills_gap") or [], 12)
        if matched:
            lines.append("- Matched Keywords: " + ", ".join(matched))
        if missing:
            lines.append("- Missing Keywords: " + ", ".join(missing))
        if gaps:
            lines.append("- Skills Gap: " + ", ".join(gaps))

    if skill_details:
        _section(lines, "Skill Validation")
        total = skill_details.get("total", 0)
        validated_count = skill_details.get("validated_count", 0)
        validation_pct = skill_details.get("validation_pct", 0)
        lines.append(f"- Validated Skills: {validated_count}/{total} ({validation_pct}%)")

        unvalidated = _items(skill_details.get("unvalidated") or [], 20)
        if unvalidated:
            lines.append("- Unvalidated Skills: " + ", ".join(unvalidated))

        validated = skill_details.get("validated") or []
        if validated:
            lines.append("- Evidence-backed Skills:")
            for item in validated[:10]:
                if isinstance(item, dict):
                    skill = item.get("skill", "Skill")
                    projects = item.get("projects") or []
                    suffix = f" ({', '.join(projects[:3])})" if projects else ""
                    lines.append(f"  - {skill}{suffix}")
                else:
                    lines.append(f"  - {item}")

    if detailed_feedback:
        _section(lines, "Detailed Fixes")
        for index, issue in enumerate(detailed_feedback[:10], start=1):
            if not isinstance(issue, dict):
                continue
            lines.extend([
                "",
                f"{index}. {issue.get('issue_title', 'Issue')}",
                f"   Severity: {issue.get('severity_level', 'N/A')} | ATS Impact: {issue.get('ats_impact', 'N/A')}",
            ])
            if issue.get("where_it_appears"):
                lines.append(f"   Where: {issue['where_it_appears']}")
            if issue.get("explanation"):
                lines.append(f"   Why it matters: {issue['explanation']}")
            if issue.get("how_to_fix"):
                lines.append(f"   How to fix: {issue['how_to_fix']}")
            action_items = _items(issue.get("action_items") or [], 6)
            if action_items:
                lines.append("   Action items:")
                lines.extend(f"   - {item}" for item in action_items)
            if issue.get("example_improvement"):
                lines.append("   Example improvement:")
                lines.extend(f"     {line}" for line in str(issue["example_improvement"]).splitlines())

    suggestions = _items(analysis.get("suggestions") or [], 12)
    if suggestions:
        _section(lines, "Suggestions")
        lines.extend(f"- {suggestion}" for suggestion in suggestions)

    return "\n".join(lines).strip() + "\n"


def _render_upload_area(analysis_mode: str):
    """Two-column upload widgets. Returns (resume_file, jd_file, jd_text)."""
    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Upload Resume")
        resume_file = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "doc", "docx"],
            help="Supported: PDF, DOC, DOCX (max 5 MB)",
            key="resume_upload",
        )
        if resume_file:
            st.success(f"✅ {resume_file.name} ({resume_file.size / 1024:.1f} KB)")

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        if analysis_mode == "Job Description Comparison":
            st.markdown("### 📋 Job Description")
            jd_method = st.radio(
                "Input method:",
                ["Paste Text", "Upload .txt File"],
                horizontal=True,
                key="jd_input_method",
            )
            if jd_method == "Upload .txt File":
                jd_file = st.file_uploader(
                    "Choose JD file (.txt only)",
                    type=["txt"],
                    key="jd_upload",
                )
                if jd_file:
                    st.success(f"✅ {jd_file.name}")
            else:
                jd_text = st.text_area(
                    "Paste job description text:",
                    height=200,
                    placeholder="Paste the JD here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.markdown("### 📋 Job Description")
            st.info("Switch to 'Job Description Comparison' mode to enable JD matching.")

    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("### 📥 Export Results")
    c1, c2 = st.columns(2)

    with c1:
        # Lazy: only call the backend the first time the user clicks expand.
        if st.button("📑 Generate PDF Report", use_container_width=True, type="primary"):
            try:
                with st.spinner("Generating PDF on backend..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state["access_token"],
                    )
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc)

        if "scorer_pdf_bytes" in st.session_state:
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state["scorer_pdf_bytes"],
                file_name="ats_resume_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_report",
            )

    with c2:
        st.download_button(
            "📄 Download Summary (.txt)",
            data=_summary_text(analysis),
            file_name="ats_summary.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_summary",
        )


def render() -> None:
    st.title("🎯 ATS Resume Scorer")
    st.markdown("Upload your resume — and optionally a job description — for a comprehensive analysis.")

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 📊 Analysis Options")
        st.info(
            "**General ATS Score**: resume only — overall compatibility.\n\n"
            "**JD Comparison**: resume + job description — targeted match analysis."
        )

    st.markdown("---")

    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
    )

    st.markdown("---")

    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    st.markdown("---")

    if not resume_file:
        st.info("👆 Upload your resume to begin.")
        # If we have a prior result in session, render it again.
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
        return

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("⚠️ Sign in from the sidebar to analyze a resume.")
        return

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")

    if not analyze:
        # Re-show previous result on rerun (e.g. after PDF generation).
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
        return

    # Fresh analysis — drop any cached PDF/result.
    st.session_state.pop("scorer_pdf_bytes", None)
    st.session_state.pop("scorer_analysis", None)

    job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""

    try:
        with st.spinner("Analyzing your resume... this can take 10–30 seconds."):
            analysis = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=access_token,
                job_description=job_description,
            )
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    st.session_state["scorer_analysis"] = analysis
    st.success("✅ Analysis complete!")
    display_results_dashboard(analysis)
    _render_export_buttons(analysis)
