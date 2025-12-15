import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import base64
import time
import json
import re

# --- CONFIGURATION MOTEUR ---
MODEL_NAME = "gemini-2.0-flash" 

# --- FONCTION UTILITAIRE (BASE64) ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None 

# --- CONFIGURATION DE LA PAGE ---
favicon_path = "assets/favicon.ico"
page_icon = favicon_path if os.path.exists(favicon_path) else "🏗️"

st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLES CSS ---
st.markdown("""
<style>
    /* UI Hacks Upload & Header */
    [data-testid='stFileUploader'] section > div > div > span { display: none; }
    [data-testid='stFileUploader'] section > div > div::after {
        content: "Glissez le dossier DCE (PDF) ici ou cliquez pour parcourir";
        color: #E85D04; font-weight: bold; display: block; margin-top: 10px; font-family: 'Helvetica Neue', sans-serif;
    }
    [data-testid='stFileUploader'] section > div > div > small { display: none; }

    .header-container { display: flex; flex-direction: row; align-items: center; margin-bottom: 2rem; gap: 20px; }
    .header-logo { width: 100px; height: auto; }
    .header-text-block { display: flex; flex-direction: column; justify-content: center; }
    .main-header { font-size: 3.5rem; color: #E85D04; font-weight: 800; font-family: 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 2px; line-height: 1; margin: 0; }
    .sub-header { font-size: 1.1rem; color: #888; font-family: 'Courier New', monospace; font-weight: 600; margin-top: 5px; white-space: nowrap; }
    
    .stChatMessage .stChatMessageAvatar { border: 2px solid #E85D04; border-radius: 50%; box-shadow: 0 0 10px rgba(232, 93, 4, 0.3); }
    
    /* Verdict Boxes */
    .decision-box-red { border: 2px solid #D32F2F; background-color: rgba(211, 47, 47, 0.1); padding: 20px; border-radius: 8px; color: #ffcdd2; box-shadow: 0 0 15px rgba(211, 47, 47, 0.2); }
    .decision-box-orange { border: 2px solid #F57C00; background-color: rgba(245, 124, 0, 0.1); padding: 20px; border-radius: 8px; color: #ffe0b2; box-shadow: 0 0 15px rgba(245, 124, 0, 0.2); }
    .decision-box-green { border: 2px solid #388E3C; background-color: rgba(56, 142, 60, 0.1); padding: 20px; border-radius: 8px; color: #c8e6c9; box-shadow: 0 0 15px rgba(56, 142, 60, 0.2); }
    
    /* Council Row */
    .council-container { margin-bottom: 20px; text-align:center; }
    .council-row { display: flex; gap: 15px; justify-content: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; }
    .council-member { text-align: center; font-size: 0.8rem; color: #888; }
    .council-img { width: 50px; height: 50px; border-radius: 50%; border: 2px solid #444; margin-bottom: 5px; transition: transform 0.2s; object-fit: cover; }
    .council-img:hover { transform: scale(1.1); border-color: #E85D04; }
    
    /* Progress Bar */
    .stProgress > div > div > div > div { background-color: #E85D04; }
    
    /* Logs */
    .success-log {
        color: #4CAF50; font-weight: bold; padding: 10px; border-left: 3px solid #4CAF50;
        background-color: rgba(76, 175, 80, 0.1); margin-bottom: 5px; border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- ASSETS ---
def get_asset_path(filename_part):
    for name in [filename_part, filename_part.lower(), filename_part.capitalize()]:
        for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".ico"]:
            path = f"assets/{name}{ext}"
            if os.path.exists(path): return path
    return "👤"

AVATARS = {
    "user": "👤",
    "evena": get_asset_path("evena"),
    "keres": get_asset_path("keres"),
    "liorah": get_asset_path("liorah"),
    "ethan": get_asset_path("ethan"),
    "krypt": get_asset_path("Krypt"),
    "phoebe": get_asset_path("phoebe"),
    "avenor": get_asset_path("avenor"),
    "logo": get_asset_path("logo-barelvox"),
    "barel": get_asset_path("barel")
}

# --- RENDER COUNCIL ---
def render_council():
    html = '<div class="council-container"><div class="council-row">'
    for member in ["evena", "keres", "liorah", "ethan", "krypt", "phoebe"]:
        path = AVATARS[member]
        img_b64 = get_img_as_base64(path)
        if img_b64:
            src = f"data:image/png;base64,{img_b64}"
        else:
            src = "https://ui-avatars.com/api/?name=" + member + "&background=333&color=fff" 
        html += f'<div class="council-member"><img src="{src}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": AVATARS["avenor"],
        "content": "Le Council OEE est en session. Mes experts sont connectés et prêts à intervenir.<br>Déposez le DCE pour initier le protocole."
    })

if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "full_context" not in st.session_state: st.session_state.full_context = ""

# --- SIDEBAR ---
with st.sidebar:
    if AVATARS["barel"] != "👤": st.image(AVATARS["barel"], use_column_width=True)
    else: st.markdown("## 🏗️ BAREL VOX")
    st.markdown("---")
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"Moteur Connecté ({MODEL_NAME}) 🟢")
    else: st.warning("Moteur en attente...")
    st.markdown("---")
    st.markdown("### 🧬 ÉTAT DU CONSEIL")
    st.markdown("**Evena** (Orchestratrice) : 🟢 Prête")
    st.markdown("**Kérès** (Nettoyeur) : 🟢 Prêt")
    st.markdown("**Trinité** (Experts) : 🟢 Prêts")
    st.markdown("**Phoebe** (Synthèse) : 🟢 Prête")
    st.markdown("**Avenor** (Arbitre) : 🟢 En attente")
    st.markdown("---")
    if st.button("🔄 Reset Session"):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "name": "Avenor",
            "avatar": AVATARS["avenor"],
            "content": "Le Council OEE est en session. Mes experts sont connectés et prêts à intervenir.<br>Déposez le DCE pour initier le protocole."
        })
        st.session_state.analysis_complete = False
        st.session_state.full_context = ""
        st.rerun()

# --- HEADER ---
logo_b64 = get_img_as_base64(AVATARS["logo"])
st.markdown(f"""
<div class="header-container">
    <img src="data:image/png;base64,{logo_b64}" class="header-logo">
    <div class="header-text-block">
        <div class="main-header">BAREL VOX</div>
        <div class="sub-header">Architecture Anti-Sycophancie • Council OEE Powered by Or El Even</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 1. EVENA : EXTRACTION JSON (Python Pur) ---
def evena_extract_json(reader):
    # Transforme le PDF en structure JSON (Page par Page)
    # Plus léger à manipuler pour le Python qu'un String géant
    doc_structure = {}
    total_text_length = 0
    
    # On limite intelligemment à 80 pages pour le MVP
    max_pages = min(80, len(reader.pages))
    
    for i in range(max_pages):
        page_content = reader.pages[i].extract_text()
        # Nettoyage primaire immédiat
        page_content = re.sub(r'\n+', ' ', page_content) # Supprime sauts de ligne
        page_content = re.sub(r'\s+', ' ', page_content) # Supprime double espaces
        doc_structure[f"page_{i+1}"] = page_content
        total_text_length += len(page_content)
        
    return doc_structure, total_text_length

# --- 2. KERES : ANONYMISATION (Simulation Python) ---
def keres_anonymize_json(json_data):
    # Regex simple pour simuler le travail sans appel API
    # On remplace les patterns d'emails et téléphones
    str_data = json.dumps(json_data, ensure_ascii=False)
    
    # Anonymisation basique
    str_data = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_HIDDEN]', str_data)
    str_data = re.sub(r'\b0[1-9]([-. ]?[0-9]{2}){4}\b', '[PHONE_HIDDEN]', str_data)
    
    return str_data # Retourne un String JSON ready pour l'API

