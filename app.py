# --- STRICT PURE LIGHT THEME & UI CSS OVERRIDES ---
st.markdown(
    """
   <style>
       @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap');

       /* 1. Global Baseline (Excluding spans to protect material icons) */
       html, body, .stApp, [data-testid="stSidebar"], 
       input, textarea, select, p, h1, h2, h3, h4, h5, h6, label, div {
           font-family: 'Lora', 'Georgia', 'Times New Roman', serif !important;
       }

       /* Protect Material Icons from font overrides */
       [data-testid="stIconMaterial"], 
       [data-testid="stIcon"],
       [data-baseweb="icon"],
       [data-testid="stFileUploaderDropzone"] span[aria-hidden="true"],
       [data-testid="stFileUploaderDropzone"] i {
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

       /* 4. Pure Light File Uploader & Browse Button */
       [data-testid="stFileUploader"] {
           background-color: transparent !important;
       }

       section[data-testid="stFileUploaderDropzone"] {
           background-color: #ffffff !important;
           border: 1.5px dashed #cbd5e1 !important;
           border-radius: 8px !important;
           padding: 16px !important;
       }

       section[data-testid="stFileUploaderDropzone"]:hover {
           border-color: #64748b !important;
           background-color: #f8fafc !important;
       }

       /* Target the Browse Files Button specifically inside Dropzone */
       [data-testid="stFileUploaderDropzone"] button {
           background-color: #f1f5f9 !important;
           color: #0f172a !important;
           border: 1px solid #cbd5e1 !important;
           border-radius: 6px !important;
           box-shadow: none !important;
       }

       [data-testid="stFileUploaderDropzone"] button:hover {
           background-color: #e2e8f0 !important;
           border-color: #64748b !important;
           color: #0f172a !important;
       }

       [data-testid="stFileUploaderDropzone"] button p,
       [data-testid="stFileUploaderDropzone"] button span:not([aria-hidden="true"]) {
           font-family: 'Lora', 'Georgia', serif !important;
           color: #0f172a !important;
       }

       /* File Uploader secondary text (200MB limit, etc.) */
       [data-testid="stFileUploaderDropzone"] [data-testid="stMarkdownContainer"] p,
       [data-testid="stFileUploaderDropzone"] small,
       [data-testid="stFileUploaderDropzone"] label {
           color: #475569 !important;
           font-family: 'Lora', 'Georgia', serif !important;
       }

       /* Fix Dark Uploaded File Badge/Pill Background */
       [data-testid="stFileUploaderFileData"],
       div[data-testid="stFileUploaderFileData"],
       [data-testid="stFileUploaderFileName"] {
           background-color: #f1f5f9 !important;
           color: #0f172a !important;
           border: 1px solid #cbd5e1 !important;
           border-radius: 6px !important;
       }

       [data-testid="stFileUploaderFileData"] * {
           color: #0f172a !important;
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