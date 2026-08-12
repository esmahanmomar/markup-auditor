import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import time
from PIL import Image, ImageEnhance
from openai import OpenAI
import pymupdf as fitz
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Markup Auditor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- STRICT PURE LIGHT THEME & UI CSS OVERRIDES ---
st.markdown(
    """
   <style>
       @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap');

       /* 1. Base Typography (Strictly exclude spans and material icon tags) */
       html, body, .stApp, [data-testid="stSidebar"], 
       input, textarea, select, p, h1, h2, h3, h4, h5, h6, label, div {
           font-family: 'Lora', 'Georgia', 'Times New Roman', serif !important;
       }

       /* Restore Material Icons globally for Streamlit */
       span[data-testid="stIconMaterial"],
       [data-testid="stIcon"],
       [data-baseweb="icon"],
       i {
           font-family: "Material Symbols Outlined", "Material Icons" !important;
       }

       /* 2. Pure Light Background Canvas */
       html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
           background-color: #f8fafc !important;
           color: #0f172a !important;
       }

       header[data-testid="stHeader"] {
           background-color: #f8fafc !important;
       }

       /* 3. Title Header */
       .hero-container {
           text-align: center;
           margin: 10px auto 25px auto;
           max-width: 850px;
       }

       .hero-title {
           font-size: 2.8rem;
           font-weight: 700;
           letter-spacing: -0.02em;
           color: #0f172a;
           text-transform: uppercase;
           margin-bottom: 4px;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       .slate-accent {
           color: #64748b;
           font-style: italic;
       }

       .card-label {
           font-size: 0.85rem;
           font-weight: 700;
           color: #334155;
           letter-spacing: 0.05em;
           text-transform: uppercase;
           margin-bottom: 8px;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       /* 4. Streamlit File Uploader Overrides */
       [data-testid="stFileUploader"] {
           background-color: transparent !important;
       }

       section[data-testid="stFileUploaderDropzone"] {
           background-color: #ffffff !important;
           border: 1.5px dashed #cbd5e1 !important;
           border-radius: 8px !important;
           padding: 18px 24px !important;
           display: flex !important;
           align-items: center !important;
           gap: 12px !important;
       }

       section[data-testid="stFileUploaderDropzone"]:hover {
           border-color: #64748b !important;
           background-color: #f8fafc !important;
       }

       /* REMOVE EXTRA TEXT ("200MB per file • PDF") */
       [data-testid="stFileUploaderDropzoneInstructions"],
       [data-testid="stFileUploaderDropzone"] small,
       [data-testid="stFileUploaderDropzone"] [data-testid="stMarkdownContainer"] {
           display: none !important;
       }

       /* Make Browse / Add Button Roomier and Bigger */
       [data-testid="stFileUploaderDropzone"] button {
           background-color: #f1f5f9 !important;
           color: #0f172a !important;
           border: 1px solid #cbd5e1 !important;
           border-radius: 6px !important;
           padding: 10px 20px !important;
           min-height: 42px !important;
           font-size: 0.95rem !important;
           font-weight: 600 !important;
           box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
           display: inline-flex !important;
           align-items: center !important;
           justify-content: center !important;
           gap: 8px !important;
       }

       [data-testid="stFileUploaderDropzone"] button:hover {
           background-color: #e2e8f0 !important;
           border-color: #64748b !important;
           color: #0f172a !important;
       }

       /* Fix Uploaded File Badge / Pill (No Dark Mode) */
       [data-testid="stFileUploaderFileData"],
       div[data-testid="stFileUploaderFileData"] {
           background-color: #ffffff !important;
           color: #0f172a !important;
           border: 1px solid #cbd5e1 !important;
           border-radius: 6px !important;
           padding: 8px 14px !important;
       }

       [data-testid="stFileUploaderFileData"] * {
           color: #0f172a !important;
           fill: #0f172a !important;
       }

       /* 5. Pure Light Text Area */
       [data-testid="stTextArea"] > div,
       [data-testid="stTextArea"] > div > div,
       div[data-baseweb="textarea"], 
       div[data-baseweb="base-input"] {
           background-color: #ffffff !important;
           border: 1px solid #cbd5e1 !important;
           border-radius: 8px !important;
       }

       textarea[data-testid="stTextArea"] {
           color: #0f172a !important;
           background-color: #ffffff !important;
           -webkit-text-fill-color: #0f172a !important;
           font-size: 0.95rem !important;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       textarea[data-testid="stTextArea"]::placeholder {
           color: #94a3b8 !important;
           -webkit-text-fill-color: #94a3b8 !important;
           font-style: italic;
       }

       /* 6. Action Button (Left Aligned) */
       div.stButton > button {
           background-color: #ffffff !important;
           color: #0f172a !important;
           font-size: 0.95rem !important;
           font-weight: 700 !important;
           font-family: 'Lora', 'Georgia', serif !important;
           padding: 12px 28px !important;
           border-radius: 6px !important;
           border: 1px solid #cbd5e1 !important;
           box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
           transition: all 0.2s ease !important;
           margin-left: 0 !important;
           margin-right: auto !important;
           display: block !important;
       }

       div.stButton > button:hover {
           background-color: #e2e8f0 !important;
           border-color: #64748b !important;
           color: #0f172a !important;
           transform: translateY(-1px);
           box-shadow: 0 4px 6px rgba(0,0,0,0.06) !important;
       }

       /* 7. Loader & Status Box */
       .loader-box {
           display: flex;
           align-items: center;
           justify-content: center;
           background: #ffffff;
           border: 1px solid #cbd5e1;
           padding: 16px;
           border-radius: 8px;
           margin: 20px 0;
           color: #0f172a;
           font-size: 0.95rem;
           font-weight: 600;
           font-family: 'Lora', 'Georgia', serif !important;
           text-align: center;
           box-shadow: 0 1px 3px rgba(0,0,0,0.04);
       }
   </style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
   <div class="hero-container">
       <div class="hero-title">
           MARKUP <span class="slate-accent">AUDITOR</span>
       </div>
   </div>
""",
    unsafe_allow_html=True,
)