# --- API GEMINI (MODE JSON) ---
def call_gemini_json(role_prompt, user_content):
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"})
    full_prompt = f"{role_prompt}\n\n---\n\nDOCUMENT JSON SOURCE :\n{user_content}"
    try:
        response = model.generate_content(full_prompt)
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# --- API GEMINI (MODE TEXTE FINAL) ---
def call_gemini_text(role_prompt, user_content):
    model = genai.GenerativeModel(MODEL_NAME)
    full_prompt = f"{role_prompt}\n\n---\n\nDONNÉES STRUCTURÉES :\n{user_content}"
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Erreur : {str(e)}"

# --- PROMPTS ---
# Trinité travaille sur le JSON et renvoie du JSON (Super efficace)
P_TRINITE = """
Tu es le moteur d'analyse du CONSEIL OEE.
Analyse ce contenu JSON (DCE BTP).
Génère un JSON strict avec 3 clés : "liorah", "ethan", "krypt".
Pour chaque clé, fournis :
- "analyse" : Un texte de 5 lignes MAX sur les risques critiques.
- "flag" : Un émoji unique (🔴, 🟠 ou 🟢).

RÔLES :
1. LIORAH (Juridique) : Pénalités, Assurances, Normes manquantes.
2. ETHAN (Risques) : Planning, Co-activité, Sécurité.
3. KRYPT (Data) : Incohérences chiffres/unités.
"""

# Avenor ne reçoit QUE le JSON de Trinité (Pas le document source)
P_AVENOR = """Tu es AVENOR. Arbitre.
Voici les rapports JSON des experts.
Synthétise et Tranche pour le client.

ALGO :
- Si un expert a mis 🔴 -> Verdict 🔴 (DANGER)
- Si majorité 🟠 -> Verdict 🟠 (VIGILANCE)
- Sinon -> 🟢 (RAS)

FORMAT DE SORTIE :
[FLAG : X] (Mets l'émoji ici)

### DÉCISION DU CONSEIL
**Verdict :** (2 phrases max, direct)
**Points de Vigilance :** (Top 3)
**Conseil Stratégique :** (1 action)"""

