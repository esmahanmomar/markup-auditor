import streamlit as st
import pymupdf as fitz
import base64
from openai import OpenAI
import streamlit.components.v1 as components
import io
import time
from PIL import Image, ImageEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Markup Auditor | QA/QC Engine", layout="wide", initial_sidebar_state="expanded")

# --- ENTERPRISE UI STYLING (CSS) ---
st.markdown("""
   <style>
       @import url('https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DInter%3Awght%40400%3B500%3B600%3B700%26family%3DJetBrains%2BMono%3Awght%40400%3B500%26display%3Dswap&data=05%7C02%7Ceomar%40cumminscederberg.com%7Cb1d21eacce514a3c47ea08def88c5203%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221478725437719%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=Hdq1IwZRr1To57fLEc7134YM1p%2BgCZ4tVLIX5t0AP1U%3D&reserved=0');

       html, body, .stApp {
           background-color: #0f172a !important;
           color: #e2e8f0 !important;
           font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
       }

       /* Top Header Branding */
       .brand-header {
           background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
           border: 1px solid #334155;
           border-radius: 12px;
           padding: 24px 32px;
           margin-bottom: 24px;
           box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
       }

       .brand-title {
           font-size: 2rem;
           font-weight: 700;
           color: #f8fafc;
           letter-spacing: -0.02em;
           margin: 0;
           display: flex;
           align-items: center;
           gap: 12px;
       }

       .brand-subtitle {
           font-size: 0.95rem;
           color: #94a3b8;
           margin-top: 6px;
           font-weight: 400;
       }

       /* Input Containers */
       div[data-testid="stFileUploader"], div.stTextArea {
           background-color: #1e293b !important;
           border: 1px solid #334155 !important;
           border-radius: 8px !important;
           padding: 16px !important;
           box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
       }

       div[data-baseweb="textarea"] textarea {
           color: #f8fafc !important;
           background-color: #0f172a !important;
           border: 1px solid #334155 !important;
           border-radius: 6px !important;
           font-family: 'Inter', sans-serif !important;
       }

       /* Buttons */
       .stButton>button {
           background-color: #2563eb !important;
           color: #ffffff !important;
           font-size: 0.875rem !important;
           font-weight: 600 !important;
           padding: 10px 20px !important;
           border-radius: 6px !important;
           border: none !important;
           box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
           transition: all 0.15s ease-in-out;
       }

       .stButton>button:hover {
           background-color: #1d4ed8 !important;
           box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
       }

       /* Loader Box */
       .loader-box {
           display: flex;
           align-items: center;
           justify-content: center;
           gap: 16px;
           background-color: #1e293b;
           border: 1px solid #334155;
           padding: 20px;
           border-radius: 8px;
           margin: 20px 0;
           color: #38bdf8;
           font-weight: 500;
       }

       /* Custom CAD Layout Tab Dock */
       .cad-dock-label {
           font-family: 'JetBrains Mono', monospace;
           font-size: 0.75rem;
           font-weight: 600;
           letter-spacing: 0.05em;
           color: #64748b;
           text-transform: uppercase;
           margin-bottom: 8px;
       }
   </style>
""", unsafe_allow_html=True)

# Executive Header Component
st.markdown("""
   <div class="brand-header">
       <div class="brand-title">
           <span>MARKUP AUDITOR</span>
           <span style="font-size: 0.75rem; background: #3b82f6; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: 600; vertical-align: middle;">ENTERPRISE</span>
       </div>
       <div class="brand-subtitle">Automated Engineering Drawing QA/QC & Redline Delta Verification Engine</div>
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
        <script src="https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Funpkg.com%2F%40panzoom%2Fpanzoom%404.5.1%2Fdist%2Fpanzoom.min.js&data=05%7C02%7Ceomar%40cumminscederberg.com%7Cb1d21eacce514a3c47ea08def88c5203%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221478725572820%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=kgltt3ImqkdsegYSrPzQVeXdIxqQF2j8qwN9Pd%2B%2Fnog%3D&reserved=0"></script>
        <style>
            body {{ margin: 0; padding: 0; background-color: #0f172a; font-family: sans-serif; color: #ffffff; overflow: hidden; }}
            .container {{ position: relative; width: 100%; height: 520px; border: 1px solid #334155; border-radius: 8px; background: #020617; overflow: hidden; }}
            .controls {{ position: absolute; top: 12px; right: 12px; z-index: 100; display: flex; gap: 6px; }}
            .btn {{ background: #1e293b; color: #f8fafc; border: 1px solid #475569; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; }}
            .btn:hover {{ background: #334155; }}
            .caption {{ position: absolute; bottom: 12px; left: 12px; z-index: 100; background: rgba(15, 23, 42, 0.9); padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #38bdf8; border: 1px solid #334155; }}
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
    st.markdown("<p style='font-weight: 600; color: #94a3b8; font-size: 0.9rem;'>1. ENGINEER MARKUPS (REV A)</p>", unsafe_allow_html=True)
    rev_a_file = st.file_uploader("Upload Rev A PDF", type=["pdf"], key="a", label_visibility="collapsed")

with col2:
    st.markdown("<p style='font-weight: 600; color: #94a3b8; font-size: 0.9rem;'>2. REVISED DRAWING SET (REV B)</p>", unsafe_allow_html=True)
    rev_b_file = st.file_uploader("Upload Rev B PDF", type=["pdf"], key="b", label_visibility="collapsed")

st.markdown("<p style='font-weight: 600; color: #94a3b8; font-size: 0.9rem; margin-top: 10px;'>AUDIT DIRECTIVES & CRITICAL AREAS (OPTIONAL)</p>", unsafe_allow_html=True)
markup_notes = st.text_area(
    "Notes",
    placeholder="e.g., Verify beam spacing adjustments @ 8'-6\" OC and removal of 2 interior structural beams.",
    label_visibility="collapsed"
)

st.write("")
if st.button("RUN AUDIT & VERIFICATION PROCESS") and rev_a_file and rev_b_file:
    if not api_key:
        st.error("Missing API Key: Enter your OpenAI Key in the sidebar or Streamlit secrets.")
    else:
        loader_placeholder = st.empty()
        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span>Extracting Annotation Layers & Generating Quadrant Grids...</span>
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
                        <span>Auditing Sheet Geometry... Processed {completed_count} of {total_pages} sheets</span>
                    </div>
                """, unsafe_allow_html=True)

        ordered_results = [results_dict[i] for i in range(total_pages)]

        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span>Synthesizing Executive Action Items...</span>
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
            f"<h3 style='text-align: center; margin: 0; color: #f8fafc; font-size: 1.25rem;'>{curr_label} ({current + 1} of {total + 1})</h3>",
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
    st.markdown("<div class='cad-dock-label'>CAD VIEWPORTS & LAYOUT TABS</div>", unsafe_allow_html=True)

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