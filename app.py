from __future__ import annotations

import html
import io
import json
import re
import time
from typing import Any

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# Smart Waste Management | Gemini Vision
# Main app entry point: python -m streamlit run app.py
# -----------------------------------------------------------------------------

APP_TITLE = "Smart Waste Management"
MAX_UPLOAD_MB = 8
MAX_IMAGE_SIDE = 1200
MODEL_CANDIDATES = (
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
)

st.set_page_config(
    page_title=f"{APP_TITLE} | AI Waste Sorter",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# A lightweight custom theme that works with Streamlit's standard components.
st.markdown(
    """
    <style>
      :root {
        --sw-bg: #07111c;
        --sw-panel: #0d1b29;
        --sw-panel-2: #102335;
        --sw-line: rgba(148, 190, 204, .16);
        --sw-text: #edf7f5;
        --sw-muted: #9bb3bd;
        --sw-green: #34d399;
        --sw-cyan: #67e8f9;
      }
      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(ellipse at 12% 0%, rgba(16, 185, 129, .12), transparent 33%),
          radial-gradient(ellipse at 95% 12%, rgba(14, 165, 233, .10), transparent 30%),
          var(--sw-bg);
        color: var(--sw-text);
      }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stSidebar"] {
        background: #091724;
        border-right: 1px solid var(--sw-line);
      }
      .block-container { max-width: 1440px; padding-top: 1.7rem; padding-bottom: 2.4rem; }
      h1, h2, h3, p, label { color: var(--sw-text); }
      .sw-hero {
        border: 1px solid rgba(103, 232, 249, .20);
        border-radius: 22px;
        padding: 1.55rem 1.7rem;
        margin-bottom: 1.1rem;
        background: linear-gradient(115deg, rgba(16, 185, 129, .15), rgba(14, 165, 233, .10) 58%, rgba(15, 23, 42, .70));
        box-shadow: 0 16px 48px rgba(0,0,0,.16);
      }
      .sw-eyebrow {
        color: #6ee7b7; font-size: .76rem; font-weight: 800;
        letter-spacing: .15em; text-transform: uppercase; margin-bottom: .45rem;
      }
      .sw-hero-title { font-size: clamp(1.8rem, 4vw, 2.65rem); line-height: 1.08; font-weight: 850; margin: 0; color: #f0fdfa; }
      .sw-hero-copy { color: #b7ccd2; font-size: 1rem; margin: .65rem 0 0 0; max-width: 760px; }
      .sw-chip {
        display: inline-block; border: 1px solid rgba(110,231,183,.25);
        background: rgba(16,185,129,.10); color: #a7f3d0;
        padding: .34rem .68rem; border-radius: 999px; font-size: .76rem; font-weight: 700;
        margin: .9rem .35rem 0 0;
      }
      .sw-section-kicker { color: #6ee7b7; text-transform: uppercase; font-size: .72rem; font-weight: 800; letter-spacing: .13em; }
      .sw-panel-title { color: #f0fdfa; font-size: 1.18rem; font-weight: 800; margin: .12rem 0 .55rem 0; }
      .sw-muted { color: var(--sw-muted); }
      .sw-object {
        border: 1px solid rgba(52,211,153,.22); border-radius: 17px;
        background: linear-gradient(135deg, rgba(16,185,129,.11), rgba(13,27,41,.9));
        padding: 1.05rem 1.1rem; margin: .6rem 0 1rem 0;
      }
      .sw-object-name { color: #f0fdfa; font-size: 1.55rem; font-weight: 850; line-height: 1.2; }
      .sw-label { color: #8daab5; text-transform: uppercase; font-size: .68rem; font-weight: 800; letter-spacing: .11em; }
      .sw-value { color: #e6f5f2; font-size: .98rem; margin-top: .18rem; }
      .sw-step {
        border-left: 3px solid #34d399; background: rgba(16,185,129,.065);
        border-radius: 0 10px 10px 0; padding: .6rem .8rem; margin: .45rem 0;
        color: #e1efed;
      }
      .sw-note { color: #9bb3bd; font-size: .82rem; }
      [data-testid="stFileUploader"] section {
        border: 1px dashed rgba(110,231,183,.4); border-radius: 14px;
        background: rgba(16,185,129,.035);
      }
      [data-testid="stImage"] img { border-radius: 14px; }
      .stButton button[kind="primary"] {
        border: 0; border-radius: 12px; font-weight: 800;
        background: linear-gradient(90deg, #059669, #0d9488);
        color: white; min-height: 2.9rem;
      }
      .stButton button[kind="primary"]:hover { border: 0; filter: brightness(1.08); }
      [data-testid="stMetric"] {
        background: rgba(13,27,41,.8); border: 1px solid var(--sw-line);
        padding: .8rem .9rem; border-radius: 13px;
      }
      [data-testid="stMetricLabel"] { color: #9bb3bd; }
      [data-testid="stMetricValue"] { color: #ecfdf5; }
      hr { border-color: var(--sw-line); }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_api_key() -> str:
    """Read the Gemini key from Streamlit secrets without displaying it."""
    try:
        value = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        value = ""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or "PASTE_" in value or "YOUR_GEMINI_API_KEY" in value:
        return ""
    return value


def prepare_image(raw_bytes: bytes) -> tuple[bytes, str, Image.Image]:
    """Validate, orient, resize and JPEG-encode the uploaded image."""
    with Image.open(io.BytesIO(raw_bytes)) as source:
        source.verify()
    with Image.open(io.BytesIO(raw_bytes)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        # Composite transparent PNGs on white so the model sees a clean image.
        white = Image.new("RGBA", image.size, "white")
        white.alpha_composite(image)
        image = white.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        preview = image.copy()
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True)
    return output.getvalue(), "image/jpeg", preview


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON, tolerating an accidental Markdown code fence."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Gemini returned an unexpected response format.")
    return data


def analyze_with_gemini(image_bytes: bytes, mime_type: str, api_key: str) -> tuple[dict[str, Any], str]:
    """Send an image to Gemini; retry transient errors and switch models automatically."""
    prompt = """You are an image-recognition and waste-sorting assistant for a student Smart Waste Management project in India.
Inspect the attached image carefully. Identify the main visible object as specifically as the image supports.
Do not guess a brand, exact model, hidden component, or material that cannot be seen.

Return ONLY valid JSON with these keys:
{
  "identified_object": "specific everyday object name",
  "likely_materials": ["material 1", "material 2"],
  "waste_category": "one main category",
  "category_reason": "short explanation",
  "disposal_steps": ["step 1", "step 2", "step 3"],
  "special_handling": "special handling advice or Not usually needed",
  "reuse_tip": "one practical reuse or repair suggestion",
  "identification_quality": "Clear or Uncertain",
  "identification_note": "brief note about what can or cannot be confirmed"
}

Choose waste_category from exactly one of:
Plastic; Metal; Glass; Paper/Cardboard; Organic/Wet Waste; E-waste; Battery/Hazardous Waste; Textile; General/Residual Waste.

Rules:
- If the object is an electronic device, circuit board, cable, charger or computer part, choose E-waste.
- If it contains a removable battery, mention that it should be separated and taken to an authorised battery collection point where available.
- Never advise putting electronics, batteries, chemicals or broken glass in ordinary mixed recycling.
- For metal drink bottles, identify stainless steel only when the visible object reasonably supports that description; otherwise say likely metal.
- Disposal services vary by city. Keep steps practical and remind users to follow local municipal or authorised collection guidance.
- Do not include a numerical confidence percentage.
- Use concise, student-friendly wording.
"""

    client = genai.Client(api_key=api_key)
    capacity_errors: list[str] = []
    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        for model_name in MODEL_CANDIDATES:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[prompt, image_part],
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            max_output_tokens=650,
                            response_mime_type="application/json",
                        ),
                    )
                    text = response.text or ""
                    if not text.strip():
                        raise RuntimeError(
                            f"{model_name} returned no text. Try a brighter photo with one main object."
                        )
                    return _extract_json(text), model_name
                except Exception as exc:
                    detail = f"{type(exc).__name__}: {exc}"
                    upper = detail.upper()
                    retryable = any(
                        token in upper
                        for token in (
                            "503",
                            "UNAVAILABLE",
                            "429",
                            "RESOURCE_EXHAUSTED",
                            "502",
                            "500",
                            "DISCONNECTED",
                            "REMOTEPROTOCOLERROR",
                            "CONNECTERROR",
                            "TIMEOUT",
                        )
                    )
                    if retryable:
                        if attempt == 0:
                            time.sleep(2)
                            continue
                        capacity_errors.append(f"{model_name}: {detail[:500]}")
                        break
                    raise
        raise RuntimeError(
            "Gemini's available models are currently busy or rate-limited. "
            "Please wait a minute and try again. Details: " + " | ".join(capacity_errors)
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def render_result(data: dict[str, Any], model_name: str) -> None:
    object_name = str(data.get("identified_object") or "Object not confidently identified")
    materials = data.get("likely_materials", [])
    if isinstance(materials, str):
        materials = [materials]
    if not isinstance(materials, list):
        materials = [str(materials)]
    materials = [str(item) for item in materials if str(item).strip()]

    category = str(data.get("waste_category") or "General/Residual Waste")
    reason = str(data.get("category_reason") or "Based on the visible object and likely material.")
    quality = str(data.get("identification_quality") or "Uncertain")
    note = str(data.get("identification_note") or "Check the object physically before disposal.")

    st.markdown('<div class="sw-section-kicker">AI analysis complete</div>', unsafe_allow_html=True)
    safe_object_name = html.escape(object_name)
    st.markdown(
        f'<div class="sw-object"><div class="sw-label">Identified object</div><div class="sw-object-name">{safe_object_name}</div></div>',
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(2)
    with metric_cols[0]:
        st.metric("Waste category", category)
    with metric_cols[1]:
        st.metric("Identification", quality)

    st.markdown("#### Likely material")
    if materials:
        st.write(" · ".join(materials))
    else:
        st.write("Material could not be confirmed from the image.")
    st.caption(reason)

    st.markdown("#### Recommended disposal")
    steps = data.get("disposal_steps", [])
    if isinstance(steps, str):
        steps = [steps]
    if not isinstance(steps, list):
        steps = [str(steps)]
    if steps:
        for index, step in enumerate(steps, start=1):
            safe_step = html.escape(str(step))
            st.markdown(f'<div class="sw-step"><b>{index}.</b> {safe_step}</div>', unsafe_allow_html=True)
    else:
        st.write("Follow local municipal collection guidance for this item.")

    special = str(data.get("special_handling") or "Not usually needed")
    reuse = str(data.get("reuse_tip") or "Consider repair or reuse before disposal.")
    with st.expander("Extra guidance"):
        st.markdown(f"**Special handling:** {html.escape(special)}")
        st.markdown(f"**Reuse / repair idea:** {html.escape(reuse)}")
        st.markdown(f"**Identification note:** {html.escape(note)}")

    st.caption(f"Recognition model: {model_name}")
    st.caption("AI guidance can be imperfect. Confirm the material and follow your local municipal rules, especially for e-waste, batteries and hazardous items.")


# -----------------------------------------------------------------------------
# Sidebar and page header
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# ♻️ WasteWise AI")
    st.caption("A Smart Waste Management project")
    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "**01 · Upload**\n\nChoose a clear photo of one item.\n\n"
        "**02 · Identify**\n\nGemini Vision recognises the object and likely material.\n\n"
        "**03 · Sort**\n\nGet a waste category and practical disposal steps."
    )
    st.divider()
    st.markdown("### Supported examples")
    st.markdown("- Bottles and containers\n- Paper and cardboard\n- Metal objects\n- Electronics and circuit boards\n- Batteries and household items")
    st.divider()
    st.caption("The old six-class `.keras` model is kept in the `legacy` folder for reference. This app uses Gemini Vision.")

st.markdown(
    """
    <div class="sw-hero">
      <div class="sw-eyebrow">AI-powered waste sorting · Student project</div>
      <h1 class="sw-hero-title">Smart Waste Management</h1>
      <p class="sw-hero-copy">Know what an object is, what it may be made of, and how to dispose of it more responsibly.</p>
      <span class="sw-chip">✦ Gemini Vision</span>
      <span class="sw-chip">♻ Material-aware sorting</span>
      <span class="sw-chip">⌁ Practical disposal tips</span>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = get_api_key()
if not api_key:
    st.warning("Gemini API key not configured yet.")
    st.code('GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"', language="toml")
    st.caption("Open `.streamlit/secrets.toml`, replace the placeholder with your key, save the file, and restart the app. Never share the key.")

left, right = st.columns([0.95, 1.05], gap="large")

with left:
    st.markdown('<div class="sw-section-kicker">Step 1 · Upload</div>', unsafe_allow_html=True)
    st.markdown('<div class="sw-panel-title">Choose an object photo</div>', unsafe_allow_html=True)
    st.markdown('<p class="sw-muted">Use good lighting and keep the main object in focus.</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload JPG, JPEG, PNG or WEBP",
        type=["jpg", "jpeg", "png", "webp"],
        help=f"Maximum upload size: {MAX_UPLOAD_MB} MB.",
        label_visibility="collapsed",
    )

    prepared_bytes: bytes | None = None
    prepared_mime: str | None = None
    upload_token = None

    if uploaded_file is not None:
        upload_token = f"{uploaded_file.name}:{uploaded_file.size}"
        if uploaded_file.size > MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"This image is larger than {MAX_UPLOAD_MB} MB. Please choose a smaller image.")
        else:
            try:
                prepared_bytes, prepared_mime, preview = prepare_image(uploaded_file.getvalue())
                st.image(preview, caption=f"Preview · {uploaded_file.name}", width="stretch")
                st.caption(f"{uploaded_file.size / 1024:.0f} KB · Image prepared for AI analysis")
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
                st.error("This file is not a valid supported image. Please try another JPG or PNG.")

    # Clear stale results when the user selects a different image.
    if st.session_state.get("upload_token") != upload_token:
        st.session_state["upload_token"] = upload_token
        st.session_state.pop("analysis_result", None)
        st.session_state.pop("analysis_error", None)

    can_analyze = prepared_bytes is not None and bool(api_key)
    identify_clicked = st.button(
        "✦  Identify this object",
        type="primary",
        width="stretch",
        disabled=not can_analyze,
    )
    if not api_key:
        st.caption("Add your Gemini API key to enable identification.")
    elif prepared_bytes is None:
        st.caption("Upload an image to enable the button.")
    else:
        st.caption("The app will try a backup Gemini model automatically if the first model is busy.")

with right:
    st.markdown('<div class="sw-section-kicker">Step 2 · Understand & sort</div>', unsafe_allow_html=True)
    st.markdown('<div class="sw-panel-title">Your AI waste report</div>', unsafe_allow_html=True)
    st.markdown('<p class="sw-muted">Object name, material, category and next steps appear here.</p>', unsafe_allow_html=True)

    if identify_clicked and prepared_bytes is not None and api_key:
        with st.spinner("Analysing the photo with Gemini Vision…"):
            try:
                result_data, model_used = analyze_with_gemini(prepared_bytes, prepared_mime or "image/jpeg", api_key)
                st.session_state["analysis_result"] = {
                    "data": result_data,
                    "model": model_used,
                }
                st.session_state.pop("analysis_error", None)
            except Exception as exc:
                st.session_state["analysis_error"] = f"{type(exc).__name__}: {exc}"
                st.session_state.pop("analysis_result", None)

    if st.session_state.get("analysis_error"):
        error_message = st.session_state["analysis_error"]
        if "503" in error_message or "UNAVAILABLE" in error_message.upper():
            st.error("Gemini's models are temporarily busy.")
            st.info("Wait about a minute, then click **Identify this object** again. The app has already tried its backup model.")
        elif "429" in error_message or "RESOURCE_EXHAUSTED" in error_message.upper():
            st.error("The Gemini API request limit or quota has been reached.")
            st.info("Check your usage and quota in Google AI Studio before retrying.")
        elif any(item in error_message.upper() for item in ("API_KEY_INVALID", "UNAUTHENTICATED", "401", "403")):
            st.error("Google rejected the API key. Check `.streamlit/secrets.toml` and confirm that the key is active.")
        else:
            st.error("Gemini could not analyse this image. See the technical details below.")
        with st.expander("Technical details", expanded=True):
            st.code(error_message[:2500])
    elif st.session_state.get("analysis_result"):
        saved = st.session_state["analysis_result"]
        render_result(saved["data"], saved["model"])
    else:
        st.markdown(
            """
            <div class="sw-object" style="border-color: rgba(148,190,204,.16); background: rgba(13,27,41,.48); padding: 1.4rem;">
              <div style="font-size:2rem; margin-bottom:.5rem;">🧠</div>
              <div style="font-size:1.05rem; font-weight:800; color:#e6f5f2;">Your waste report will appear here</div>
              <div class="sw-note" style="margin-top:.45rem;">Upload a photo on the left and select “Identify this object” to begin.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()
footer_left, footer_right = st.columns([2, 1])
with footer_left:
    st.caption("♻️ Smart Waste Management · Gemini Vision prototype")
with footer_right:
    st.caption("Use local authorised collection guidance for final disposal decisions.")