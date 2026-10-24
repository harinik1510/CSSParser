import json
from pathlib import Path

import streamlit as st

from parser import parse_css


st.set_page_config(
    page_title="CSS Insight Parser",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --accent: #818cf8;
    --accent2: #38bdf8;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(ellipse at 10% 0%, #18274b 0%, transparent 42%),
        radial-gradient(ellipse at 95% 10%, #241b49 0%, transparent 35%),
        #080d19;
}

.block-container {
    max-width: 1180px;
    padding-top: 2.3rem;
    padding-bottom: 3rem;
}

.hero {
    padding: 30px 32px;
    border: 1px solid #334363;
    border-radius: 22px;
    background: linear-gradient(120deg, #172747, #17172f 75%);
    margin-bottom: 26px;
}

.eyebrow {
    color: #a5b4fc;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 2px;
    font-weight: 700;
    margin-bottom: 12px;
}

.hero h1 {
    color: #f8fafc;
    font-size: clamp(30px, 4vw, 43px);
    line-height: 1.2;
    font-weight: 800;
    margin: 0 0 12px 0;
}

.hero p {
    color: #bac7dc;
    font-size: 15px;
    line-height: 1.8;
    margin: 0;
    max-width: 700px;
}

.pill {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 30px;
    border: 1px solid #46547b;
    background: #242b4a;
    color: #dbeafe;
    font-size: 12px;
    margin: 18px 6px 0 0;
}

.section-title {
    font-size: 20px;
    font-weight: 700;
    color: #f1f5f9;
    margin: 12px 0 6px;
}

.section-subtitle {
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 18px;
}

div[data-testid="stFileUploader"] {
    border: 1px dashed #596b95;
    border-radius: 16px;
    background: rgba(21, 33, 57, 0.72);
    padding: 16px;
}

div[data-testid="stFileUploader"] section {
    background: transparent;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #151f35, #101727);
    border: 1px solid #2a3956;
    border-radius: 15px;
    padding: 17px 18px;
}

div[data-testid="stMetricLabel"] {
    color: #a5b4cc;
}

div[data-testid="stMetricValue"] {
    color: #e0e7ff;
    font-weight: 800;
}

div.stButton > button {
    border-radius: 11px;
    min-height: 45px;
    font-weight: 700;
    border: 1px solid #6477e8;
    transition: all 0.2s ease;
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(100deg, #6366f1, #3b82f6);
    color: white;
}

div.stButton > button:hover {
    border-color: #a5b4fc;
    transform: translateY(-1px);
}

div[data-testid="stDownloadButton"] button {
    background: linear-gradient(100deg, #4f46e5, #2563eb);
    color: white;
    border: none;
    border-radius: 11px;
    font-weight: 700;
    min-height: 48px;
}

div[data-testid="stCode"] {
    border: 1px solid #2c3b59;
    border-radius: 14px;
}

hr {
    border-color: #293650;
}

.footer {
    text-align: center;
    color: #71809b;
    font-size: 12px;
    padding-top: 28px;
}
</style>
""", unsafe_allow_html=True)


SAMPLE_CSS = """
/* Sample stylesheet */
body {
    font-family: Arial, sans-serif;
    font-size: 16px;
    color: #333333;
    line-height: 1.5;
}

.card, .panel {
    background-color: #ffffff;
    padding: 20px;
    border-color: rgb(200, 200, 200);
}

button:hover {
    color: white;
    font-weight: bold;
}

@media (max-width: 768px) {
    .card {
        font-size: 14px;
    }
}
"""


def clear_results():
    st.session_state.pop("parsed_result", None)
    st.session_state.pop("parsed_filename", None)


st.markdown("""
<div class="hero">
    <div class="eyebrow">DEVELOPER TOOLKIT &nbsp; / &nbsp; CSS ANALYSIS</div>
    <h1>CSS Insight Parser </h1>
    <p>
        Turn your stylesheet into structured, meaningful data.
        Extract selectors, declarations, colors and typography,
        then export everything into a clean JSON report.
    </p>
    <span class="pill">✦ Python powered</span>
    <span class="pill">⌘ Structured JSON</span>
    <span class="pill">↗ Instant export</span>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="section-title">&nbsp; Upload stylesheet</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-subtitle">Choose a CSS file from your device or try the sample stylesheet.</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Choose a CSS file",
    type=["css"],
    help="Only .css files are supported.",
    key="css_uploader",
)

sample_col, info_col = st.columns([1, 2])
with sample_col:
    use_sample = st.button("✦ Try sample CSS", use_container_width=True)
with info_col:
    if uploaded_file is not None:
        st.caption(f"Selected file: {uploaded_file.name}")
    else:
        st.caption("Supports selectors, nested media rules, colors and typography.")

if use_sample:
    st.session_state["use_sample"] = True
    clear_results()

if uploaded_file is not None:
    st.session_state["use_sample"] = False

parse_clicked = st.button(
    "⚡ Parse CSS",
    type="primary",
    use_container_width=True,
)

if parse_clicked:
    try:
        if st.session_state.get("use_sample", False):
            css_text = SAMPLE_CSS
            filename = "sample.css"
        elif uploaded_file is not None:
            css_text = uploaded_file.getvalue().decode("utf-8-sig")
            filename = uploaded_file.name
        else:
            clear_results()
            st.warning("Upload a CSS file or select Try sample CSS.")
            st.stop()

        if not css_text.strip():
            clear_results()
            st.warning("The selected CSS file is empty.")
            st.stop()

        with st.spinner("Analyzing stylesheet..."):
            result = parse_css(css_text, filename=filename)

        st.session_state["parsed_result"] = result
        st.session_state["parsed_filename"] = filename
        st.success("Parsing complete — your report is ready.")

    except UnicodeDecodeError:
        clear_results()
        st.error("Could not decode the file. Please use UTF-8 encoded CSS.")
    except Exception as exc:
        clear_results()
        st.error(f"Could not parse the CSS file: {exc}")

if "parsed_result" in st.session_state:
    result = st.session_state["parsed_result"]
    filename = st.session_state["parsed_filename"]
    stats = result["statistics"]

    st.divider()
    st.markdown(
        '<div class="section-title"> &nbsp; Analysis overview</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">A quick breakdown of your stylesheet.</div>',
        unsafe_allow_html=True,
    )

    metrics = [
        ("CSS Rules", stats["rules"]),
        ("Selectors", stats["selectors"]),
        ("Declarations", stats["declarations"]),
        ("Unique Colors", stats["unique_colors"]),
        ("Properties", stats["unique_properties"]),
    ]
    cols = st.columns(5)
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)

    st.markdown(
        '<div class="section-title"> &nbsp; Structured JSON</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Inspect the extracted data before exporting it.</div>',
        unsafe_allow_html=True,
    )

    json_text = json.dumps(result, indent=4, ensure_ascii=False)
    with st.container(border=True):
        st.caption(f"FILE: {filename}  •  FORMAT: JSON")
        st.code(json_text, language="json", line_numbers=True)

    st.markdown(
        '<div class="section-title"> &nbsp; Export report</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Download the complete structured report for further use.</div>',
        unsafe_allow_html=True,
    )

    download_name = f"{Path(filename).stem}_parsed.json"
    st.download_button(
        "⬇  Download JSON report",
        data=json_text.encode("utf-8"),
        file_name=download_name,
        mime="application/json",
        type="primary",
        use_container_width=True,
    )

st.markdown("""
<div class="footer">
    CSS INSIGHT PARSER &nbsp; • &nbsp; BUILT WITH PYTHON + STREAMLIT
</div>
""", unsafe_allow_html=True)
