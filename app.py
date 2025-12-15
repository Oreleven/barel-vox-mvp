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
        font-size: 3rem;
        color: #E85D04; /* Orange BTP */
        font-weight: 800;
        font-family: 'Helvetica Neue', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 10px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        font-family: 'Courier New', monospace;
        margin-bottom: 2rem;
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
    
    /* Signature du Conseil (Petits avatars) */
    .council-signature img {
        border-radius: 50%;
        border: 1px solid #555;
        margin-right: 10px;
        transition: transform 0.3s;
    }
    .council-signature img:hover {
        transform: scale(1.2);
        border-color: #E85D04;
    }
</style>
""", unsafe_allow_html=True)

# --- GESTION ROBUSTE DES IMAGES ---
def get_asset_path(base_name):
    # Cherche l'image peu importe l'extension ou la casse
    for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG"]:
        path = f"assets/{base_name}{ext}"
        if os.path.exists(path):
            return path
    return "👤" # Fallback emoji si image manquante

# MAPPING DES AVATARS (Pour le chat)
AVATARS = {
    "user": "👤",
    "keres": get_asset_path("keres"),
    "liorah": get_asset_path("liorah"),
    "ethan": get_asset_path("ethan"),
    "krypt": get_asset_path("krypt"),
    "phoebe": get_asset_path("phoebe"),
    "avenor": get_asset_path("avenor"),
}

# --- INITIALISATION SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Intro Avenor
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": AVATARS["avenor"],
        "content": "Le Council OEE est en session. Kérès, Liorah, Ethan, Krypt et Phoebe sont connectés. Déposez le DCE pour initier le protocole."
    })

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
    
if "full_context" not in st.session_state:
    st.session_state.full_context = ""

# --- SIDEBAR (Photo Barel + Statuts Verts) ---
with st.sidebar:
    # 1. PHOTO DU PATRON (Barel)
    barel_path = get_asset_path("barel")
    if barel_path != "👤":
        st.image(barel_path, use_column_width=True)
    else:
        st.markdown("## 🏗️ BAREL VOX")
    
    st.markdown("---")
    
    # 2. INPUT CLÉ API
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password", help="Colle ta clé AI Studio ici.")
    
    if api_key:
        genai.configure(api_key=api_key)
        st.success("Moteur Connecté 🟢")
    else:
        st.warning("Moteur en attente...")
        
    st.markdown("---")
    
    # 3. ÉTAT DU COUNCIL (Tableau de bord vert)
    st.markdown("### 🧬 ÉTAT DU CONSEIL")
    st.markdown("👁️ **Kérès** (Nettoyeur) : 🟢 *OK*")
    st.markdown("⚖️ **Liorah** (Raison) : 🟢 *Prête*")
    st.markdown("⚡ **Ethan** (Contradiction) : 🟢 *Prêt*")
    st.markdown("👾 **Krypt** (Perturbation) : 🟢 *Prêt*")
    st.markdown("💎 **Phoebe** (Synthèse) : 🟢 *OK*")
    st.markdown("👑 **Avenor** (Arbitre) : 🟢 *En attente*")
    
    st.markdown("---")
    if st.button("🔄 Reset Session"):
        st.session_state.messages = []
        st.session_state.analysis_complete = False
        st.session_state.full_context = ""
        st.rerun()

# --- HEADER UI (Logo + Titre alignés) ---
col_logo, col_title = st.columns([1, 5])

with col_logo:
    logo_path = get_asset_path("logo-barelvox")
    if logo_path != "👤":
        st.image(logo_path, width=130)
    else:
        st.write("🏗️")

with col_title:
    st.markdown('<div class="main-header">BAREL VOX</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Architecture Anti-Sycophancie • Powered by Council OEE</div>', unsafe_allow_html=True)

# --- FONCTION MOTEUR (APPEL GEMINI) ---
def call_gemini(role_prompt, user_content, model_name="gemini-1.5-flash"):
    try:
        model = genai.GenerativeModel(model_name)
        full_prompt = f"{role_prompt}\n\n---\n\nDOCUMENT A TRAITER :\n{user_content}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Erreur Agent : {str(e)}"

# --- PROMPTS DU COUNCIL ---
P_KERES = """Tu es KÉRÈS. TA MISSION : Anonymiser et structurer.
Prends ce texte OCR brut (DCE BTP).
1. Enlève les noms de personnes, emails, téléphones -> remplace par [CONFIDENTIEL].
2. GARDE ABSOLUMENT : Prix, Dates, Pénalités, Quantités, Normes (DTU).
3. Ne résume pas. Rends un texte propre."""

P_LIORAH = """Tu es LIORAH (Juridique & Conformité).
Analyse ce texte BTP nettoyé.
Cherche : Pénalités de retard non plafonnées, Manque d'assurances, Clauses abusives, Références normes manquantes.
Format : Markdown, Liste à puces. Sois factuelle."""

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
Ne donne pas de décision, juste les faits purs."""

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

