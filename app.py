import streamlit as st
import fitz  # PyMuPDF
import base64
import openai
import streamlit.components.v1 as components
import io
import time
from PIL import Image, ImageEnhance
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="MARKUP AUDITOR", layout="wide")

# CSS Styling
st.markdown("""
   <style>
       @import url('https://nam02.safelinks.protection.outlook.com/?url=https%3A%2F%2Ffonts.googleapis.com%2Fcss2%3Ffamily%3DDM%2BSans%3Aital%2Copsz%2Cwght%400%2C9..40%2C100..1000%3B1%2C9..40%2C100..1000%26display%3Dswap&data=05%7C02%7Ceomar%40cumminscederberg.com%7C4dd1d1b786074320d4ac08def261f168%7C9118270b61d6488d8bd6ca11e909b902%7C0%7C0%7C639214699662839177%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=JfVdT1z7uE8025KxDb3%2B2oWeMN55wioY9Vo3VKZVTiY%3D&reserved=0');

       html, body, .stApp,
       .stApp p, .stApp h1, .stApp h2, .stApp h3,
       .stApp h4, .stApp h5, .stApp h6, .stApp label,
       .stMarkdown, .centered-title, .centered-subtitle {
           font-family: 'DM Sans', sans-serif !important;
       }

       [data-testid="stIcon"], [class*="material-symbols"],
       i, button i, div[data-testid="stFileUploader"] i,
       [data-baseweb="icon"] {
           font-family: inherit !important;
       }

       .stApp {
           background-color: #f4f5f7;
           color: #1c1e21;
       }

       .centered-title {
           text-align: center;
           font-size: 2.8rem;
           font-weight: 700;
           color: #1a1a1a;
           margin-top: 5px;
           margin-bottom: 5px;
           letter-spacing: -0.5px;
       }

       .centered-subtitle {
           text-align: center;
           font-size: 1.1rem;
           color: #555555;
           margin-bottom: 25px;
       }

       div[data-testid="stFileUploader"], div.stTextArea {
           background-color: #ffffff;
           border-radius: 10px;
           padding: 15px;
           border: 1px solid #e0e0e0;
           box-shadow: 0 2px 8px rgba(0,0,0,0.03);
       }

       .stButton>button {
           width: 100%;
           background-color: #2b2d42 !important;
           color: #ffffff !important;
           font-size: 15px !important;
           font-weight: 600;
           padding: 8px 12px;
           border-radius: 8px !important;
           border: none !important;
           box-shadow: 0 2px 6px rgba(0,0,0,0.08);
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
           border-radius: 10px;
           margin: 20px 0;
           box-shadow: 0 2px 8px rgba(0,0,0,0.04);
       }

       .loader-icon {
           font-size: 2rem;
           animation: bounce 1s infinite alternate;
       }

       @keyframes bounce {
           from { transform: translateY(0px); }
           to { transform: translateY(-6px); }
       }

       .loader-text {
           font-size: 1.1rem;
           font-weight: 600;
           color: #2b2d42;
       }

       ul > li {
           margin-bottom: 12px !important;
       }

       div[data-testid="stColumn"] {
           position: relative;
       }

       .sheet-preview-popover {
           display: none;
           position: absolute;
           bottom: 115%;
           left: 50%;
           transform: translateX(-50%);
           width: 220px;
           background-color: #ffffff;
           border: 1px solid #d0d0d0;
           box-shadow: 0 6px 16px rgba(0,0,0,0.18);
           border-radius: 8px;
           padding: 5px;
           z-index: 9999;
           pointer-events: none;
       }

       .sheet-preview-popover img {
           width: 100%;
           border-radius: 4px;
           display: block;
       }

       div[data-testid="stColumn"]:hover .sheet-preview-popover {
           display: block;
           animation: fadeIn 0.3s ease-in-out forwards;
           animation-delay: 1.5s;
           opacity: 0;
       }

       @keyframes fadeIn {
           to { opacity: 1; }
       }
   </style>
""", unsafe_allow_html=True)

