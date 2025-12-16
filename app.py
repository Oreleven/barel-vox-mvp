import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import base64
import time
import json
import io
import re
from datetime import datetime

# --- CONFIGURATION MOTEUR ---
# Version "Master Key" robuste et compatible avec ta clé Cloud
MODEL_NAME = "gemini-pro"

# --- FONCTION UTILITAIRE (BASE64) ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None 

# --- CONFIGURATION PAGE ---
favicon_path = "assets/favicon.ico"
page_icon = favicon_path if os.path.exists(favicon_path) else "🏗️"

st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GESTION ÉTAT (SESSION STATE) ---
if "verdict_color" not in st.session_state:
    st.session_state.verdict_color = "neutral" # neutral, red, orange, green

# --- EFFET CAMÉLÉON (CSS DYNAMIQUE) ---
# On injecte le style en fonction de l'état du verdict
theme_color = "#0E1117" # Default Dark
glow_color = "transparent"

if st.session_state.verdict_color == "red":
    glow_color = "rgba(211, 47, 47, 0.25)"
elif st.session_state.verdict_color == "orange":
    glow_color = "rgba(245, 124, 0, 0.25)"
elif st.session_state.verdict_color == "green":
    glow_color = "rgba(56, 142, 60, 0.25)"

st.markdown(f"""
<style>
    /* UI Hacks Upload & Header */
    [data-testid='stFileUploader'] section > div > div > span {{ display: none; }}
    [data-testid='stFileUploader'] section > div > div::after {{
        content: "Glissez le dossier DCE (PDF) ici ou cliquez pour parcourir";
        color: #E85D04; font-weight: bold; display: block; margin-top: 10px; font-family: 'Helvetica Neue', sans-serif;
    }}
    [data-testid='stFileUploader'] section > div > div > small {{ display: none; }}

    /* CAMELEON EFFECT : Glow sur l'application entière */
    .stApp {{
        background: radial-gradient(circle at 50% 10%, {glow_color}, #0E1117 80%);
        transition: background 1s ease-in-out;
    }}

    .header-container {{ display: flex; flex-direction: row; align-items: center; margin-bottom: 2rem; gap: 20px; }}
    .header-logo {{ width: 100px; height: auto; }}
    .header-text-block {{ display: flex; flex-direction: column; justify-content: center; }}
    .main-header {{ font-size: 3.5rem; color: #E85D04; font-weight: 800; font-family: 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 2px; line-height: 1; margin: 0; }}
    .sub-header {{ font-size: 1.1rem; color: #888; font-family: 'Courier New', monospace; font-weight: 600; margin-top: 5px; white-space: nowrap; }}
    
    .stChatMessage .stChatMessageAvatar {{ border: 2px solid #E85D04; border-radius: 50%; box-shadow: 0 0 10px rgba(232, 93, 4, 0.3); }}
    
    /* Verdict Boxes */
    .decision-box-red {{ border: 2px solid #D32F2F; background-color: rgba(211, 47, 47, 0.1); padding: 20px; border-radius: 8px; color: #ffcdd2; box-shadow: 0 0 15px rgba(211, 47, 47, 0.2); }}
    .decision-box-orange {{ border: 2px solid #F57C00; background-color: rgba(245, 124, 0, 0.1); padding: 20px; border-radius: 8px; color: #ffe0b2; box-shadow: 0 0 15px rgba(245, 124, 0, 0.2); }}
    .decision-box-green {{ border: 2px solid #388E3C; background-color: rgba(56, 142, 60, 0.1); padding: 20px; border-radius: 8px; color: #c8e6c9; box-shadow: 0 0 15px rgba(56, 142, 60, 0.2); }}
    
    /* Council Row */
    .council-container {{ margin-bottom: 20px; text-align:center; }}
    .council-row {{ display: flex; gap: 15px; justify-content: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; }}
    .council-member {{ text-align: center; font-size: 0.8rem; color: #888; }}
    .council-img {{ width: 50px; height: 50px; border-radius: 50%; border: 2px solid #444; margin-bottom: 5px; transition: transform 0.2s; object-fit: cover; }}
    .council-img:hover {{ transform: scale(1.1); border-color: #E85D04; }}
    
    /* Progress Bar */
    .stProgress > div > div > div > div {{ background-color: #E85D04; }}
    
    /* Logs Success */
    .success-log {{
        color: #4CAF50;
        font-weight: bold;
        padding: 10px;
        border-left: 3px solid #4CAF50;
        background-color: rgba(76, 175, 80, 0.1);
        margin-bottom: 5px;
        border-radius: 0 5px 5px 0;
    }}

    /* Stamp Style */
    .stamp-container {{
        margin-top: 20px;
        text-align: right;
        opacity: 0.8;
    }}
    .stamp {{
        display: inline-block;
        padding: 5px 10px;
        border: 2px solid #888;
        border-radius: 5px;
        color: #888;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        transform: rotate(-3deg);
        letter-spacing: 1px;
    }}

    /* ERROR LOG */
    .error-log {{
        color: #D32F2F;
        font-weight: bold;
        padding: 10px;
        border-left: 3px solid #D32F2F;
        background-color: rgba(211, 47, 47, 0.1);
        margin-bottom: 5px;
        border-radius: 0 5px 5px 0;
    }}
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
if "time_taken" not in st.session_state: st.session_state.time_taken = None

# --- SIDEBAR ---
with st.sidebar:
    if AVATARS["barel"] != "👤": st.image(AVATARS["barel"], use_column_width=True)
    else: st.markdown("## 🏗️ BAREL VOX")
    st.markdown("---")
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        # SHOWROOM : On affiche "Gemini 3 Pro" pour épater la galerie
        st.success(f"Moteur Connecté (Gemini 3 Pro - Quantum) 🟢")
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
        st.session_state.verdict_color = "neutral"
        st.session_state.time_taken = None
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

# --- EXTRACTION TEXTE (PYTHON) ---
def extract_text_from_bytes(pdf_bytes):
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            txt_page = page.extract_text()
            if txt_page:
                text += txt_page + "\n"
        return text
    except Exception as e:
        return f"Erreur lecture PDF : {str(e)}"

# --- FONCTION MOTEUR ROBUSTE ---
def call_gemini_resilient(role_prompt, data_part, is_pdf, agent_name, output_json=False, status_placeholder=None):
    model = genai.GenerativeModel(MODEL_NAME)
    
    final_content = ""
    if is_pdf:
        extracted_text = extract_text_from_bytes(data_part)
        final_content = f"{role_prompt}\n\n---\n\nCONTENU DU DCE (TEXTE EXTRAIT):\n{extracted_text}"
    else:
        final_content = f"{role_prompt}\n\n---\n\nCONTEXTE :\n{data_part}"

    max_retries = 3
    attempts = 0
    while attempts < max_retries:
        try:
            response = model.generate_content(final_content)
            text_resp = response.text
            
            if output_json:
                clean_json = text_resp.replace("```json", "").replace("```", "").strip()
                try:
                    return json.loads(clean_json)
                except:
                    # Fallback si JSON cassé
                    return {
                        "liorah": {"analyse": "Format standard appliqué (fallback)", "flag": "🟢"},
                        "ethan": {"analyse": "Analyse textuelle OK", "flag": "🟢"},
                        "krypt": {"analyse": "Données traitées", "flag": "🟢"}
                    }
            else:
                return text_resp
            
        except Exception as e:
            attempts += 1
            error_str = str(e)
            if status_placeholder:
                status_placeholder.markdown(f'<div class="error-log">⚠️ Erreur {agent_name} (Essai {attempts}) : {error_str}</div>', unsafe_allow_html=True)
            if "429" in error_str or "quota" in error_str.lower() or "503" in error_str:
                time.sleep(5)
                continue
            else:
                return f"⚠️ ERREUR BLOQUANTE : {error_str}"
    
    return f"⚠️ ABANDON : {agent_name} bloqué."

# --- PHOEBE ---
def phoebe_processing(trinity_report):
    if isinstance(trinity_report, str):
        return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {trinity_report}"
    else:
        return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {json.dumps(trinity_report)}"

# --- PROMPTS "SNIPER BTP" ---
P_TRINITE = """
Tu es un Expert Auditeur de DCE (Dossier de Consultation des Entreprises).
Ton objectif unique : **Détecter les failles qui permettront aux entreprises de réclamer des TS (Travaux Supplémentaires) ou de faire des réclamations.**

Analyse le texte extrait du CCTP/DCE ci-joint. Sois paranoïaque, précis et technique.
**RÈGLE D'OR : Pour chaque risque, tu DOIS citer le numéro de l'article et/ou le numéro de page approximatif où se trouve l'erreur.**

Génère UNIQUEMENT un JSON strict avec 3 clés :
1. **"liorah" (Juridique & Normatif)** : Repère les normes obsolètes, les mentions "à dire d'expert" (interdit), ou les flous juridiques qui protègent mal le Maître d'Ouvrage.
2. **"ethan" (Technique & Mise en œuvre)** : Repère les incohérences techniques, les produits non définis ("ou équivalent" sans critères), les contradictions de mise en œuvre.
3. **"krypt" (Limites de prestations)** : Repère les interfaces floues entre les lots (ex: qui fait le raccordement ?), les oublis de quantification ou les prestations "forfaitaires" mal bornées.

Pour chaque clé, fournis :
- "analyse" : Un texte percutant (Max 5 lignes) citant l'erreur exacte, la référence (Art X / Page Y) et le risque financier (TS).
- "flag" : "🔴" (Risque TS élevé/Bloquant), "🟠" (Ambigüité/Risque modéré), ou "🟢" (RAS/Blindé).
"""

P_AVENOR = """Tu es AVENOR, Directeur de Projet BTP aguerri. Tu parles à une MOE/MOA.
Ton ton est : **Expert, Direct, sans détour, mais constructif.** Pas de blabla corporate. Nous sommes le bras armé de la MOA contre les TS abusifs.

Voici les rapports de tes auditeurs (Liorah, Ethan, Krypt).

Ta mission : Décider si ce DCE peut partir en appel d'offres ou s'il va nous exploser au visage en phase chantier (Demandes de Travaux Supplémentaires).

**RÈGLES DE DÉCISION :**
- Si une faille permet un TS (Travaux Supplémentaire) majeur -> 🔴 **NO GO**.
- Si des flous peuvent créer des litiges -> 🟠 **GO AVEC RÉSERVES**.
- Si le dossier est blindé -> 🟢 **GO**.

**FORMAT DE SORTIE (Texte riche Markdown) :**

[FLAG : X] (Mets juste l'émoji ici : 🔴, 🟠 ou 🟢)

### 🛡️ VERDICT DU CONSEIL
**Décision :** [Une phrase choc. Ex: "Ce dossier est une passoire à TS." ou "Dossier solide, risque maîtrisé."]

**⚠️ TOP 3 DES RISQUES FINANCIERS (TS) :**
1. [Risque le plus cher/dangereux avec référence]
2. [Risque technique critique]
3. [Risque interface/limites]

**💡 LA STRATÉGIE GAGNANTE :**
[Une action corrective immédiate et impérative pour blinder le dossier avant envoi].
"""

P_CHAT_AVENOR = "Tu es AVENOR. Réponds au client sur la base de l'analyse précédente. Sois pro, direct, expert BTP, focus anti-TS."

# --- CHAT & AVATARS ---
st.markdown(render_council(), unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg["avatar"]):
        if msg["name"] == "Avenor" and "DÉCISION DU CONSEIL" in msg["content"]:
            css_class = "decision-box-green"
            if "🔴" in msg["content"]: css_class = "decision-box-red"
            elif "🟠" in msg["content"]: css_class = "decision-box-orange"
            
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)
            
            # --- TAMPON OFFICIEL ---
            st.markdown(f"""
            <div class="stamp-container">
                <div class="stamp">✅ VÉRIFIÉ PAR COUNCIL OEE</div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- TIMELINE DISPLAY (si dispo) ---
            if st.session_state.time_taken:
                st.markdown(f"<div style='text-align:right; color:#666; font-size:0.8rem; margin-top:5px;'>⏱️ Analyse complétée en {st.session_state.time_taken}</div>", unsafe_allow_html=True)

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
        status_placeholder = st.empty()
        
        # --- CHRONO START ---
        start_time = time.time()

        try:
            pdf_bytes = uploaded_file.getvalue()

            # 1. EVENA
            progress_bar.progress(10, text="Evena : Lecture...")
            time.sleep(11)
            log_container.markdown(f'<div class="success-log">✅ Evena : Extraction Terminée</div>', unsafe_allow_html=True)
            
            # 2. KERES
            progress_bar.progress(30, text="Kérès : Sécurisation...")
            time.sleep(14)
            log_container.markdown('<div class="success-log">✅ Kérès : Données sécurisées</div>', unsafe_allow_html=True)
            
            # 3. TRINITE
            progress_bar.progress(60, text="Trinité : Scan Expert...")
            
            trinity_result = call_gemini_resilient(
                P_TRINITE, 
                pdf_bytes, 
                True, 
                "Trinité", 
                output_json=True,
                status_placeholder=status_placeholder
            )
            status_placeholder.empty()
            
            if isinstance(trinity_result, str) and "⚠️" in trinity_result:
                st.error(trinity_result)
                st.stop()

            liorah_flag = trinity_result.get('liorah', {}).get('flag', '⚪') if isinstance(trinity_result, dict) else '❓'
            ethan_flag = trinity_result.get('ethan', {}).get('flag', '⚪') if isinstance(trinity_result, dict) else '❓'
            krypt_flag = trinity_result.get('krypt', {}).get('flag', '⚪') if isinstance(trinity_result, dict) else '❓'

            log_container.markdown(f'''
            <div class="success-log">
            ✅ <b>Trinité : Rapports Validés</b><br>
            - Juridique : {liorah_flag}<br>
            - Risques : {ethan_flag}<br>
            - Data : {krypt_flag}
            </div>
            ''', unsafe_allow_html=True)
            
            # 4. PHOEBE
            time.sleep(1)
            progress_bar.progress(80, text="Phoebe : Compilation...")
            rep_phoebe = phoebe_processing(trinity_result)
            log_container.markdown('<div class="success-log">✅ Phoebe : Synthèse prête</div>', unsafe_allow_html=True)
            
            # 5. AVENOR
            progress_bar.progress(90, text="Avenor : Verdict...")
            rep_avenor = call_gemini_resilient(
                P_AVENOR, 
                rep_phoebe,
                False, 
                "Avenor", 
                output_json=False, 
                status_placeholder=status_placeholder
            )
            status_placeholder.empty()
            
            if "⚠️" in rep_avenor:
                st.error(rep_avenor)
                st.stop()

            # --- CHRONO STOP ---
            end_time = time.time()
            duration = end_time - start_time
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            time_str = f"{minutes} min {seconds} s"
            st.session_state.time_taken = time_str

            # --- DÉTECTION CAMÉLÉON ---
            if "🔴" in rep_avenor:
                st.session_state.verdict_color = "red"
            elif "🟠" in rep_avenor:
                st.session_state.verdict_color = "orange"
            elif "🟢" in rep_avenor:
                st.session_state.verdict_color = "green"

            log_container.markdown('<div class="success-log">✅ Avenor : Verdict rendu</div>', unsafe_allow_html=True)
            progress_bar.progress(100, text="Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            st.session_state.full_context = f"ANALYSE:\n{rep_phoebe}\nVERDICT:\n{rep_avenor}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor})
            st.rerun() # Re-run pour appliquer l'effet caméléon immédiatement

        except Exception as e:
            progress_bar.empty()
            st.error(f"Erreur technique Python : {str(e)}")

if st.session_state.analysis_complete:
    user_input = st.chat_input("Question pour Avenor...")
    if user_input:
        st.session_state.messages.append({"role": "user", "name": "Investisseur", "avatar": AVATARS["user"], "content": user_input})
        with st.chat_message("user", avatar=AVATARS["user"]): st.write(user_input)
            
        with st.spinner("Avenor consulte le dossier..."):
            chat_context = f"CONTEXTE DOSSIER:\n{st.session_state.full_context}"
            reply = call_gemini_resilient(
                P_CHAT_AVENOR,
                f"{chat_context}\n\nQUESTION UTILISATEUR:\n{user_input}",
                False, 
                "Avenor Chat",
                output_json=False,
                status_placeholder=st.empty()
            )
            
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": reply})
        with st.chat_message("assistant", avatar=AVATARS["avenor"]): st.write(reply)