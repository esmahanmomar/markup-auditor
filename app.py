import streamlit as st
import fitz  # PyMuPDF
import base64
import openai
import streamlit.components.v1 as components
import io
import time
from PIL import Image, ImageEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="MARKUP AUDITOR", layout="wide")

# CSS Styling - Clean Light Background with Civil3D Style Tab Dock
st.markdown("""
   <style>
       @import url('https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DDM%2BSans%3Awght%40400%3B500%3B700%26family%3DJetBrains%2BMono%3Awght%40400%3B600%26display%3Dswap&data=05%7C02%7Ceomar%40cumminscederberg.com%7C7105e593cec14fc74cd208def3fa4b64%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639216453518727890%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=t2H3jeZ4gDUrLJMRw%2FlXHJL0gtL%2BQLxLOpN8G5OVqGA%3D&reserved=0');

       html, body, .stApp {
           background-color: #f4f5f7;
           color: #1c1e21;
           font-family: 'DM Sans', sans-serif !important;
       }

       .centered-title {
           text-align: center;
           font-size: 2.6rem;
           font-weight: 700;
           color: #1a1a1a;
           margin: 5px 0;
           letter-spacing: -0.5px;
       }

       .centered-subtitle {
           text-align: center;
           font-size: 1.05rem;
           color: #555555;
           margin-bottom: 20px;
       }

       div[data-testid="stFileUploader"], div.stTextArea {
           background-color: #ffffff;
           border-radius: 8px;
           padding: 12px;
           border: 1px solid #e0e0e0;
           box-shadow: 0 2px 6px rgba(0,0,0,0.03);
       }

       .stButton>button {
           background-color: #2b2d42 !important;
           color: #ffffff !important;
           font-size: 14px !important;
           font-weight: 600;
           padding: 8px 12px;
           border-radius: 6px !important;
           border: none !important;
           box-shadow: 0 2px 5px rgba(0,0,0,0.08);
           transition: all 0.2s ease-in-out;
       }

       .stButton>button:hover {
           background-color: #3d405b !important;
       }

       .loader-box {
           display: flex;
           align-items: center;
           justify-content: center;
           gap: 15px;
           background-color: #ffffff;
           border: 1px solid #e0e0e0;
           padding: 18px;
           border-radius: 8px;
           margin: 20px 0;
           box-shadow: 0 2px 8px rgba(0,0,0,0.04);
       }
   </style>
""", unsafe_allow_html=True)

