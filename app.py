import streamlit as st
import pymupdf as fitz
import base64
from openai import OpenAI
import streamlit.components.v1 as components
import io
import time
from PIL import Image, ImageEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Markup Auditor | Delta Verification Engine", layout="wide", initial_sidebar_state="expanded")

# --- PULSEBOARD / VERCEL / RAYCAST ULTRA-MODERN DARK UI ---
st.markdown("""
   <style>
       @import url('https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DPlus%2BJakarta%2BSans%3Awght%40300%3B400%3B500%3B600%3B700%3B800%3B900%26family%3DJetBrains%2BMono%3Awght%40400%3B500%3B600%26display%3Dswap&data=05%7C02%7Ceomar%40cumminscederberg.com%7C259d5dc390d24ec1f0ca08def890a735%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221497360305017%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=1x%2BZe5YDxOKefZcmv6yei3w2Ac%2BeROZeaIWYLLCVRHo%3D&reserved=0');

       html, body, .stApp {
           background-color: #030712 !important;
           color: #f8fafc !important;
           font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
       }

       /* Background Radial Glow Effect */
       .stApp {
           background-image:
               radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.12) 0%, transparent 40%),
               radial-gradient(circle at 85% 20%, rgba(147, 51, 234, 0.08) 0%, transparent 45%) !important;
       }

       /* Top Navigation Bar */
       .top-nav {
           display: flex;
           justify-content: space-between;
           align-items: center;
           padding: 12px 24px;
           background: rgba(15, 23, 42, 0.6);
           backdrop-filter: blur(12px);
           border: 1px solid rgba(255, 255, 255, 0.08);
           border-radius: 12px;
           margin-bottom: 32px;
       }

       .nav-brand {
           display: flex;
           align-items: center;
           gap: 10px;
           font-weight: 800;
           font-size: 1.1rem;
           letter-spacing: -0.02em;
           color: #ffffff;
       }

       .nav-badge {
           background: rgba(59, 130, 246, 0.15);
           color: #60a5fa;
           border: 1px solid rgba(96, 165, 250, 0.3);
           padding: 2px 10px;
           border-radius: 20px;
           font-size: 0.72rem;
           font-weight: 600;
       }

       .nav-links {
           display: flex;
           gap: 24px;
           font-size: 0.85rem;
           color: #94a3b8;
           font-weight: 500;
       }

       /* PulseBoard Hero Typography */
       .hero-container {
           margin: 20px 0 36px 0;
           max-width: 900px;
       }

       .hero-title {
           font-size: 3.8rem;
           font-weight: 900;
           line-height: 1.05;
           letter-spacing: -0.03em;
           color: #ffffff;
           margin: 0 0 16px 0;
           text-transform: uppercase;
       }

       .gradient-text {
           background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%);
           -webkit-background-clip: text;
           -webkit-text-fill-color: transparent;
       }

       .hero-subtitle {
           font-size: 1.05rem;
           color: #94a3b8;
           line-height: 1.6;
           font-weight: 400;
           max-width: 680px;
           margin-bottom: 28px;
       }

       /* Metric Counters Row */
       .metrics-row {
           display: flex;
           gap: 40px;
           padding-top: 12px;
           border-top: 1px solid rgba(255, 255, 255, 0.08);
           margin-bottom: 32px;
       }

       .metric-item {
           display: flex;
           flex-direction: column;
       }

       .metric-val {
           font-size: 1.5rem;
           font-weight: 800;
           color: #ffffff;
           letter-spacing: -0.02em;
       }

       .metric-lbl {
           font-size: 0.75rem;
           color: #64748b;
           font-weight: 500;
           text-transform: uppercase;
           letter-spacing: 0.05em;
           margin-top: 2px;
       }

       /* Card Section Styling */
       .card-label {
           font-family: 'JetBrains Mono', monospace;
           font-size: 0.78rem;
           font-weight: 600;
           color: #60a5fa;
           letter-spacing: 0.08em;
           text-transform: uppercase;
           margin-bottom: 10px;
           display: flex;
           align-items: center;
           gap: 8px;
       }

       /* File Uploader Custom Styling */
       [data-testid="stFileUploaderDropzone"] {
           background: rgba(15, 23, 42, 0.5) !important;
           border: 1px solid rgba(255, 255, 255, 0.1) !important;
           border-radius: 12px !important;
           padding: 24px !important;
           transition: all 0.2s ease-in-out;
       }

       [data-testid="stFileUploaderDropzone"]:hover {
           border-color: #3b82f6 !important;
           background: rgba(15, 23, 42, 0.8) !important;
           box-shadow: 0 0 25px rgba(59, 130, 246, 0.15);
       }

       [data-testid="stFileUploaderDropzone"] * {
           color: #94a3b8 !important;
       }

       /* Text Area Styling */
       div[data-baseweb="textarea"] {
           background-color: rgba(15, 23, 42, 0.5) !important;
           border: 1px solid rgba(255, 255, 255, 0.1) !important;
           border-radius: 12px !important;
       }

       div[data-baseweb="textarea"] textarea {
           color: #f8fafc !important;
           background-color: transparent !important;
           font-family: 'Plus Jakarta Sans', sans-serif !important;
           font-size: 0.9rem !important;
       }

       /* PulseBoard CTA Button (Centered Pill) */
       div.stButton > button {
           width: 100% !important;
           background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
           color: #ffffff !important;
           font-family: 'Plus Jakarta Sans', sans-serif !important;
           font-size: 0.95rem !important;
           font-weight: 700 !important;
           padding: 16px 32px !important;
           border-radius: 40px !important;
           border: 1px solid rgba(147, 197, 253, 0.3) !important;
           box-shadow: 0 10px 30px rgba(37, 99, 235, 0.35) !important;
           transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
           letter-spacing: 0.02em !important;
       }

       div.stButton > button:hover {
           background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
           box-shadow: 0 12px 40px rgba(59, 130, 246, 0.5) !important;
           transform: translateY(-2px);
       }

       /* Loader Box */
       .loader-box {
           display: flex;
           align-items: center;
           justify-content: center;
           gap: 16px;
           background: rgba(15, 23, 42, 0.8);
           border: 1px solid #3b82f6;
           padding: 20px;
           border-radius: 12px;
           margin: 24px 0;
           color: #60a5fa;
           font-family: 'JetBrains Mono', monospace;
           font-weight: 600;
           box-shadow: 0 0 30px rgba(59, 130, 246, 0.2);
       }

       /* Footer Logo Ticker Bar (PulseBoard Style) */
       .ticker-bar {
           margin-top: 60px;
           padding-top: 24px;
           border-top: 1px solid rgba(255, 255, 255, 0.06);
           display: flex;
           justify-content: space-around;
           align-items: center;
           opacity: 0.45;
           font-family: 'JetBrains Mono', monospace;
           font-size: 0.8rem;
           letter-spacing: 0.05em;
           color: #94a3b8;
       }
   </style>
""", unsafe_allow_html=True)

