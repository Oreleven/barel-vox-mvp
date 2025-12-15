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
    # Intro simple, le conseil est affiché en dur en dessous
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
                time.sleep((attempt + 2) * 5) # Pause incrémentale
                continue
            else:
                return f"⚠️ Erreur Agent : {error_msg}"
    return "⚠️ Erreur : Trafic saturé. Réessayez."

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
# On affiche les avatars en permanence sous le titre pour qu'ils ne disparaissent pas
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
            
        status_box = st.status(f"🚀 Initialisation du Protocole OEE...", expanded=True)
        try:
            status_box.write("📄 Lecture du PDF (Extraction Optimisée)...")
            reader = PdfReader(uploaded_file)
            
            # --- OPTIMISATION : ON NE LIT QUE LES 50 PREMIÈRES PAGES POUR LE MVP ---
            # Cela évite le crash sur les gros CCTP tout en gardant l'essentiel
            max_pages = min(50, len(reader.pages)) 
            raw_text = ""
            for i in range(max_pages):
                raw_text += reader.pages[i].extract_text() + "\n"
            
            status_box.write(f"👁️ Kérès : Analyse des {max_pages} pages clés...")
            clean_text = call_gemini(P_KERES, raw_text[:25000]) # Limite charactères pour vitesse
            
            status_box.write("⚡ Trinité : Scan Juridique, Risques & Data...")
            rep_trinity = call_gemini(P_TRINITY, clean_text)
            
            status_box.write("💎 Phoebe : Compilation Stratégique...")
            rep_phoebe = call_gemini(P_PHOEBE, rep_trinity)
            
            status_box.write("👑 Avenor : Verdict...")
            rep_avenor = call_gemini(P_AVENOR, rep_phoebe)
            
            status_box.update(label="✅ Audit Terminé", state="complete", expanded=False)
            
            st.session_state.full_context = f"CTX (Extrait):\n{clean_text}\nANALYSES:\n{rep_trinity}\nVERDICT:\n{rep_avenor}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor})
            st.rerun()

        except Exception as e:
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