# Centered Header
st.markdown("<h1 class='centered-title'>👷 MARKUP AUDITOR</h1>", unsafe_allow_html=True)
st.markdown("<p class='centered-subtitle'>🛠️ AI-Powered QA/QC Construction Drawing Verification System</p>", unsafe_allow_html=True)

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
       pix = page.get_pixmap(dpi=250)
       img_data = pix.tobytes("png")
       images_full.append(img_data)

       page_annots = []
       annot = page.first_annot
       while annot:
           info = annot.info
           content = info.get("content", "").strip()
           title = info.get("title", "").strip()
           subject = info.get("subject", "").strip()
           rect = annot.rect

           x0 = min(rect.x0, rect.x1)
           x1 = max(rect.x0, rect.x1)
           y0 = min(rect.y0, rect.y1)
           y1 = max(rect.y0, rect.y1)

           page_annots.append({
               "author": title,
               "content": content,
               "subject": subject,
               "type": annot.type[1] if isinstance(annot.type, tuple) else str(annot.type),
               "bbox": [x0, y0, x1, y1]
           })
           annot = annot.next

       annots_per_page.append(page_annots)

       img = Image.open(io.BytesIO(img_data)).convert('RGB')
       img_np = np.array(img)
       h, w, _ = img_np.shape
       page_crops = []

       # 1. Foxit / PDF Bounding Box Crops
       if len(page_annots) > 0:
           scale_x = w / page.rect.width if page.rect.width > 0 else 1.0
           scale_y = h / page.rect.height if page.rect.height > 0 else 1.0

           for a in page_annots:
               bbox = a["bbox"]
               box_x0 = min(bbox[0], bbox[2]) * scale_x
               box_x1 = max(bbox[0], bbox[2]) * scale_x
               box_y0 = min(bbox[1], bbox[3]) * scale_y
               box_y1 = max(bbox[1], bbox[3]) * scale_y

               pad = 120
               min_x = max(0, int(box_x0) - pad)
               max_x = min(w, int(box_x1) + pad)
               min_y = max(0, int(box_y0) - pad)
               max_y = min(h, int(box_y1) + pad)

               if (max_x > min_x) and (max_y > min_y):
                   crop_img = img.crop((min_x, min_y, max_x, max_y))
                   enhancer = ImageEnhance.Contrast(crop_img)
                   crop_img = enhancer.enhance(1.4)

                   buffer = io.BytesIO()
                   crop_img.save(buffer, format="PNG")
                   page_crops.append(buffer.getvalue())

       # 2. Relaxed Sensitive Red Mask Detection
       r, g, b = img_np[:,:,0], img_np[:,:,1], img_np[:,:,2]
       red_mask = (r > 80) & (r > (g * 1.15)) & (r > (b * 1.15))

       if np.any(red_mask):
           y_indices, x_indices = np.where(red_mask)
           min_x = max(0, int(np.min(x_indices)) - 80)
           max_x = min(w, int(np.max(x_indices)) + 80)
           min_y = max(0, int(np.min(y_indices)) - 80)
           max_y = min(h, int(np.max(y_indices)) + 80)

           if (max_x > min_x) and (max_y > min_y):
               crop_img = img.crop((min_x, min_y, max_x, max_y))
               enhancer = ImageEnhance.Contrast(crop_img)
               crop_img = enhancer.enhance(1.3)

               buffer = io.BytesIO()
               crop_img.save(buffer, format="PNG")
               page_crops.append(buffer.getvalue())

       # 3. Always include 2 Main Drawing View Crops to Guarantee HD Detail for GPT-4o
       # Plan View Area (Top Half)
       plan_crop = img.crop((0, 0, w, int(h * 0.55)))
       buf_plan = io.BytesIO()
       plan_crop.save(buf_plan, format="PNG")
       page_crops.append(buf_plan.getvalue())

       # Sections & Elevations Area (Bottom Half)
       section_crop = img.crop((0, int(h * 0.45), w, h))
       buf_sec = io.BytesIO()
       section_crop.save(buf_sec, format="PNG")
       page_crops.append(buf_sec.getvalue())

       crops_per_page.append(page_crops)

   return images_full, crops_per_page, annots_per_page, len(doc)

