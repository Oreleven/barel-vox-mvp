import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import base64
import time

# --- CONFIGURATION MOTEUR ---
MODEL_NAME = "gemini-2.0-flash" 

# --- FONCTION UTILITAIRE (BASE64) ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

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
    
    /* Council Row (Toujours visible) */
    .council-container { margin-bottom: 20px; text-align:center; }
    .council-row { display: flex; gap: 15px; justify-content: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; }
    .council-member { text-align: center; font-size: 0.8rem; color: #888; }
    .council-img { width: 50px; height: 50px; border-radius: 50%; border: 2px solid #444; margin-bottom: 5px; transition: transform 0.2s; }
    .council-img:hover { transform: scale(1.1); border-color: #E85D04; }
    
    /* Progress Bar Color Hack */
    .stProgress > div > div > div > div {
        background-color: #E85D04;
    }
    
    /* Logs Steps */
    .step-log {
        padding: 8px;
        margin-bottom: 5px;
        border-left: 3px solid #E85D04;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 0 5px 5px 0;
    }
    .step-done { color: #4CAF50; font-weight: bold; }
    .step-running { color: #FF9800; font-weight: bold; animation: pulse 1.5s infinite; }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
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
    "keres": get_asset_path("keres"),
    "liorah": get_asset_path("liorah"),
    "ethan": get_asset_path("ethan"),
    "krypt": get_asset_path("Krypt"),
    "phoebe": get_asset_path("phoebe"),
    "avenor": get_asset_path("avenor"),
    "logo": get_asset_path("logo-barelvox"),
    "barel": get_asset_path("barel")
}

# --- FONCTION D'AFFICHAGE DU CONSEIL (HTML) ---
def render_council():
    html = '<div class="council-container"><div class="council-row">'
    for member in ["keres", "liorah", "ethan", "krypt", "phoebe"]:
        img_b64 = get_img_as_base64(AVATARS[member])
        if img_b64:
            html += f'<div class="council-member"><img src="data:image/png;base64,{img_b64}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": AVATARS["avenor"],
        "content": f"Le Council OEE est en session. Mes experts sont connectés.<br>Déposez le DCE pour initier le protocole."
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
    st.markdown("**Kérès** : 🟢 Prêt")
    st.markdown("**Trinité** : 🟢 Prêts")
    st.markdown("**Phoebe** : 🟢 Prête")
    st.markdown("**Avenor** : 🟢 En attente")
    st.markdown("---")
    if st.button("🔄 Reset Session"):
        st.session_state.messages = []
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

# --- FONCTION MOTEUR ROBUSTE ---
def call_gemini(role_prompt, user_content, retries=3):
    model = genai.GenerativeModel(MODEL_NAME)
    full_prompt = f"{role_prompt}\n\n---\n\nDOCUMENT A TRAITER :\n{user_content}"
    
    for attempt in range(retries):
        try:
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                time.sleep((attempt + 2) * 10) # Pause longue : 20s, 30s, 40s
                continue
            else:
                return f"⚠️ Erreur Agent : {error_msg}"
    return "⚠️ Erreur : Trafic saturé. Réessayez plus tard ou avec un fichier plus petit."

# --- PROMPTS ---
P_KERES = "Tu es KÉRÈS. Analyse ce début de DCE. Anonymise et structure les infos clés : Prix, Dates, Pénalités, Normes. Supprime Noms. Pas de blabla."
P_TRINITY = """Tu es le CONSEIL TECHNIQUE (La Trinité). Analyse ce segment critique du DCE.
ROLE 1 : LIORAH (Juridique) -> Cherche Pénalités, Assurances, Clauses abusives.
ROLE 2 : ETHAN (Risques) -> Cherche Planning, Co-activité, Sécurité.
ROLE 3 : KRYPT (Data) -> Cherche Incohérences chiffres/unités.
FORMAT SORTIE: 3 paragraphes distincts (LIORAH, ETHAN, KRYPT)."""
P_PHOEBE = "Tu es PHOEBE. Synthèse. Fusionne le rapport ci-dessous. Garde uniquement les points bloquants et critiques."
P_AVENOR = """Tu es AVENOR. Arbitre.
ALGO : Danger/Illégal -> 🔴. Doutes -> 🟠. RAS -> 🟢.
FORMAT STRICT :
[FLAG : X]
### DÉCISION DU CONSEIL
**Verdict :** (2 phrases max, direct)
**Points de Vigilance :** (Top 3)
**Conseil Stratégique :** (1 action)"""
P_CHAT_AVENOR = "Tu es AVENOR. Réponds au client sur le dossier. Sois pro, direct, expert BTP."

# --- ZONE CHAT & AFFICHAGE CONSEIL ---
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
            
        # CONTENEURS POUR L'AFFICHAGE PROGRESSIF
        progress_bar = st.progress(0, text="Initialisation...")
        log_container = st.container() # Pour empiler les logs
        
        # Fonction pour ajouter une ligne de log
        def add_log(text, status="running"):
            css = "step-running" if status == "running" else "step-done"
            icon = "⏳" if status == "running" else "✅"
            log_container.markdown(f'<div class="step-log {css}">{icon} {text}</div>', unsafe_allow_html=True)

        try:
            # ETAPE 1
            progress_bar.progress(10, text="Lecture du fichier...")
            reader = PdfReader(uploaded_file)
            max_pages = min(50, len(reader.pages))
            raw_text = ""
            for i in range(max_pages): raw_text += reader.pages[i].extract_text() + "\n"
            
            # ETAPE 2
            progress_bar.progress(30, text="Action Kérès...")
            add_log("Kérès : Analyse des pages clés...", "running")
            clean_text = call_gemini(P_KERES, raw_text[:20000]) # Réduit un peu pour la sécurité
            add_log("Kérès : Analyse terminée.", "done")
            
            # ETAPE 3
            progress_bar.progress(60, text="Action Trinité...")
            add_log("Trinité (Liorah/Ethan/Krypt) : Scan en cours...", "running")
            rep_trinity = call_gemini(P_TRINITY, clean_text)
            add_log("Trinité : Rapports Experts générés.", "done")
            
            # ETAPE 4
            progress_bar.progress(80, text="Action Phoebe...")
            add_log("Phoebe : Compilation Stratégique...", "running")
            rep_phoebe = call_gemini(P_PHOEBE, rep_trinity)
            add_log("Phoebe : Synthèse validée.", "done")
            
            # ETAPE 5
            progress_bar.progress(95, text="Action Avenor...")
            add_log("Avenor : Délibération finale...", "running")
            rep_avenor = call_gemini(P_AVENOR, rep_phoebe)
            add_log("Avenor : Verdict rendu.", "done")
            
            # FIN
            progress_bar.progress(100, text="✅ Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            st.session_state.full_context = f"CTX (Extrait):\n{clean_text}\nANALYSES:\n{rep_trinity}\nVERDICT:\n{rep_avenor}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor})
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