P_CHAT_AVENOR = "Tu es AVENOR. Réponds au client. Sois pro, direct, expert BTP."

# --- CHAT UI ---
st.markdown(render_council(), unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg["avatar"]):
        if msg["name"] == "Avenor" and "DÉCISION DU CONSEIL" in msg["content"]:
            css_class = "decision-box-green"
            if "🔴" in msg["content"]: css_class = "decision-box-red"
            elif "🟠" in msg["content"]: css_class = "decision-box-orange"
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            if msg["role"] == "assistant":
                st.markdown(f"**{msg['name']}**")
                st.markdown(msg["content"], unsafe_allow_html=True)
            else:
                st.write(msg["content"])

# --- EXECUTION FLOW ---
if not st.session_state.analysis_complete:
    uploaded_file = st.file_uploader("Upload DCE", type=['pdf'], label_visibility="collapsed")

    if uploaded_file:
        if not api_key:
            st.error("⛔ Clé API manquante.")
            st.stop()
            
        st.session_state.messages.append({"role": "user", "name": "Utilisateur", "avatar": AVATARS["user"], "content": f"Dossier transmis : {uploaded_file.name}"})
        with st.chat_message("user", avatar=AVATARS["user"]): st.write(f"Dossier transmis : **{uploaded_file.name}**")
            
        log_container = st.container()
        progress_bar = st.progress(0, text="Initialisation...")
        
        try:
            # 1. EVENA (Python Pur - Extraction JSON)
            progress_bar.progress(10, text="Evena : Lecture & Structure JSON...")
            reader = PdfReader(uploaded_file)
            json_doc, doc_len = evena_extract_json(reader)
            log_container.markdown(f'<div class="success-log">✅ Evena : Extraction JSON terminée (Volume: {doc_len} chars)</div>', unsafe_allow_html=True)
            
            # 2. KERES (Python Pur - Anonymisation Regex)
            time.sleep(1)
            progress_bar.progress(30, text="Kérès : Anonymisation du JSON...")
            clean_json_str = keres_anonymize_json(json_doc)
            log_container.markdown('<div class="success-log">✅ Kérès : Données anonymisées et nettoyées</div>', unsafe_allow_html=True)
            
            # 3. TRINITÉ (API 1 - Envoi du JSON pour analyse)
            time.sleep(2)
            progress_bar.progress(60, text="Trinité : Analyse Expert (Appel Unique)...")
            
            # On envoie les 60 000 premiers caractères du JSON pour être sûr de passer (env 20-30 pages denses)
            # C'est la limite safe pour le Free Tier en un seul appel
            trinity_result = call_gemini_json(P_TRINITE, clean_json_str[:60000])
            
            if "error" in trinity_result:
                raise Exception(trinity_result["error"])
            
            log_container.markdown(f'''
            <div class="success-log">
            ✅ <b>Trinité : Rapports Validés</b><br>
            - Juridique : {trinity_result.get('liorah', {}).get('flag', '❓')}<br>
            - Risques : {trinity_result.get('ethan', {}).get('flag', '❓')}<br>
            - Data : {trinity_result.get('krypt', {}).get('flag', '❓')}
            </div>
            ''', unsafe_allow_html=True)
            
            # 4. PHOEBE (Formatage Python - Pas d'API)
            time.sleep(1)
            progress_bar.progress(80, text="Phoebe : Compilation...")
            log_container.markdown('<div class="success-log">✅ Phoebe : Dossier transmis à Avenor</div>', unsafe_allow_html=True)
            
            # 5. AVENOR (API 2 - Verdict sur le JSON de Trinité)
            time.sleep(2)
            progress_bar.progress(95, text="Avenor : Verdict final...")
            
            # Avenor ne lit que le résultat de Trinité (très léger)
            verdict = call_gemini_text(P_AVENOR, json.dumps(trinity_result))
            
            progress_bar.progress(100, text="Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            # Sauvegarde pour le Chat
            st.session_state.full_context = f"ANALYSE EXPERTS:\n{json.dumps(trinity_result)}\nVERDICT:\n{verdict}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": verdict})
            st.rerun()

        except Exception as e:
            progress_bar.empty()
            st.error(f"Erreur critique : {str(e)}")

if st.session_state.analysis_complete:
    user_input = st.chat_input("Question pour Avenor...")
    if user_input:
        st.session_state.messages.append({"role": "user", "name": "Stéphane", "avatar": AVATARS["user"], "content": user_input})
        with st.chat_message("user", avatar=AVATARS["user"]): st.write(user_input)
            
        with st.spinner("Avenor réfléchit..."):
            full_prompt = f"{P_CHAT_AVENOR}\nCTX:\n{st.session_state.full_context}\nQ: {user_input}"
            model = genai.GenerativeModel(MODEL_NAME)
            reply = model.generate_content(full_prompt).text
            
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": reply})
        with st.chat_message("assistant", avatar=AVATARS["avenor"]): st.write(reply)