# PulseBoard Top Navigation Bar
st.markdown("""
   <div class="top-nav">
       <div class="nav-brand">
           <span style="color: #3b82f6; font-size: 1.3rem;">⚡</span>
           <span>MarkupAuditor</span>
           <span class="nav-badge">ENGINEERING V2.4</span>
       </div>
       <div class="nav-links">
           <span>Vector Engine</span>
           <span>QA/QC Pipeline</span>
           <span>CAD Delta</span>
           <span>Enterprise</span>
       </div>
   </div>
""", unsafe_allow_html=True)

# PulseBoard Hero Typography Section
st.markdown("""
   <div class="hero-container">
       <div class="hero-title">
           ENGINEERING<br>
           <span class="gradient-text">DIGITAL REDLINE</span><br>
           AUDITOR
       </div>
       <div class="hero-subtitle">
           Automated drawing comparison and intelligence engine. Upload Rev A markup sheets alongside Rev B revised drawing packages to detect, track, and verify CAD drafting modifications instantly.
       </div>
       <div class="metrics-row">
           <div class="metric-item">
               <span class="metric-val">100%</span>
               <span class="metric-lbl">Vector Annotations</span>
           </div>
           <div class="metric-item">
               <span class="metric-val">4-Quad</span>
               <span class="metric-lbl">High-Res Inspection</span>
           </div>
           <div class="metric-item">
               <span class="metric-val">GPT-4o</span>
               <span class="metric-lbl">Vision QA Engine</span>
           </div>
       </div>
   </div>
""", unsafe_allow_html=True)

