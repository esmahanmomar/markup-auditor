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

# --- SERIF TYPOGRAPHY & CLEAN NATIVE STREAMLIT UPLOADER ---
st.markdown(
    """
   <style>
       @import url('https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DLora%3Aital%2Cwght%400%2C400..700%3B1%2C400..700%26display%3Dswap&data=05%7C02%7Ceomar%40cumminscederberg.com%7C9c685c354605436cb5cc08def89e5c68%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221556250436271%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=rXpT0MnJBkpMIRQragRqfutfRadTZ%2Fc660hz0m9RNVg%3D&reserved=0');

       /* 1. Global Serif Font Override (Excludes Streamlit Icons) */
       html, body, .stApp, [data-testid="stSidebar"],
       input, textarea, select, p, h1, h2, h3, h4, h5, h6, label {
           font-family: 'Lora', 'Georgia', 'Times New Roman', serif !important;
       }

       /* 2. Preserve Streamlit Material Icon Fonts */
       [data-testid="stIconMaterial"],
       [data-testid="stIcon"],
       [data-baseweb="icon"],
       span[aria-hidden="true"] {
           font-family: "Material Symbols Outlined", sans-serif !important;
       }

       /* 3. Global Ash Gray Canvas */
       html, body, .stApp, [data-testid="stSidebar"] {
           background-color: #e2e8f0 !important;
           color: #0f172a !important;
       }

       /* 4. Header Title Styling */
       .hero-container {
           text-align: center;
           margin: 15px auto 30px auto;
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
           color: #475569;
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

       /* 5. FILE UPLOADER (Clean Light Dropzone, Native Streamlit Controls) */
       [data-testid="stFileUploader"] {
           background-color: transparent !important;
       }

       section[data-testid="stFileUploaderDropzone"] {
           background-color: #f8fafc !important;
           border: 1.5px dashed #94a3b8 !important;
           border-radius: 8px !important;
           padding: 16px !important;
       }

       section[data-testid="stFileUploaderDropzone"]:hover {
           border-color: #475569 !important;
           background-color: #ffffff !important;
       }

       /* 6. TEXT AREA FIX (Light Ash Gray Input) */
       [data-testid="stTextArea"] > div,
       [data-testid="stTextArea"] > div > div,
       div[data-baseweb="textarea"],
       div[data-baseweb="base-input"] {
           background-color: #f8fafc !important;
           border: 1px solid #94a3b8 !important;
           border-radius: 8px !important;
       }

       textarea[data-testid="stTextArea"] {
           color: #0f172a !important;
           background-color: #f8fafc !important;
           -webkit-text-fill-color: #0f172a !important;
           font-size: 0.95rem !important;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       textarea[data-testid="stTextArea"]::placeholder {
           color: #64748b !important;
           -webkit-text-fill-color: #64748b !important;
           font-style: italic;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       /* 7. MAIN ACTION BUTTONS */
       div.stButton > button {
           background-color: #f1f5f9 !important;
           color: #0f172a !important;
           font-size: 0.95rem !important;
           font-weight: 700 !important;
           font-family: 'Lora', 'Georgia', serif !important;
           padding: 12px 32px !important;
           border-radius: 6px !important;
           border: 1px solid #94a3b8 !important;
           box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
           transition: all 0.2s ease !important;
           margin: 0 auto !important;
           display: block !important;
       }

       div.stButton > button:hover {
           background-color: #cbd5e1 !important;
           border-color: #475569 !important;
           color: #000000 !important;
           transform: translateY(-1px);
           box-shadow: 0 4px 8px rgba(0,0,0,0.08) !important;
       }

       /* 8. Status Display Box */
       .loader-box {
           display: flex;
           align-items: center;
           justify-content: center;
           background: #f8fafc;
           border: 1px solid #94a3b8;
           padding: 16px;
           border-radius: 8px;
           margin: 20px 0;
           color: #1e293b;
           font-size: 0.95rem;
           font-weight: 600;
           font-family: 'Lora', 'Georgia', serif !important;
           text-align: center;
       }
   </style>
""",
    unsafe_allow_html=True,
)