# API Key Handling
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
          "type": (
              annot.type[1]
              if isinstance(annot.type, tuple)
              else str(annot.type)
          ),
      })

    annots_per_page.append(page_annots)

    img = Image.open(io.BytesIO(img_data)).convert("RGB")
    w, h = img.size
    page_crops = []

    quadrants = [
        (0, 0, int(w * 0.55), int(h * 0.55)),
        (int(w * 0.45), 0, w, int(h * 0.55)),
        (0, int(h * 0.45), int(w * 0.55), h),
        (int(w * 0.45), int(h * 0.45), w, h),
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


def process_single_sheet(
    sheet_index,
    img_a_bytes,
    img_b_bytes,
    crops_a_list,
    crops_b_list,
    annots_a_list,
    user_notes,
    api_key_val,
):
  client = OpenAI(api_key=api_key_val)

  base64_a = base64.b64encode(img_a_bytes).decode("utf-8")
  base64_b = base64.b64encode(img_b_bytes).decode("utf-8")

  if annots_a_list and len(annots_a_list) > 0:
    annot_summary = (
        f"\nEXTRACTED VECTOR ANNOTATIONS ON REV A SHEET {sheet_index+1}:\n"
    )
    for idx, a in enumerate(annots_a_list):
      txt = a["content"] if a["content"] else "Graphic Markup / Callout Box"
      annot_summary += f"- Redline #{idx+1} ({a['type']}): \"{txt}\" (Subject: {a['subject']})\n"
  else:
    annot_summary = (
        "\nNO EMBEDDED PDF VECTOR ANNOTATIONS DETECTED ON METADATA LAYER. YOU"
        " MUST PERFORM FULL VISUAL OPTICAL COMPARISON ACROSS CROPS TO DETECT"
        " REDLINES AND TEXT EDITS.\n"
    )

  content_payload = [{
      "type": "text",
      "text": (
          f"User Specific Directives: {user_notes}\n{annot_summary}\nCompare"
          f" Sheet {sheet_index+1} Rev A against Rev B thoroughly across text"
          " labels, dimensions, and drawing lines."
      ),
  }]

  content_payload.append(
      {"type": "text", "text": "REV A OVERALL SHEET (Redlines):"}
  )
  content_payload.append({
      "type": "image_url",
      "image_url": {"url": f"data:image/png;base64,{base64_a}", "detail": "high"},
  })

  content_payload.append(
      {"type": "text", "text": "REV B OVERALL SHEET (Revised Output):"}
  )
  content_payload.append({
      "type": "image_url",
      "image_url": {"url": f"data:image/png;base64,{base64_b}", "detail": "high"},
  })

  labels = [
      "Top-Left Quad",
      "Top-Right Quad",
      "Bottom-Left Quad",
      "Bottom-Right Quad",
  ]
  for i in range(min(len(crops_a_list), 4)):
    crop_a_b64 = base64.b64encode(crops_a_list[i]).decode("utf-8")
    crop_b_b64 = base64.b64encode(crops_b_list[i]).decode("utf-8")
    content_payload.append({
        "type": "text",
        "text": (
            f"HIGH-RES DETAILED COMPARISON [{labels[i]}] - REV A vs REV B:"
        ),
    })
    content_payload.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{crop_a_b64}",
            "detail": "high",
        },
    })
    content_payload.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{crop_b_b64}",
            "detail": "high",
        },
    })

  system_prompt = (
      f"You are a Senior Structural & Civil Engineering QA/QC Inspector auditing"
      f" Sheet {sheet_index+1}.\n\nSTRICT COMPREHENSIVE AUDIT & VISUAL DIFF"
      " RULES:\n1. Evaluate ONLY Sheet {sheet_index+1}.\n2. Perform a"
      " meticulous visual optical scan comparing Rev A and Rev B across all 4"
      " quadrant crops. Check for altered text notes (e.g. 'SEAWALL' changed to"
      " 'CENTER OF ROAD'), moved alignment lines, updated dimensions, and"
      " added/removed graphic callouts.\n3. Do not rely solely on embedded PDF"
      " metadata. Scan the image pixels directly for redlines, clouding, and"
      " text edits.\n4. Read the Title Block on the bottom right to report the"
      " exact Sheet Number (e.g., CM-1.0, CM-1.3).\n\nFORMAT YOUR OUTPUT"
      " EXACTLY AS FOLLOWS:\n\n### Engineering Callout & Design Audit\n\n*"
      " **Location & Drawing Ref**: [Grid Lines / Detail Ref / Title Block"
      " Sheet Number]\n  * **Engineer Redline Directive**: [Exact directive /"
      " question visible on Rev A or in redlines]\n  * **Rev B Visual"
      " Geometry Verification**: [Observed physical CAD changes in Rev B,"
      " including exact text modifications]\n  * **Status**: FULLY ADDRESSED"
      " (or MISSED / PARTIALLY ADDRESSED / NO MARKUPS DETECTED ON THIS"
      " SHEET)\n  * **QA/QC Technical Notes**: [Detailed technical"
      " commentary]\n"
  )

  max_retries = 5
  backoff = 15
  for attempt in range(max_retries):
    try:
      response = client.chat.completions.create(
          model="gpt-4o",
          messages=[
              {"role": "system", "content": system_prompt},
              {"role": "user", "content": content_payload},
          ],
          max_tokens=2500,
      )
      return sheet_index, response.choices[0].message.content
    except Exception as e:
      if "rate_limit" in str(e).lower() or "429" in str(e):
        time.sleep(backoff)
        backoff *= 2  # Exponential backoff for rate limit handling
      elif attempt < max_retries - 1:
        time.sleep(5)
      else:
        raise e