# Safe API Key Fetching
api_key = None
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

col1, col2 = st.columns(2)

def process_pdf_with_annotations(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    images_full = []
    crops_per_page = []
    annots_per_page = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        images_full.append(img_data)

        page_annots = []
        for annot in page.annots():
            info = annot.info
            page_annots.append({
                "author": info.get("title", "").strip(),
                "content": info.get("content", "").strip(),
                "subject": info.get("subject", "").strip(),
                "type": annot.type[1] if isinstance(annot.type, tuple) else str(annot.type)
            })

        annots_per_page.append(page_annots)

        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        w, h = img.size
        page_crops = []

        quadrants = [
            (0, 0, int(w * 0.55), int(h * 0.55)),
            (int(w * 0.45), 0, w, int(h * 0.55)),
            (0, int(h * 0.45), int(w * 0.55), h),
            (int(w * 0.45), int(h * 0.45), w, h)
        ]

        for box in quadrants:
            crop_img = img.crop(box)
            enhancer = ImageEnhance.Contrast(crop_img)
            crop_img = enhancer.enhance(1.25)
            buf = io.BytesIO()
            crop_img.save(buf, format="PNG")
            page_crops.append(buf.getvalue())

        crops_per_page.append(page_crops)

    return images_full, crops_per_page, annots_per_page, len(doc)

def process_single_sheet(sheet_index, img_a_bytes, img_b_bytes, crops_a_list, crops_b_list, annots_a_list, user_notes, api_key_val):
    client = OpenAI(api_key=api_key_val)

    base64_a = base64.b64encode(img_a_bytes).decode('utf-8')
    base64_b = base64.b64encode(img_b_bytes).decode('utf-8')

    if annots_a_list and len(annots_a_list) > 0:
        annot_summary = f"\nEXTRACTED VECTOR ANNOTATIONS ON REV A SHEET {sheet_index+1}:\n"
        for idx, a in enumerate(annots_a_list):
            txt = a['content'] if a['content'] else "Graphic Markup / Callout Box"
            annot_summary += f"- Redline #{idx+1} ({a['type']}): \"{txt}\" (Subject: {a['subject']})\n"
    else:
        annot_summary = f"\nNO EMBEDDED PDF VECTOR ANNOTATIONS DETECTED ON SHEET {sheet_index+1}.\n"

    content_payload = [
        {"type": "text", "text": f"User Specific Directives: {user_notes}\n{annot_summary}\nCompare Sheet {sheet_index+1} Rev A against Rev B."}
    ]

    content_payload.append({"type": "text", "text": "REV A OVERALL SHEET (Redlines):"})
    content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_a}", "detail": "high"}})

    content_payload.append({"type": "text", "text": "REV B OVERALL SHEET (Revised Output):"})
    content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_b}", "detail": "high"}})

    labels = ["Top-Left Quad", "Top-Right Quad", "Bottom-Left Quad", "Bottom-Right Quad"]
    for i in range(min(len(crops_a_list), 4)):
        crop_a_b64 = base64.b64encode(crops_a_list[i]).decode('utf-8')
        crop_b_b64 = base64.b64encode(crops_b_list[i]).decode('utf-8')
        content_payload.append({"type": "text", "text": f"HIGH-RES DETAILED COMPARISON [{labels[i]}] - REV A vs REV B:"})
        content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{crop_a_b64}", "detail": "high"}})
        content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{crop_b_b64}", "detail": "high"}})

    system_prompt = (
        f"You are a Senior Structural & Civil Engineering QA/QC Inspector auditing Sheet {sheet_index+1}.\n\n"
        "STRICT AUDIT & SHEET ISOLATION RULES:\n"
        f"1. Evaluate ONLY Sheet {sheet_index+1}. DO NOT cross-reference or invent directives from other sheets or previous drawings.\n"
        "2. Check the EXTRACTED VECTOR ANNOTATIONS layer provided above for this specific sheet.\n"
        "3. IF NO REDLINES OR ANNOTATIONS EXIST ON THIS SHEET (in metadata or visually), YOU MUST SET STATUS TO 'NO MARKUPS DETECTED ON THIS SHEET' AND DO NOT INVENT CALLOUTS.\n"
        "4. If markups exist, evaluate physical CAD drafting execution in Rev B.\n"
        "5. Read the Title Block on the bottom right of the image to state the true Sheet Number (e.g., CM-1.0, CM-1.1).\n\n"
        "FORMAT YOUR OUTPUT EXACTLY AS FOLLOWS:\n\n"
        "### Engineering Callout & Design Delta Audit\n\n"
        "* **Location & Drawing Ref**: [Grid Lines / Detail Ref / Title Block Sheet Number]\n"
        "  * **Engineer Redline Directive**: [Exact directive on THIS sheet, or 'None']\n"
        "  * **Rev B Visual Geometry Verification**: [Observed physical CAD changes in Rev B]\n"
        "  * **Status**: FULLY ADDRESSED (or MISSED / PARTIALLY ADDRESSED / NO MARKUPS DETECTED ON THIS SHEET)\n"
        "  * **QA/QC Technical Notes**: [Technical notes]\n"
    )

    max_retries = 5
    backoff = 10
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_payload}
                ],
                max_tokens=2500
            )
            return sheet_index, response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 1.5
            else:
                raise e