def process_single_sheet(sheet_index, img_a_bytes, img_b_bytes, crops_a_list, annots_a_list, user_notes, api_key_val):
   client = openai.OpenAI(api_key=api_key_val)

   base64_a = base64.b64encode(img_a_bytes).decode('utf-8')
   base64_b = base64.b64encode(img_b_bytes).decode('utf-8')

   annot_summary = ""
   if annots_a_list:
       annot_summary = "\nEXTRACTED FOXIT / PDF MARKUP ANNOTATIONS ON REV A:\n"
       for idx, a in enumerate(annots_a_list):
           annot_summary += f"- Markup #{idx+1} (Author: {a['author'] or 'N/A'}, Type: {a['type']}): Content = \"{a['content']}\"\n"
   else:
       annot_summary = "\nEXTRACTED FOXIT / PDF MARKUP ANNOTATIONS ON REV A: None detected in vector data.\n"

   content_payload = [
       {"type": "text", "text": f"User Notes: {user_notes}\n{annot_summary}\nAnalyze Sheet {sheet_index+1} Rev A (marked-up) vs Rev B (revised)."}
   ]

   content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_a}", "detail": "high"}})
   content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_b}", "detail": "high"}})

   for crop_bytes in crops_a_list[:4]:
       crop_b64 = base64.b64encode(crop_bytes).decode('utf-8')
       content_payload.append({"type": "text", "text": "HIGH-RESOLUTION ZOOMED CROP OF DRAWING / MARKUP SECTION ON REV A:"})
       content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{crop_b64}", "detail": "high"}})

   system_prompt = (
       "You are a Senior Structural Engineering QA/QC Inspector performing a comprehensive redline markup audit on Sheet " + str(sheet_index+1) + ".\n\n"
       "AUDIT DIRECTIVE:\n"
       "1. Look closely at the Plan View, Front View Section, Cross Sections, and Notes on Rev A.\n"
       "2. Identify and transcribe ALL red text callouts, red text boxes, red clouds, or red leader lines (e.g. callouts referencing concrete caps, seawall, geotextile, PVC pipes, etc.).\n"
       "3. IGNORE standard black title block parameters like scale, DWG path, or standard sheet numbers unless explicitly marked in red.\n"
       "4. DO NOT claim 'No red callouts found' when red callouts exist in the full sheet or zoomed crops.\n"
       "5. Check whether Rev B incorporated each callout directive.\n\n"
       "FORMAT YOUR OUTPUT EXACTLY AS FOLLOWS:\n\n"
       "### Red Line Markups & Callout Verification\n\n"
       "* **Location Reference**: [e.g., Plan View / Front View Section / Cross Section A / Detail CM-2.0]\n"
       "  * **Engineer Callout / Red Directive Text**: [Exact wording of the red markup]\n"
       "  * **Target Area & Scope**: [Location in drawing]\n"
       "  * **Status**: FULLY ADDRESSED (or MISSED / PARTIALLY ADDRESSED)\n"
       "  * **Spot-the-Difference & Verification**: [Explanation verifying whether Rev B incorporated the requirement]\n"
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
               max_tokens=1500
           )
           return sheet_index, response.choices[0].message.content
       except openai.RateLimitError as e:
           if attempt < max_retries - 1:
               time.sleep(backoff)
               backoff *= 1.5
           else:
               raise e

with col1:
   st.subheader("1. Engineer Callouts / Markups (Rev A)")
   rev_a_file = st.file_uploader("Upload Rev A PDF (with Markups)", type=["pdf"], key="a")

with col2:
   st.subheader("2. Revised Drawing (Rev B)")
   rev_b_file = st.file_uploader("Upload Rev B PDF", type=["pdf"], key="b")

markup_notes = st.text_area(
   "Specific Areas / Notes to Check (Optional):",
   placeholder="e.g., Check signature block addresses, detail tags, and note updates."
)