P_CHAT_AVENOR = """Tu es AVENOR, le chef du Conseil OEE.
Tu discutes maintenant avec le client (Stéphane).
Tu as en mémoire tout le dossier technique analysé précédemment.
Réponds à ses questions sur les risques, le juridique ou la data en te basant sur l'analyse faite.
Sois pro, direct, un peu autoritaire mais bienveillant (style Architecte Senior)."""

# --- AFFICHAGE HISTORIQUE CHAT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg["avatar"]):
        # Affichage spécial pour le verdict
        if msg["name"] == "Avenor" and "DÉCISION DU CONSEIL" in msg["content"]:
            css_class = "decision-box-green"
            if "🔴" in msg["content"]: css_class = "decision-box-red"
            elif "🟠" in msg["content"]: css_class = "decision-box-orange"
            
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
            
            # SIGNATURE DU CONSEIL (Les têtes sous le verdict)
            st.markdown("<br><small>Conseil réuni :</small>", unsafe_allow_html=True)
            cols_sig = st.columns([1,1,1,1,10])
            with cols_sig[0]: st.image(AVATARS["keres"], width=40)
            with cols_sig[1]: st.image(AVATARS["liorah"], width=40)
            with cols_sig[2]: st.image(AVATARS["ethan"], width=40)
            with cols_sig[3]: st.image(AVATARS["krypt"], width=40)
            
        else:
            st.markdown(f"**{msg['name']}**")
            st.write(msg["content"])

# --- ZONE D'UPLOAD (Se cache si analyse faite) ---
if not st.session_state.analysis_complete:
    uploaded_file = st.file_uploader("📂 Déposez le dossier (PDF) pour analyse...", type=['pdf'])

    if uploaded_file:
        if not api_key:
            st.error("⛔ Clé API manquante. Regarde la barre latérale.")
            st.stop()
            
        # 1. Message User
        st.session_state.messages.append({"role": "user", "name": "Utilisateur", "avatar": AVATARS["user"], "content": f"Dossier transmis : {uploaded_file.name}"})
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.write(f"Dossier transmis : **{uploaded_file.name}**")
            
        # 2. Pipeline
        status_box = st.status("🚀 Initialisation du Protocole OEE...", expanded=True)
        
        try:
            # A. Extraction
            status_box.write("📄 Lecture du PDF en cours...")
            reader = PdfReader(uploaded_file)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text() + "\n"
            
            # B. Kérès
            status_box.write("👁️ Kérès : Anonymisation et Structuration...")
            clean_text = call_gemini(P_KERES, raw_text[:30000]) # Limite safe
            
            # C. Trio Experts
            status_box.write("⚡ Déploiement des Experts (Liorah, Ethan, Krypt)...")
            rep_liorah = call_gemini(P_LIORAH, clean_text)
            status_box.write("⚖️ Liorah : Analyse Juridique terminée.")
            rep_ethan = call_gemini(P_ETHAN, clean_text)
            status_box.write("🛡️ Ethan : Analyse Risques terminée.")
            rep_krypt = call_gemini(P_KRYPT, clean_text)
            status_box.write("👾 Krypt : Analyse Data terminée.")
            
            # D. Phoebe (Secret)
            status_box.write("💎 Phoebe : Compilation et synthèse pour le Board...")
            input_phoebe = f"Rapport LIORAH:\n{rep_liorah}\n\nRapport ETHAN:\n{rep_ethan}\n\nRapport KRYPT:\n{rep_krypt}"
            rep_phoebe = call_gemini(P_PHOEBE, input_phoebe)
            
            # E. Avenor (Verdict)
            status_box.write("👑 Avenor : Délibération finale...")
            rep_avenor = call_gemini(P_AVENOR, rep_phoebe)
            
            status_box.update(label="✅ Audit Terminé", state="complete", expanded=False)
            
            # Sauvegarde du contexte pour le Chat
            st.session_state.full_context = f"CONTEXTE DOSSIER:\n{clean_text}\n\nANALYSES:\n{input_phoebe}\n\nVERDICT:\n{rep_avenor}"
            st.session_state.analysis_complete = True
            
            # Affichage Verdict
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor})
            st.rerun()

        except Exception as e:
            st.error(f"Erreur critique du Council : {e}")

# --- ZONE DE CHAT (Se débloque APRES l'analyse) ---
if st.session_state.analysis_complete:
    user_input = st.chat_input("Posez une question à Avenor sur le dossier...")
    
    if user_input:
        # Affiche message user
        st.session_state.messages.append({"role": "user", "name": "Stéphane", "avatar": AVATARS["user"], "content": user_input})
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.write(user_input)
            
        # Réponse Avenor avec mémoire
        with st.spinner("Avenor réfléchit..."):
            full_prompt = f"{P_CHAT_AVENOR}\n\nCONTEXTE COMPLET :\n{st.session_state.full_context}\n\nQUESTION UTILISATEUR : {user_input}"
            
            # On appelle Gemini (il joue le rôle d'Avenor Chat)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
            reply = response.text
            
        # Affiche réponse
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": reply})
        with st.chat_message("assistant", avatar=AVATARS["avenor"]):
            st.write(reply)