def render_panzoom_image(img_bytes, caption, key_id):
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Funpkg.com%2F%40panzoom%2Fpanzoom%404.5.1%2Fdist%2Fpanzoom.min.js&data=05%7C02%7Ceomar%40cumminscederberg.com%7C259d5dc390d24ec1f0ca08def890a735%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221497360341557%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=75ywWcWdExZ2scF70ms0p4qMO1NlZNN1vouFfB6uZYY%3D&reserved=0"></script>
        <style>
            body {{ margin: 0; padding: 0; background-color: #030712; font-family: sans-serif; color: #ffffff; overflow: hidden; }}
            .container {{ position: relative; width: 100%; height: 520px; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; background: #000000; overflow: hidden; }}
            .controls {{ position: absolute; top: 12px; right: 12px; z-index: 100; display: flex; gap: 6px; }}
            .btn {{ background: #0f172a; color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.15); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600; font-family: sans-serif; }}
            .btn:hover {{ background: #3b82f6; color: #fff; }}
            .caption {{ position: absolute; bottom: 12px; left: 12px; z-index: 100; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; color: #60a5fa; border: 1px solid rgba(255, 255, 255, 0.1); }}
            .pan-target {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; cursor: grab; }}
            .pan-target img {{ max-width: 98%; max-height: 98%; object-fit: contain; }}
            .pan-target:active {{ cursor: grabbing; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="caption">{caption}</div>
            <div class="controls">
                <button class="btn" id="zoom-in-{key_id}">Zoom In</button>
                <button class="btn" id="zoom-out-{key_id}">Zoom Out</button>
                <button class="btn" id="reset-{key_id}">Reset</button>
            </div>
            <div class="pan-target" id="pan-target-{key_id}">
                <img id="img-{key_id}" src="data:image/png;base64,{b64_img}" />
            </div>
        </div>
        <script>
            const elem = document.getElementById('pan-target-{key_id}');
            const panzoom = Panzoom(elem, {{ maxScale: 8, minScale: 0.8, contain: 'outside' }});
            elem.parentElement.addEventListener('wheel', panzoom.zoomWithWheel);
            document.getElementById('zoom-in-{key_id}').addEventListener('click', panzoom.zoomIn);
            document.getElementById('zoom-out-{key_id}').addEventListener('click', panzoom.zoomOut);
            document.getElementById('reset-{key_id}').addEventListener('click', panzoom.reset);
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=535)

with col1:
    st.markdown("<div class='card-label'><span>01 //</span> ENGINEER MARKUPS (REV A)</div>", unsafe_allow_html=True)
    rev_a_file = st.file_uploader("Upload Rev A PDF", type=["pdf"], key="a", label_visibility="collapsed")

with col2:
    st.markdown("<div class='card-label'><span>02 //</span> REVISED DRAWING SET (REV B)</div>", unsafe_allow_html=True)
    rev_b_file = st.file_uploader("Upload Rev B PDF", type=["pdf"], key="b", label_visibility="collapsed")

st.markdown("<div class='card-label' style='margin-top: 16px;'><span>03 //</span> CRITICAL INSPECTION DIRECTIVES (OPTIONAL)</div>", unsafe_allow_html=True)
markup_notes = st.text_area(
    "Notes",
    placeholder="e.g., Verify beam spacing adjustments @ 8'-6\" OC and removal of 2 interior structural beams.",
    label_visibility="collapsed"
)

st.write("")

# Centered Pill Launch Button
btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])

with btn_col2:
    run_audit = st.button("Start Verification Process →")

if run_audit and rev_a_file and rev_b_file:
    if not api_key:
        st.error("Missing API Key: Enter your OpenAI Key in the sidebar or Streamlit secrets.")
    else:
        loader_placeholder = st.empty()
        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span>Extracting Vector Layers & Generating High-Res Quadrant Grids...</span>
            </div>
        """, unsafe_allow_html=True)

        images_a, crops_a, annots_a, count_a = process_pdf_with_annotations(rev_a_file)
        images_b, crops_b, annots_b, count_b = process_pdf_with_annotations(rev_b_file)

        total_pages = min(count_a, count_b)
        results_dict = {}
        sheet_names = [f"Sheet {i+1}" for i in range(total_pages)]

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_index = {}
            for i in range(total_pages):
                f = executor.submit(
                    process_single_sheet, i, images_a[i], images_b[i], crops_a[i], crops_b[i], annots_a[i], markup_notes, api_key
                )
                future_to_index[f] = i
                time.sleep(0.5)

            completed_count = 0
            for future in as_completed(future_to_index):
                idx, result_text = future.result()
                results_dict[idx] = result_text
                completed_count += 1
                loader_placeholder.markdown(f"""
                    <div class='loader-box'>
                        <span>Auditing Sheet Geometry... Processed {completed_count} of {total_pages} Sheets</span>
                    </div>
                """, unsafe_allow_html=True)

        ordered_results = [results_dict[i] for i in range(total_pages)]

        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span>Synthesizing Executive Delta Report...</span>
            </div>
        """, unsafe_allow_html=True)

        full_audit_text = "\n\n".join([f"**Sheet {idx+1}:**\n" + res for idx, res in enumerate(ordered_results)])
        client = OpenAI(api_key=api_key)

        missed_summary = ""
        for attempt in range(5):
            try:
                res_missed = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Chief Structural QA/QC Manager. Synthesize ONLY the MISSED or INCOMPLETE markups across all sheets.\n"
                                "Format as bullet points categorized by sheet number.\n"
                                "Include the requested engineering directive and why physical drafting failed in Rev B. If zero items were missed, state 'No missed markups detected.'"
                            )
                        },
                        {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                    ],
                    max_tokens=1000
                )
                missed_summary = res_missed.choices[0].message.content
                break
            except Exception:
                time.sleep(10)

        addressed_summary = ""
        for attempt in range(5):
            try:
                res_addressed = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Chief Structural QA/QC Manager. Synthesize ONLY the FULLY ADDRESSED markups across all sheets.\n"
                                "Format as bullet points categorized by sheet number.\n"
                                "Briefly state the verified physical drawing change executed in Rev B."
                            )
                        },
                        {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                    ],
                    max_tokens=1000
                )
                addressed_summary = res_addressed.choices[0].message.content
                break
            except Exception:
                time.sleep(10)

        loader_placeholder.empty()

        st.session_state.audit_results = ordered_results
        st.session_state.images_a = images_a
        st.session_state.images_b = images_b
        st.session_state.sheet_names = sheet_names
        st.session_state.total_pages = total_pages
        st.session_state.current_slide = 0
        st.session_state.summary_missed = missed_summary
        st.session_state.summary_addressed = addressed_summary

# Render Navigation & Layout Tabs
if "audit_results" in st.session_state and len(st.session_state.audit_results) > 0:
    st.write("---")

    total = st.session_state.total_pages
    current = st.session_state.current_slide
    sheet_names = st.session_state.sheet_names

    # Hotkeys
    components.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft') {
                const prevBtn = Array.from(doc.querySelectorAll('button')).find(el => el.textContent.includes('Previous'));
                if (prevBtn && !prevBtn.disabled) prevBtn.click();
            } else if (e.key === 'ArrowRight') {
                const nextBtn = Array.from(doc.querySelectorAll('button')).find(el => el.textContent.includes('Next'));
                if (nextBtn && !nextBtn.disabled) nextBtn.click();
            }
        });
        </script>
        """,
        height=0,
        width=0
    )

    # Top Navigation Bar
    nav_col1, nav_col2, nav_col3 = st.columns([1.2, 3, 1.2])

    with nav_col1:
        if st.button("◀ Previous Sheet", key="btn_prev", disabled=(current == 0)):
            st.session_state.current_slide = max(0, current - 1)
            st.rerun()

    with nav_col2:
        curr_label = sheet_names[current] if current < total else "Master QA/QC Executive Summary"
        st.markdown(
            f"<h3 style='text-align: center; margin: 0; color: #f8fafc; font-size: 1.15rem; font-weight: 700;'>{curr_label} ({current + 1} of {total + 1})</h3>",
            unsafe_allow_html=True
        )

    with nav_col3:
        if st.button("Next Sheet ▶", key="btn_next", disabled=(current == total)):
            st.session_state.current_slide = min(total, current + 1)
            st.rerun()

    # Main Sheet View
    if current < total:
        img_a = st.session_state.images_a[current]
        img_b = st.session_state.images_b[current]
        result_text = st.session_state.audit_results[current]

        c1, c2 = st.columns(2)
        with c1:
            render_panzoom_image(img_a, f"Rev A (Redlines) — {sheet_names[current]}", f"reva_{current}")
        with c2:
            render_panzoom_image(img_b, f"Rev B (Revised) — {sheet_names[current]}", f"revb_{current}")

        st.markdown(f"### Detailed Engineering Delta Audit ({sheet_names[current]})")
        st.markdown(result_text)

    else:
        st.markdown("## Master QA/QC Executive Summary")
        sum_col_left, sum_col_right = st.columns(2)

        with sum_col_left:
            st.error("### Incomplete / Missed Markups")
            st.markdown(st.session_state.summary_missed)

        with sum_col_right:
            st.success("### Verified / Addressed Markups")
            st.markdown(st.session_state.summary_addressed)

    # CAD Layout Navigation Dock
    st.write("---")
    st.markdown("<div class='card-label'>CAD VIEWPORTS & LAYOUT TABS</div>", unsafe_allow_html=True)

    tab_cols = st.columns(min(total + 2, 12))

    with tab_cols[0]:
        st.button("Model Space", key="c3d_model", disabled=True)

    for idx in range(total):
        col_target = tab_cols[(idx + 1) % min(total + 2, 12)]
        with col_target:
            tab_label = f"• {sheet_names[idx]}" if idx == current else f"{sheet_names[idx]}"
            if st.button(tab_label, key=f"c3d_tab_{idx}"):
                st.session_state.current_slide = idx
                st.rerun()

    with tab_cols[(total + 1) % min(total + 2, 12)]:
        summary_label = "• Summary" if current == total else "Summary"
        if st.button(summary_label, key="c3d_tab_summary"):
            st.session_state.current_slide = total
            st.rerun()

# Bottom Ticker Bar (PulseBoard Tech Stack Style)
st.markdown("""
   <div class="ticker-bar">
       <span>✦ PyMuPDF Engine</span>
       <span>✦ OpenAI GPT-4o Vision</span>
       <span>✦ High-DPI Quadrant Matrix</span>
       <span>✦ Vector Layer Parser</span>
   </div>
""", unsafe_allow_html=True)