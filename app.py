import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLES CSS (Cyber-BTP & Caméléon) ---
st.markdown("""
<style>
    /* Header Barel Vox */
    .main-header {
        font-size: 2.5rem;
        color: #E85D04; /* Orange BTP */
        text-align: center;
        font-weight: 800;
        font-family: 'Helvetica Neue', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Courier New', monospace;
    }
    
    /* Avatars avec bordures néons */
    .stChatMessage .stChatMessageAvatar {
        border: 2px solid #E85D04;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(232, 93, 4, 0.3);
    }
    
    /* EFFET CAMÉLÉON (Boites de décision) */
    .decision-box-red {
        border: 2px solid #D32F2F;
        background-color: rgba(211, 47, 47, 0.1);
        padding: 20px;
        border-radius: 8px;
        color: #ffcdd2;
        box-shadow: 0 0 15px rgba(211, 47, 47, 0.2);
    }
    .decision-box-orange {
        border: 2px solid #F57C00;
        background-color: rgba(245, 124, 0, 0.1);
        padding: 20px;
        border-radius: 8px;
        color: #ffe0b2;
        box-shadow: 0 0 15px rgba(245, 124, 0, 0.2);
    }
    .decision-box-green {
        border: 2px solid #388E3C;
        background-color: rgba(56, 142, 60, 0.1);
        padding: 20px;
        border-radius: 8px;
        color: #c8e6c9;
        box-shadow: 0 0 15px rgba(56, 142, 60, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- GESTION ROBUSTE DES AVATARS ---
def get_avatar(base_name):
    # Cherche l'image peu importe l'extension ou la casse
    for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG"]:
        path = f"assets/{base_name}{ext}"
        if os.path.exists(path):
            return path
    return "👤" # Fallback

# MAPPING DU COUNCIL (Tes fichiers mis à jour)
AVATARS = {
    "user": "👤",
    "keres": get_avatar("keres"),
    "liorah": get_avatar("liorah"),
    "ethan": get_avatar("ethan"),
    "krypt": get_avatar("krypt"),
    "phoebe": get_avatar("phoebe"),
    "avenor": get_avatar("avenor"),
}

# --- INITIALISATION SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Intro Avenor
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor (Arbitre Final)",
        "avatar": AVATARS["avenor"],
        "content": "Le Council OEE est en session. Kérès, Liorah, Ethan, Krypt et Phoebe sont connectés. Déposez le DCE pour initier le protocole."
    })

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

# --- SIDEBAR & SÉCURITÉ ---
with st.sidebar:
    # Recherche intelligente du logo (PNG ou JPG)
    logo_path = get_avatar("logo-barelvox")
    
    if logo_path != "👤":
        # Si le logo est trouvé, on l'affiche en grand
        st.image(logo_path, use_column_width=True)
    else:
        # Sinon, on affiche le texte
        st.markdown("## 🏗️ BAREL VOX")
    
    st.markdown("---")
    
    # INPUT CLÉ API (Direct Drive)
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password", help="Colle ta clé AI Studio ici.")
    
    if api_key:
        genai.configure(api_key=api_key)
        st.success("Moteur Connecté 🟢")
    else:
        st.warning("Moteur en attente...")
        
    st.markdown("---")
    st.markdown("### 🧬 ÉTAT DU COUNCIL")
    st.markdown("👁️ **Kérès** (Nettoyeur) : *En ligne*")
    st.markdown("⚖️ **Liorah** (Raison) : *Prête*")
    st.markdown("⚡ **Ethan** (Contradiction) : *Prêt*")
    st.markdown("👾 **Krypt** (Perturbation) : *Prêt*")
    st.markdown("💎 **Phoebe** (Synthèse) : *En veille*")
    st.markdown("👑 **Avenor** (Arbitre) : *En attente*")
    
    st.markdown("---")
    if st.button("🔄 Reset Session"):
        st.session_state.messages = []
        st.session_state.analysis_complete = False
        st.rerun()

# --- HEADER UI ---
st.markdown('<div class="main-header">BAREL VOX</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Architecture Anti-Sycophancie • Powered by Council OEE</div>', unsafe_allow_html=True)

# --- FONCTION MOTEUR (APPEL GEMINI) ---
def call_gemini(role_prompt, user_content, model_name="gemini-1.5-flash"):
    try:
        model = genai.GenerativeModel(model_name)
        # On concatène le rôle et le contenu pour être sûr
        full_prompt = f"{role_prompt}\n\n---\n\nDOCUMENT A TRAITER :\n{user_content}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Erreur Agent : {str(e)}"

# --- PROMPTS DU COUNCIL (CERVEAUX) ---
P_KERES = """Tu es KÉRÈS. TA MISSION : Anonymiser et structurer.
Prends ce texte OCR brut (DCE BTP).
1. Enlève les noms de personnes, emails, téléphones -> remplace par [CONFIDENTIEL].
2. GARDE ABSOLUMENT : Prix, Dates, Pénalités, Quantités, Normes (DTU).
3. Ne résume pas. Rends un texte propre exploitable par des experts."""

P_LIORAH = """Tu es LIORAH (Juridique & Conformité).
Analyse ce texte BTP nettoyé.
Cherche : Pénalités de retard non plafonnées, Manque d'assurances, Clauses abusives, Références normes manquantes.
Format : Markdown, Liste à puces. Sois factuelle et juridique."""

P_ETHAN = """Tu es ETHAN (Risques & Contradiction).
Crash-test ce projet BTP. Sois brutal.
Cherche : Planning irréaliste (Hiver/Intempéries), Co-activité dangereuse, Risques sécurité oubliés, Budget sous-estimé.
Format : Markdown. Ton sévère."""

P_KRYPT = """Tu es KRYPT (Data & Anomalies).
Cherche les bugs dans la matrice.
Cherche : Incohérences d'unités (m2/m3), Matériaux obsolètes, Contradictions techniques, Chiffres aberrants.
Format : Markdown. Focus Data."""

P_PHOEBE = """Tu es PHOEBE (Compilation Secrète).
Voici 3 rapports d'experts (Liorah, Ethan, Krypt).
TA MISSION : Fusionner ces informations pour le Décideur (Avenor).
1. Supprime les doublons.
2. Garde uniquement les points critiques et bloquants.
3. Structure en : [Juridique] / [Risques] / [Data].
Ne donne pas de décision, juste les faits purs et durs."""

P_AVENOR = """Tu es AVENOR (Arbitre Final).
Voici la synthèse technique de Phoebe.
TA MISSION : Trancher pour le client.

ALGORITHME DE DÉCISION :
- Si danger mortel, illégal ou faillite assurée -> 🔴 (Rouge)
- Si doutes sérieux, flou ou risque financier -> 🟠 (Orange)
- Si RAS -> 🟢 (Vert)

FORMAT DE SORTIE (Strict) :
[FLAG : X] (Mets l'émoji ici)

### DÉCISION DU CONSEIL

**Verdict :** (2 phrases max, ton direct)

**Points de Vigilance Prioritaires :**
- (Liste les 3 points les plus graves)

**Conseil Stratégique :** (Une action immédiate)
"""

# --- AFFICHAGE CHAT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg["avatar"]):
        # Si c'est Avenor et qu'on a le verdict, on applique le style
        if msg["name"] == "Avenor (Arbitre Final)" and "DÉCISION DU CONSEIL" in msg["content"]:
            css_class = "decision-box-green" # Default
            if "🔴" in msg["content"]: css_class = "decision-box-red"
            elif "🟠" in msg["content"]: css_class = "decision-box-orange"
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"**{msg['name']}**")
            st.write(msg["content"])

# --- ZONE D'UPLOAD ---
uploaded_file = st.file_uploader("📂 Déposez le dossier (PDF) pour analyse...", type=['pdf'], disabled=st.session_state.analysis_complete)

# --- ORCHESTRATION DU COUNCIL ---
if uploaded_file and not st.session_state.analysis_complete:
    if not api_key:
        st.error("⛔ Clé API manquante. Regarde la barre latérale.")
        st.stop()
        
    # 1. User Upload
    st.session_state.messages.append({"role": "user", "name": "Utilisateur", "avatar": AVATARS["user"], "content": f"Dossier transmis : {uploaded_file.name}"})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.write(f"Dossier transmis : **{uploaded_file.name}**")
        
    # 2. Status Bar Dynamique
    status_box = st.status("🚀 Initialisation du Protocole OEE...", expanded=True)
    
    try:
        # A. EXTRACTION
        status_box.write("📄 Lecture du PDF en cours...")
        reader = PdfReader(uploaded_file)
        raw_text = ""
        for page in reader.pages:
            raw_text += page.extract_text() + "\n"
        
        # B. KÉRÈS (Nettoyage)
        status_box.write("👁️ Kérès : Anonymisation et Structuration...")
        clean_text = call_gemini(P_KERES, raw_text[:30000]) # Limite safe pour Flash
        
        # C. TRIO PARALLÈLE (Séquentiel rapide)
        status_box.write("⚡ Déploiement des Experts (Liorah, Ethan, Krypt)...")
        
        # Liorah
        rep_liorah = call_gemini(P_LIORAH, clean_text)
        st.toast("Liorah a terminé son audit.", icon="⚖️")
        
        # Ethan
        rep_ethan = call_gemini(P_ETHAN, clean_text)
        st.toast("Ethan a crash-testé le projet.", icon="🛡️")
        
        # Krypt
        rep_krypt = call_gemini(P_KRYPT, clean_text)
        st.toast("Krypt a scanné la Data.", icon="👾")
        
        # D. PHOEBE (Compilation)
        status_box.write("💎 Phoebe : Compilation et filtrage du bruit...")
        input_phoebe = f"Rapport LIORAH:\n{rep_liorah}\n\nRapport ETHAN:\n{rep_ethan}\n\nRapport KRYPT:\n{rep_krypt}"
        rep_phoebe = call_gemini(P_PHOEBE, input_phoebe)
        
        # (Optionnel : On peut afficher Phoebe si tu veux, sinon elle reste secrète)
        # st.session_state.messages.append({"role": "assistant", "name": "Phoebe", "avatar": AVATARS["phoebe"], "content": rep_phoebe})

        # E. AVENOR (Arbitrage)
        status_box.write("👑 Avenor : Délibération finale...")
        rep_avenor = call_gemini(P_AVENOR, rep_phoebe)
        
        status_box.update(label="✅ Audit Terminé", state="complete", expanded=False)
        
        # Affichage Final
        st.session_state.messages.append({"role": "assistant", "name": "Avenor (Arbitre Final)", "avatar": AVATARS["avenor"], "content": rep_avenor})
        st.rerun() # Refresh pour afficher le message avec le style CSS

    except Exception as e:
        st.error(f"Erreur critique du Council : {e}")

    st.session_state.analysis_complete = True