# Centered Light Header
st.markdown("<h1 class='centered-title'>👷 MARKUP AUDITOR</h1>", unsafe_allow_html=True)
st.markdown("<p class='centered-subtitle'>🛠️ AI QA/QC Structural & Civil Drawing Markup Verification</p>", unsafe_allow_html=True)

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
        annot = page.first_annot
        while annot:
            info = annot.info
            page_annots.append({
                "author": info.get("title", "").strip(),
                "content": info.get("content", "").strip(),
                "subject": info.get("subject", "").strip(),
                "type": annot.type[1] if isinstance(annot.type, tuple) else str(annot.type)
            })
            annot = annot.next

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
    client = openai.OpenAI(api_key=api_key_val)

    base64_a = base64.b64encode(img_a_bytes).decode('utf-8')
    base64_b = base64.b64encode(img_b_bytes).decode('utf-8')

    annot_summary = ""
    if annots_a_list:
        annot_summary = "\nEXTRACTED VECTOR MARKUPS ON REV A:\n"
        for idx, a in enumerate(annots_a_list):
            annot_summary += f"- Redline #{idx+1} ({a['type']}): \"{a['content']}\"\n"

    content_payload = [
        {"type": "text", "text": f"User Audit Directives: {user_notes}\n{annot_summary}\nCompare Sheet {sheet_index+1} Rev A (Redlines) against Rev B (Final Revised Drawing)."}
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
        "CRITICAL DRAFTING EVALUATION DIRECTIVES:\n"
        "1. Redlines on Rev A (e.g., 'SPACE EVENLY @ 8'-6\" OC' with crossed out members) are DRAFTING INSTRUCTIONS for CAD modifications.\n"
        "2. DO NOT expect redline directive text to appear on Rev B. Once drafted, redline notes are removed.\n"
        "3. YOU MUST CHECK PHYSICAL CAD GEOMETRY IN REV B:\n"
        "   - Inspect structural members (beams, joists, piles, walls, pipes).\n"
        "   - If Rev A instructed 'Space evenly @ 8'-6\" OC' and showed 2 beams crossed out, check if Rev B physically removed those 2 members and re-spaced the remaining beams across the span.\n"
        "   - If physical members were removed and re-spaced as requested, mark status as FULLY ADDRESSED.\n"
        "   - Only mark as MISSED if Rev B physically failed to alter the geometry/members.\n"
        "4. Ignore standard unedited title block text (dwg path, scale, borders).\n\n"
        "FORMAT YOUR OUTPUT EXACTLY AS FOLLOWS:\n\n"
        "### Engineering Callout & Design Delta Audit\n\n"
        "* **Location & Drawing Ref**: [Grid Lines / Detail Ref / Location]\n"
        "  * **Engineer Redline Directive**: [e.g. 'Space beams evenly @ 8'-6\" OC & remove 2 interior beams']\n"
        "  * **Rev B Visual Geometry Verification**: [Describe physical CAD drafting changes observed in Rev B]\n"
        "  * **Status**: FULLY ADDRESSED (or MISSED / PARTIALLY ADDRESSED)\n"
        "  * **QA/QC Technical Notes**: [Explanation of physical drafting execution]\n"
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
        except openai.RateLimitError as e:
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
        <script src="https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Funpkg.com%2F%40panzoom%2Fpanzoom%404.5.1%2Fdist%2Fpanzoom.min.js&data=05%7C02%7Ceomar%40cumminscederberg.com%7C7105e593cec14fc74cd208def3fa4b64%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639216453518770864%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=n22KQRMCP8TEyPp2nii2hpsl0n2MzGCp4bmo5ewWETs%3D&reserved=0"></script>
        <style>
            body {{ margin: 0; padding: 0; background-color: #111; font-family: sans-serif; color: #ffffff; overflow: hidden; }}
            .container {{ position: relative; width: 100%; height: 520px; border: 1px solid #ccc; border-radius: 6px; background: #000; overflow: hidden; }}
            .controls {{ position: absolute; top: 10px; right: 10px; z-index: 100; display: flex; gap: 6px; }}
            .btn {{ background: #2b2d42; color: #fff; border: 1px solid #555; padding: 5px 9px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: bold; }}
            .btn:hover {{ background: #3d405b; }}
            .caption {{ position: absolute; bottom: 8px; left: 10px; z-index: 100; background: rgba(0,0,0,0.8); padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #007acc; border: 1px solid #333; }}
            .pan-target {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; cursor: grab; }}
            .pan-target img {{ max-width: 98%; max-height: 98%; object-fit: contain; }}
            .pan-target:active {{ cursor: grabbing; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="caption">{caption}</div>
            <div class="controls">
                <button class="btn" id="zoom-in-{key_id}">➕ Zoom In</button>
                <button class="btn" id="zoom-out-{key_id}">➖ Zoom Out</button>
                <button class="btn" id="reset-{key_id}">🔄 Reset</button>
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
    st.subheader("1. Engineer Callouts / Markups (Rev A)")
    rev_a_file = st.file_uploader("Upload Rev A PDF (with Markups)", type=["pdf"], key="a")

with col2:
    st.subheader("2. Revised Drawing (Rev B)")
    rev_b_file = st.file_uploader("Upload Rev B PDF", type=["pdf"], key="b")

markup_notes = st.text_area(
    "Specific Areas / Notes to Check (Optional):",
    placeholder="e.g., Focus on beam spacing adjustments @ 8'-6\" OC and removal of 2 interior beams."
)

if st.button("👷 AUDIT CALLOUTS & MARKUPS") and rev_a_file and rev_b_file:
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
    else:
        loader_placeholder = st.empty()
        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span style='font-size: 2rem;'>👷</span>
                <span style='font-weight: 600; color: #333;'>DISSECTING DRAWINGS... Tiling high-res visual grids...</span>
            </div>
        """, unsafe_allow_html=True)

        images_a, crops_a, annots_a, count_a = process_pdf_with_annotations(rev_a_file)
        images_b, crops_b, annots_b, count_b = process_pdf_with_annotations(rev_b_file)

        total_pages = min(count_a, count_b)
        results_dict = {}
        sheet_names = [f"CM-{i+1}.0" if i > 0 else "CM-1.0" for i in range(total_pages)]

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
                        <span style='font-size: 2rem;'>🛠️</span>
                        <span style='font-weight: 600; color: #333;'>AUDIT IN PROGRESS... Processed {completed_count} of {total_pages} sheets...</span>
                    </div>
                """, unsafe_allow_html=True)

        ordered_results = [results_dict[i] for i in range(total_pages)]

        loader_placeholder.markdown("""
            <div class='loader-box'>
                <span style='font-size: 2rem;'>📋</span>
                <span style='font-weight: 600; color: #333;'>SYNTHESIZING EXECUTIVE REMEDIAL LIST...</span>
            </div>
        """, unsafe_allow_html=True)

        full_audit_text = "\n\n".join([f"**Sheet {idx+1} ({sheet_names[idx]}):**\n" + res for idx, res in enumerate(ordered_results)])
        client = openai.OpenAI(api_key=api_key)

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
                                "Format as bullet points categorized by sheet designation (e.g., **CM-1.0**).\n"
                                "Include the requested engineering directive and why physical drafting failed in Rev B. If zero items were missed, state 'No missed markups detected.'"
                            )
                        },
                        {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                    ],
                    max_tokens=1000
                )
                missed_summary = res_missed.choices[0].message.content
                break
            except openai.RateLimitError:
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
                                "Format as bullet points categorized by sheet designation (e.g., **CM-1.0**).\n"
                                "Briefly state the verified physical drawing change executed in Rev B."
                            )
                        },
                        {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                    ],
                    max_tokens=1000
                )
                addressed_summary = res_addressed.choices[0].message.content
                break
            except openai.RateLimitError:
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
        curr_label = sheet_names[current] if current < total else "Master QA/QC Action List"
        st.markdown(
            f"<h3 style='text-align: center; margin: 0; color: #1a1a1a;'>{curr_label} ({current + 1} of {total + 1})</h3>",
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

        st.markdown("#### 🔍 Interactive Zoom & Pan (Mouse Wheel to Zoom, Click & Drag to Pan)")
        c1, c2 = st.columns(2)
        with c1:
            render_panzoom_image(img_a, f"Rev A (Redlines) — {sheet_names[current]}", f"reva_{current}")
        with c2:
            render_panzoom_image(img_b, f"Rev B (Revised) — {sheet_names[current]}", f"revb_{current}")

        st.markdown(f"### 📋 Detailed Engineering Delta Audit ({sheet_names[current]})")
        st.markdown(result_text)

    else:
        st.markdown("## 📋 MASTER QA/QC REMEDIAL ACTION LIST")
        sum_col_left, sum_col_right = st.columns(2)

        with sum_col_left:
            st.error("### ❌ Missed / Incomplete Revisions")
            st.markdown(st.session_state.summary_missed)

        with sum_col_right:
            st.success("### ✅ Fully Addressed Markups")
            st.markdown(st.session_state.summary_addressed)

    # Civil3D Layout Tabs Dock Bar (Dark CAD tab bar placed at bottom of light theme page)
    st.write("---")
    st.markdown("<p style='font-family: monospace; font-weight: 700; color: #333; margin-bottom: 5px;'>📐 CIVIL3D LAYOUT TABS</p>", unsafe_allow_html=True)

    tab_cols = st.columns(min(total + 2, 12))

    # Model Tab
    with tab_cols[0]:
        st.button("Model", key="c3d_model", disabled=True)

    for idx in range(total):
        col_target = tab_cols[(idx + 1) % min(total + 2, 12)]
        with col_target:
            tab_label = f"🟦 {sheet_names[idx]}" if idx == current else f"{sheet_names[idx]}"
            if st.button(tab_label, key=f"c3d_tab_{idx}"):
                st.session_state.current_slide = idx
                st.rerun()

    with tab_cols[(total + 1) % min(total + 2, 12)]:
        summary_label = "🟦 Summary" if current == total else "Summary"
        if st.button(summary_label, key="c3d_tab_summary"):
            st.session_state.current_slide = total
            st.rerun()