# Centered Header Title
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
        "\nNO EMBEDDED PDF VECTOR ANNOTATIONS DETECTED ON SHEET"
        f" {sheet_index+1}.\n"
    )

  content_payload = [{
      "type": "text",
      "text": (
          f"User Specific Directives: {user_notes}\n{annot_summary}\nCompare"
          f" Sheet {sheet_index+1} Rev A against Rev B."
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
      f" Sheet {sheet_index+1}.\n\nSTRICT AUDIT & SHEET ISOLATION"
      f" RULES:\n1. Evaluate ONLY Sheet {sheet_index+1}. DO NOT"
      " cross-reference or invent directives from other sheets or previous"
      " drawings.\n2. Check the EXTRACTED VECTOR ANNOTATIONS layer provided"
      " above for this specific sheet.\n3. IF NO REDLINES OR ANNOTATIONS EXIST"
      " ON THIS SHEET (in metadata or visually), YOU MUST SET STATUS TO 'NO"
      " MARKUPS DETECTED ON THIS SHEET' AND DO NOT INVENT CALLOUTS.\n4. If"
      " markups exist, evaluate physical CAD drafting execution in Rev B.\n5."
      " Read the Title Block on the bottom right of the image to state the"
      " true Sheet Number (e.g., CM-1.0, CM-1.1).\n\nFORMAT YOUR OUTPUT EXACTLY"
      " AS FOLLOWS:\n\n### Engineering Callout & Design Delta Audit\n\n*"
      " **Location & Drawing Ref**: [Grid Lines / Detail Ref / Title Block"
      " Sheet Number]\n  * **Engineer Redline Directive**: [Exact directive on"
      " THIS sheet, or 'None']\n  * **Rev B Visual Geometry Verification**:"
      " [Observed physical CAD changes in Rev B]\n  * **Status**: FULLY"
      " ADDRESSED (or MISSED / PARTIALLY ADDRESSED / NO MARKUPS DETECTED ON"
      " THIS SHEET)\n  * **QA/QC Technical Notes**: [Technical notes]\n"
  )

  max_retries = 5
  backoff = 10
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
        <script src="https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Funpkg.com%2F%40panzoom%2Fpanzoom%404.5.1%2Fdist%2Fpanzoom.min.js&data=05%7C02%7Ceomar%40cumminscederberg.com%7C9c685c354605436cb5cc08def89e5c68%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639221556250465006%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=7G8QvdROZBjotjuQzSQyZ9vLlSFanuyaOvVVDy3%2FARE%3D&reserved=0"></script>
        <style>
            body {{ margin: 0; padding: 0; background-color: transparent; font-family: 'Lora', 'Georgia', serif; color: #0f172a; overflow: hidden; }}
            .container {{ position: relative; width: 100%; height: 520px; border: 1px solid #cbd5e1; border-radius: 8px; background: #cbd5e1; overflow: hidden; }}
            .controls {{ position: absolute; top: 12px; right: 12px; z-index: 100; display: flex; gap: 6px; }}
            .btn {{ background: #f8fafc; color: #0f172a; border: 1px solid #94a3b8; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; font-family: 'Lora', 'Georgia', serif; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .btn:hover {{ background: #94a3b8; color: #000; }}
            .caption {{ position: absolute; bottom: 12px; left: 12px; z-index: 100; background: #f8fafc; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: 600; color: #1e293b; border: 1px solid #cbd5e1; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
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


# --- FORM SECTION ---
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

# Centered Action Button
btn_col1, btn_col2, btn_col3 = st.columns([1.5, 2, 1.5])
with btn_col2:
  run_audit = st.button("EXECUTE DRAWING DELTA AUDIT →")

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

    with ThreadPoolExecutor(max_workers=3) as executor:
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
        time.sleep(0.5)

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

# Render Navigation & Layout
if (
    "audit_results" in st.session_state
    and len(st.session_state.audit_results) > 0
):
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
      width=0,
  )

  # Top Navigation Bar
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

    st.markdown(f"### Technical Delta Report ({sheet_names[current]})")
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

  # Layout Navigation Dock
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
