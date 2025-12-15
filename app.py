import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
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
    .decision-box-red { border: 2px solid #D32F2F; background-color: rgba(211, 47, 47, 0.1); padding: 20px; border-radius: 8px; color: #ffcdd2; box-shadow: 0 0 15px rgba(211, 47, 47, 0.2); }
    .decision-box-orange { border: 2px solid #F57C00; background-color: rgba(245, 124, 0, 0.1); padding: 20px; border-radius: 8px; color: #ffe0b2; box-shadow: 0 0 15px rgba(245, 124, 0, 0.2); }
    .decision-box-green { border: 2px solid #388E3C; background-color: rgba(56, 142, 60, 0.1); padding: 20px; border-radius: 8px; color: #c8e6c9; box-shadow: 0 0 15px rgba(56, 142, 60, 0.2); }
    .council-container { margin-bottom: 20px; text-align:center; }
    .council-row { display: flex; gap: 15px; justify-content: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; }
    .council-member { text-align: center; font-size: 0.8rem; color: #888; }
    .council-img { width: 50px; height: 50px; border-radius: 50%; border: 2px solid #444; margin-bottom: 5px; transition: transform 0.2s; object-fit: cover; }
    .council-img:hover { transform: scale(1.1); border-color: #E85D04; }
    .stProgress > div > div > div > div { background-color: #E85D04; }
    .success-log { color: #4CAF50; font-weight: bold; padding: 10px; border-left: 3px solid #4CAF50; background-color: rgba(76, 175, 80, 0.1); margin-bottom: 5px; border-radius: 0 5px 5px 0; }
    .waiting-log { color: #FF9800; font-weight: bold; padding: 10px; border-left: 3px solid #FF9800; background-color: rgba(255, 152, 0, 0.1); margin-bottom: 5px; border-radius: 0 5px 5px 0; animation: pulse 2s infinite;}
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.6;} 100% {opacity: 1;} }
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
        if img_b64: src = f"data:image/png;base64,{img_b64}"
        else: src = "https://ui-avatars.com/api/?name=" + member + "&background=333&color=fff" 
        html += f'<div class="council-member"><img src="{src}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"],
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
    st.markdown("**Evena** : 🟢 Prête")
    st.markdown("**Kérès** : 🟢 Prêt")
    st.markdown("**Trinité** : 🟢 Prêts")
    st.markdown("**Phoebe** : 🟢 Prête")
    st.markdown("**Avenor** : 🟢 En attente")
    st.markdown("---")
    if st.button("🔄 Reset Session"):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"],
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

# --- FONCTION MOTEUR "IMMORTELLE" ---
def call_gemini_resilient(role_prompt, user_content, agent_name, output_json=False, status_placeholder=None):
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"} if output_json else {})
    full_prompt = f"{role_prompt}\n\n---\n\nDOCUMENT A TRAITER :\n{user_content}"
    
    attempts = 0
    while True: # Boucle infinie tant que ça ne passe pas
        try:
            attempts += 1
            response = model.generate_content(full_prompt)
            if output_json: return json.loads(response.text)
            else: return response.text
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                # On affiche un message d'attente à l'utilisateur
                if status_placeholder:
                    status_placeholder.markdown(f'<div class="waiting-log">⏳ Trafic saturé pour {agent_name}. Pause technique de 20s (Tentative {attempts})...</div>', unsafe_allow_html=True)
                time.sleep(20) # On attend sagement
                continue # On recommence la boucle
            else:
                return f"⚠️ Erreur critique Agent {agent_name} : {error_str}"

# --- FONCTIONS LOCALES ---
def evena_extract_json(reader):
    doc_structure = {}
    max_pages = min(80, len(reader.pages))
    for i in range(max_pages):
        page_content = reader.pages[i].extract_text()
        page_content = re.sub(r'\n+', ' ', page_content) 
        doc_structure[f"page_{i+1}"] = page_content
    return doc_structure

def keres_anonymize_json(json_data):
    str_data = json.dumps(json_data, ensure_ascii=False)
    str_data = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_HIDDEN]', str_data)
    str_data = re.sub(r'\b0[1-9]([-. ]?[0-9]{2}){4}\b', '[PHONE_HIDDEN]', str_data)
    return str_data

def phoebe_processing(trinity_report):
    return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {trinity_report}"

# --- PROMPTS ---
P_TRINITE = """
Tu es le moteur d'analyse du CONSEIL OEE.
Analyse ce contenu JSON (DCE BTP).
Génère un JSON strict avec 3 clés : "liorah", "ethan", "krypt".
Pour chaque clé, fournis :
- "analyse" : Un texte de 5 lignes MAX sur les risques critiques.
- "flag" : Un émoji unique (🔴, 🟠 ou 🟢).
"""

P_AVENOR = """Tu es AVENOR. Arbitre.
Voici les rapports JSON des experts.
Synthétise et Tranche pour le client.
ALGO : Si un expert a mis 🔴 -> Verdict 🔴. Si majorité 🟠 -> Verdict 🟠. Sinon -> 🟢.
FORMAT SORTIE :
[FLAG : X]
### DÉCISION DU CONSEIL
**Verdict :** (2 phrases max)
**Points de Vigilance :** (Top 3)
**Conseil Stratégique :** (1 action)"""

P_CHAT_AVENOR = "Tu es AVENOR. Réponds au client. Sois pro, direct, expert BTP."

# --- CHAT & AVATARS ---
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

# --- EXECUTION ---
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
        status_placeholder = st.empty() # Pour les messages d'attente
        
        try:
            # 1. EVENA
            progress_bar.progress(10, text="Evena : Lecture du fichier...")
            reader = PdfReader(uploaded_file)
            json_doc = evena_extract_json(reader)
            log_container.markdown(f'<div class="success-log">✅ Evena : Extraction Terminée</div>', unsafe_allow_html=True)
            
            # 2. KERES
            time.sleep(1)
            progress_bar.progress(30, text="Kérès : Nettoyage...")
            clean_json_str = keres_anonymize_json(json_doc)
            log_container.markdown('<div class="success-log">✅ Kérès : Données anonymisées</div>', unsafe_allow_html=True)
            
            # 3. TRINITE (API RESILIENTE)
            progress_bar.progress(60, text="Trinité : Scan Expert...")
            # On passe le placeholder pour afficher les messages d'attente
            trinity_result = call_gemini_resilient(P_TRINITE, clean_json_str[:60000], "Trinité", output_json=True, status_placeholder=status_placeholder)
            
            # Nettoyage du placeholder d'attente
            status_placeholder.empty()
            
            log_container.markdown(f'''
            <div class="success-log">
            ✅ <b>Trinité : Rapports Validés</b><br>
            - Juridique : {trinity_result.get('liorah', {}).get('flag', '❓')}<br>
            - Risques : {trinity_result.get('ethan', {}).get('flag', '❓')}<br>
            - Data : {trinity_result.get('krypt', {}).get('flag', '❓')}
            </div>
            ''', unsafe_allow_html=True)
            
            # 4. PHOEBE
            time.sleep(1)
            progress_bar.progress(80, text="Phoebe : Compilation...")
            rep_phoebe = phoebe_processing(json.dumps(trinity_result))
            log_container.markdown('<div class="success-log">✅ Phoebe : Synthèse prête</div>', unsafe_allow_html=True)
            
            # 5. AVENOR (API RESILIENTE)
            progress_bar.progress(90, text="Avenor : Délibération...")
            rep_avenor = call_gemini_resilient(P_AVENOR, rep_phoebe, "Avenor", output_json=False, status_placeholder=status_placeholder)
            status_placeholder.empty()
            
            log_container.markdown('<div class="success-log">✅ Avenor : Verdict rendu</div>', unsafe_allow_html=True)
            progress_bar.progress(100, text="Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            st.session_state.full_context = f"ANALYSE:\n{rep_phoebe}\nVERDICT:\n{rep_avenor}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor})
            st.rerun()

        except Exception as e:
            progress_bar.empty()
            st.error(f"Erreur technique : {str(e)}")

if st.session_state.analysis_complete:
    user_input = st.chat_input("Question pour Avenor...")
    if user_input:
        st.session_state.messages.append({"role": "user", "name": "Stéphane", "avatar": AVATARS["user"], "content": user_input})
        with st.chat_message("user", avatar=AVATARS["user"]): st.write(user_input)
            
        with st.spinner("Avenor réfléchit..."):
            full_prompt = f"{P_CHAT_AVENOR}\nCTX:\n{st.session_state.full_context}\nQ: {user_input}"
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                reply = model.generate_content(full_prompt).text
            except: reply = "Désolé, je suis surchargé. Réessayez."
            
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": reply})
        with st.chat_message("assistant", avatar=AVATARS["avenor"]): st.write(reply)