if st.button("👷 AUDIT CALLOUTS & MARKUPS") and rev_a_file and rev_b_file:
   if not api_key:
       st.error("Please enter your OpenAI API key in the sidebar.")
   else:
       loader_placeholder = st.empty()
       loader_placeholder.markdown("""
           <div class='loader-box'>
               <span class='loader-icon'>👷</span>
               <span class='loader-text'>PARALLEL AUDIT IN PROGRESS... Extracting high-dpi crops and auditing markups...</span>
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
                   process_single_sheet, i, images_a[i], images_b[i], crops_a[i], annots_a[i], markup_notes, api_key
               )
               future_to_index[f] = i
               time.sleep(1.0)

           completed_count = 0
           for future in as_completed(future_to_index):
               idx, result_text = future.result()
               results_dict[idx] = result_text
               completed_count += 1
               loader_placeholder.markdown(f"""
                   <div class='loader-box'>
                       <span class='loader-icon'>🛠️</span>
                       <span class='loader-text'>AUDIT IN PROGRESS... Completed {completed_count} of {total_pages} sheets...</span>
                   </div>
               """, unsafe_allow_html=True)

       ordered_results = [results_dict[i] for i in range(total_pages)]

       loader_placeholder.markdown("""
           <div class='loader-box'>
               <span class='loader-icon'>📋</span>
               <span class='loader-text'>FINALIZING AUDIT... Synthesizing split Master Remedial summary...</span>
           </div>
       """, unsafe_allow_html=True)

       full_audit_text = "\n\n".join([f"**Sheet {idx+1}:**\n" + res for idx, res in enumerate(ordered_results)])

       client = openai.OpenAI(api_key=api_key)

       # Summary Left Column: Missed / Incomplete items
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
                               "Format as bullet points categorized by sheet number (e.g., **Sheet X**).\n"
                               "Include the exact directive text and what was missed. If zero items were missed, state 'No missed markups detected.'"
                           )
                       },
                       {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                   ],
                   max_tokens=700
               )
               missed_summary = res_missed.choices[0].message.content
               break
           except openai.RateLimitError:
               time.sleep(10)

       # Summary Right Column: Fully Addressed items
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
                               "Format as bullet points categorized by sheet number (e.g., **Sheet X**).\n"
                               "Briefly state the resolved markup callout and its location in Rev B."
                           )
                       },
                       {"role": "user", "content": f"Full Audit Results:\n\n{full_audit_text}"}
                   ],
                   max_tokens=700
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

# Render Slide Navigation Interface
if "audit_results" in st.session_state and len(st.session_state.audit_results) > 0:
   st.write("---")

   total = st.session_state.total_pages
   current = st.session_state.current_slide
   sheet_names = st.session_state.sheet_names

   components.html(
       """
       <script>
       const doc = window.parent.document;
       doc.addEventListener('keydown', function(e) {
           if (e.key === 'ArrowLeft') {
               const prevBtn = doc.querySelector('button[data-testid="stBaseButton-secondary"]:has(div:contains("Previous"))') ||
                               Array.from(doc.querySelectorAll('button')).find(el => el.textContent.includes('Previous Sheet'));
               if (prevBtn && !prevBtn.disabled) prevBtn.click();
           } else if (e.key === 'ArrowRight') {
               const nextBtn = doc.querySelector('button[data-testid="stBaseButton-secondary"]:has(div:contains("Next"))') ||
                               Array.from(doc.querySelectorAll('button')).find(el => el.textContent.includes('Next Sheet'));
               if (nextBtn && !nextBtn.disabled) nextBtn.click();
           }
       });
       </script>
       """,
       height=0,
       width=0
   )

   # Top Navigation Bar
   nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])

   with nav_col1:
       if st.button("◀ Previous Sheet", key="btn_prev", disabled=(current == 0)):
           st.session_state.current_slide = max(0, current - 1)
           st.rerun()

   with nav_col2:
       curr_label = sheet_names[current] if current < total else "Master Executive REMEDIAL LIST"
       st.markdown(
           f"<h3 style='text-align: center; margin: 0;'>Slide {current + 1} of {total + 1} &nbsp;—&nbsp; {curr_label}</h3>"
           f"<p style='text-align: center; color: #777; margin: 2px 0 0 0; font-size: 0.85rem;'>Tip: Use Left/Right Arrow keys to navigate</p>",
           unsafe_allow_html=True
       )

   with nav_col3:
       if st.button("Next Sheet ▶", key="btn_next", disabled=(current == total)):
           st.session_state.current_slide = min(total, current + 1)
           st.rerun()

   # Main Slide View
   if current < total:
       img_a = st.session_state.images_a[current]
       img_b = st.session_state.images_b[current]
       result_text = st.session_state.audit_results[current]

       c1, c2 = st.columns(2)
       with c1:
           st.image(img_a, caption=f"Rev A (Marked-Up) — {sheet_names[current]}", use_container_width=True)
       with c2:
           st.image(img_b, caption=f"Rev B (Revised) — {sheet_names[current]}", use_container_width=True)

       st.markdown(f"### 🔍 Detailed Callout & Specification Breakdown ({sheet_names[current]})")
       st.markdown(result_text)

   else:
       st.markdown("## 📋 MASTER QA/QC ACTION REMEDIAL LIST")

       sum_col_left, sum_col_right = st.columns(2)

       with sum_col_left:
           st.error("### ❌ Missed / Incomplete Revisions")
           st.markdown(st.session_state.summary_missed)

       with sum_col_right:
           st.success("### ✅ Fully Addressed Markups")
           st.markdown(st.session_state.summary_addressed)

   st.write("---")
   st.markdown("#### 🎯 Quick Jump to Sheet")

   num_cols = min(total + 1, 10)
   sheet_cols = st.columns(num_cols)

   for idx in range(total + 1):
       col_idx = idx % num_cols
       with sheet_cols[col_idx]:
           if idx < total:
               btn_label = sheet_names[idx]
               if idx == current:
                   btn_label = f"👉 {btn_label}"

               img_bytes = st.session_state.images_a[idx]
               img_thumb = Image.open(io.BytesIO(img_bytes))
               img_thumb.thumbnail((220, 160))
               buf = io.BytesIO()
               img_thumb.save(buf, format="PNG")
               b64_thumb = base64.b64encode(buf.getvalue()).decode("utf-8")

               st.markdown(f"""
                   <div class="sheet-preview-popover">
                       <img src="data:image/png;base64,{b64_thumb}" />
                   </div>
               """, unsafe_allow_html=True)

               if st.button(btn_label, key=f"jump_sheet_{idx}"):
                   st.session_state.current_slide = idx
                   st.rerun()
           else:
               btn_label = "📋 Summary"
               if idx == current:
                   btn_label = f"👉 {btn_label}"

               if st.button(btn_label, key="jump_sheet_summary"):
                   st.session_state.current_slide = idx
                   st.rerun()