def render_panzoom_image(img_bytes, caption, key_id):
  b64_img = base64.b64encode(img_bytes).decode("utf-8")
  html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/@panzoom/panzoom@4.5.1/dist/panzoom.min.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background-color: transparent; font-family: 'Lora', 'Georgia', serif; color: #0f172a; overflow: hidden; }}
            .container {{ position: relative; width: 100%; height: 520px; border: 1px solid #cbd5e1; border-radius: 8px; background: #ffffff; overflow: hidden; }}
            .controls {{ position: absolute; top: 12px; right: 12px; z-index: 100; display: flex; gap: 6px; }}
            .btn {{ background: #f8fafc; color: #0f172a; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; font-family: 'Lora', 'Georgia', serif; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .btn:hover {{ background: #e2e8f0; color: #0f172a; }}
            .caption {{ position: absolute; bottom: 12px; left: 12px; z-index: 100; background: #f8fafc; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #0f172a; border: 1px solid #cbd5e1; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
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


# --- UPLOAD SECTION ---
with col1:
  st.markdown(
      "<div class='card-label'>01 // MARKED-UP DRAWING SET (REV A"
      " REDLINES)</div>",
      unsafe_allow_html=True,
  )
  rev_a_file = st.file_uploader(
      "Upload Rev A PDF",
      type=["pdf"],
      key="a",
      label_visibility="collapsed",
  )

with col2:
  st.markdown(
      "<div class='card-label'>02 // REVISED CAD DRAWING SET (REV B"
      " ISSUANCE)</div>",
      unsafe_allow_html=True,
  )
  rev_b_file = st.file_uploader(
      "Upload Rev B PDF",
      type=["pdf"],
      key="b",
      label_visibility="collapsed",
  )

st.markdown(
    "<div class='card-label' style='margin-top: 14px;'>03 // MANDATORY QA/QC"
    " REVIEW DIRECTIVES & AUDIT SPECIFICATIONS (OPTIONAL)</div>",
    unsafe_allow_html=True,
)

markup_notes = st.text_area(
    "Notes",
    placeholder=(
        "e.g., Ensure dimensions were added on concrete cap; verify structural"
        " beam elevations per Revision Note #3."
    ),
    label_visibility="collapsed",
)

# Left-Aligned Button
run_audit = st.button("EXECUTE DRAWING AUDIT")

if run_audit and rev_a_file and rev_b_file:
  if not api_key:
    st.error(
        "Missing API Key: Enter your OpenAI Key in the sidebar or Streamlit"
        " secrets."
    )
  else:
    loader_placeholder = st.empty()
    loader_placeholder.markdown(
        """
            <div class='loader-box'>
                <span>Working with Annotation Layers & Processing Markups</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    images_a, crops_a, annots_a, count_a = process_pdf_with_annotations(
        rev_a_file
    )
    images_b, crops_b, annots_b, count_b = process_pdf_with_annotations(
        rev_b_file
    )

    total_pages = min(count_a, count_b)
    results_dict = {}
    sheet_names = [f"Sheet {i+1}" for i in range(total_pages)]

    # Sequential processing (max_workers=1) prevents rate limit exhaustion
    with ThreadPoolExecutor(max_workers=1) as executor:
      future_to_index = {}
      for i in range(total_pages):
        f = executor.submit(
            process_single_sheet,
            i,
            images_a[i],
            images_b[i],
            crops_a[i],
            crops_b[i],
            annots_a[i],
            markup_notes,
            api_key,
        )
        future_to_index[f] = i
        time.sleep(2)  # Short pause between sheet dispatches

      completed_count = 0
      for future in as_completed(future_to_index):
        idx, result_text = future.result()
        results_dict[idx] = result_text
        completed_count += 1
        loader_placeholder.markdown(
            f"""
                    <div class='loader-box'>
                        <span>Checking drawing revisions... Evaluated {completed_count} of {total_pages} Sheet Sets</span>
                    </div>
                """,
            unsafe_allow_html=True,
        )

    ordered_results = [results_dict[i] for i in range(total_pages)]

    loader_placeholder.markdown(
        """
            <div class='loader-box'>
                <span>Synthesizing Executive Engineering Compliance & Discrepancy Matrix...</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    full_audit_text = "\n\n".join(
        [f"**Sheet {idx+1}:**\n" + res for idx, res in enumerate(ordered_results)]
    )
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
                        "You are a Chief Structural QA/QC Manager. Synthesize"
                        " ONLY the MISSED or INCOMPLETE markups across all"
                        " sheets.\nFormat as bullet points categorized by sheet"
                        " number.\nInclude the requested engineering directive"
                        " and why physical drafting failed in Rev B. If zero"
                        " items were missed, state 'No missed markups"
                        " detected.'"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Full Audit Results:\n\n{full_audit_text}",
                },
            ],
            max_tokens=1000,
        )
        missed_summary = res_missed.choices[0].message.content
        break
      except Exception as e:
        time.sleep(12)

    addressed_summary = ""
    for attempt in range(5):
      try:
        res_addressed = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Chief Structural QA/QC Manager. Synthesize"
                        " ONLY the FULLY ADDRESSED markups across all"
                        " sheets.\nFormat as bullet points categorized by sheet"
                        " number.\nBriefly state the verified physical drawing"
                        " change executed in Rev B."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Full Audit Results:\n\n{full_audit_text}",
                },
            ],
            max_tokens=1000,
        )
        addressed_summary = res_addressed.choices[0].message.content
        break
      except Exception as e:
        time.sleep(12)

    loader_placeholder.empty()

    st.session_state.audit_results = ordered_results
    st.session_state.images_a = images_a
    st.session_state.images_b = images_b
    st.session_state.sheet_names = sheet_names
    st.session_state.total_pages = total_pages
    st.session_state.current_slide = 0
    st.session_state.summary_missed = missed_summary
    st.session_state.summary_addressed = addressed_summary

# Navigation & Output Rendering
if (
    "audit_results" in st.session_state
    and len(st.session_state.audit_results) > 0
):
  st.write("---")

  total = st.session_state.total_pages
  current = st.session_state.current_slide
  sheet_names = st.session_state.sheet_names

  # Keyboard Navigation Hotkeys
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
      width=0,
  )

  # Top Nav Bar
  nav_col1, nav_col2, nav_col3 = st.columns([1.2, 3, 1.2])

  with nav_col1:
    if st.button("◀ Previous Sheet", key="btn_prev", disabled=(current == 0)):
      st.session_state.current_slide = max(0, current - 1)
      st.rerun()

  with nav_col2:
    curr_label = sheet_names[current] if current < total else "Executive Summary"
    st.markdown(
        f"<h3 style='text-align: center; margin: 0; color: #0f172a; font-size:"
        f" 1.15rem; font-weight: 700;'>{curr_label} ({current + 1} of"
        f" {total + 1})</h3>",
        unsafe_allow_html=True,
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
      render_panzoom_image(
          img_a,
          f"Rev A (Redlines) — {sheet_names[current]}",
          f"reva_{current}",
      )
    with c2:
      render_panzoom_image(
          img_b,
          f"Rev B (Revised) — {sheet_names[current]}",
          f"revb_{current}",
      )

    st.markdown(f"### Technical Report ({sheet_names[current]})")
    st.markdown(result_text)

  else:
    st.markdown("## Executive QA/QC Compliance Summary")
    sum_col_left, sum_col_right = st.columns(2)

    with sum_col_left:
      st.error("### Non-Compliant / Unresolved Structural Directives")
      st.markdown(st.session_state.summary_missed)

    with sum_col_right:
      st.success("### Verified & Conforming Revisions")
      st.markdown(st.session_state.summary_addressed)

  # Sheet Navigation Dock
  st.write("---")
  st.markdown(
      "<div class='card-label'>SHEET INDEX & VIEWPORT SELECTION</div>",
      unsafe_allow_html=True,
  )

  tab_cols = st.columns(min(total + 1, 12))

  for idx in range(total):
    col_target = tab_cols[idx % min(total + 1, 12)]
    with col_target:
      tab_label = (
          f"• {sheet_names[idx]}" if idx == current else f"{sheet_names[idx]}"
      )
      if st.button(tab_label, key=f"c3d_tab_{idx}"):
        st.session_state.current_slide = idx
        st.rerun()

  with tab_cols[total % min(total + 1, 12)]:
    summary_label = "• Summary" if current == total else "Summary"
    if st.button(summary_label, key="c3d_tab_summary"):
      st.session_state.current_slide = total
      st.rerun()