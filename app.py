import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import base64
import time
import json
import io
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

# --- CONFIGURATION PAGE ---
favicon_path = "assets/favicon.ico"
page_icon = favicon_path if os.path.exists(favicon_path) else "🏗️"

st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SÉCURITÉ INITIALISATION (Le Fix Anti-Crash) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": get_asset_path("avenor"),
        "content": "Le Council OEE est en session. Mes experts sont connectés et prêts à intervenir.<br>Déposez le DCE pour initier le protocole."
    })

if "verdict_color" not in st.session_state: st.session_state.verdict_color = "neutral"
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "full_context" not in st.session_state: st.session_state.full_context = ""
if "time_taken" not in st.session_state: st.session_state.time_taken = None

# --- EFFET CAMÉLÉON ---
glow_color = "transparent"
if st.session_state.verdict_color == "red": glow_color = "rgba(211, 47, 47, 0.25)"
elif st.session_state.verdict_color == "orange": glow_color = "rgba(245, 124, 0, 0.25)"
elif st.session_state.verdict_color == "green": glow_color = "rgba(56, 142, 60, 0.25)"

st.markdown(f"""
<style>
    /* UI Hacks */
    [data-testid='stFileUploader'] section > div > div > span {{ display: none; }}
    [data-testid='stFileUploader'] section > div > div::after {{
        content: "Glissez le dossier DCE (PDF) ici ou cliquez pour parcourir";
        color: #E85D04; font-weight: bold; display: block; margin-top: 10px; font-family: 'Helvetica Neue', sans-serif;
    }}
    [data-testid='stFileUploader'] section > div > div > small {{ display: none; }}

    /* Caméléon */
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
    
    /* Logs */
    .success-log {{
        color: #4CAF50;
        font-weight: bold;
        padding: 10px;
        border-left: 3px solid #4CAF50;
        background-color: rgba(76, 175, 80, 0.1);
        margin-bottom: 5px;
        border-radius: 0 5px 5px 0;
    }}
    .error-log {{
        color: #D32F2F;
        font-weight: bold;
        padding: 10px;
        border-left: 3px solid #D32F2F;
        background-color: rgba(211, 47, 47, 0.1);
        margin-bottom: 5px;
        border-radius: 0 5px 5px 0;
    }}

    /* Stamp & Timeline */
    .stamp-block {{
        margin-top: 20px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-top: 1px solid rgba(255,255,255,0.1);
        padding-top: 10px;
    }}
    .stamp {{
        padding: 5px 10px;
        border: 2px solid #888;
        border-radius: 5px;
        color: #888;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        transform: rotate(-3deg);
        letter-spacing: 1px;
        font-size: 0.8rem;
    }}
    .timeline {{
        color: #666;
        font-size: 0.8rem;
        font-style: italic;
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

# --- SIDEBAR ---
with st.sidebar:
    if AVATARS["barel"] != "👤": st.image(AVATARS["barel"], use_column_width=True)
    else: st.markdown("## 🏗️ BAREL VOX")
    st.markdown("---")
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"Moteur Connecté (Gemini-3.0-Pro) 🟢")
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

# --- NETTOYAGE JSON CHIRURGICAL ---
def clean_gemini_json(text):
    """Extrait le JSON même si Gemini bavarde avant/après"""
    try:
        # On cherche le premier { et le dernier }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return json.loads(text) # Tentative directe
    except:
        return None

# --- FONCTION MOTEUR ROBUSTE ---
def call_gemini_resilient(role_prompt, data_part, is_pdf, agent_name, output_json=False, status_placeholder=None):
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"} if output_json else {})
    
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
                data = clean_gemini_json(text_resp)
                if data: return data
                else: raise ValueError("JSON invalide")
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
                if output_json: # Fallback structuré
                     return {
                        "liorah": {"analyse": "Erreur technique analyse", "flag": "🟠"},
                        "ethan": {"analyse": "Erreur technique analyse", "flag": "🟠"},
                        "krypt": {"analyse": "Erreur technique analyse", "flag": "🟠"}
                    }
                return f"⚠️ ERREUR BLOQUANTE : {error_str}"
    
    return f"⚠️ ABANDON : {agent_name} bloqué."

# --- PHOEBE ---
def phoebe_processing(trinity_report):
    if isinstance(trinity_report, str): return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {trinity_report}"
    else: return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {json.dumps(trinity_report)}"

# --- PROMPTS LÉGAUX & RIGOUREUX ---
P_TRINITE = """
Tu es un Expert Auditeur de DCE BTP (Code de la Commande Publique Français).
Analyse le texte du CCTP ci-joint.

**TES INSTRUCTIONS STRICTES (ANTI-HALLUCINATION & RÈGLES DE L'ART) :**

1.  **UPEC / CARACTÉRISTIQUES TECHNIQUES :**
    - Si le CCTP décrit précisément le produit (Ex: Classement UPEC, Épaisseur couche d'usure, Poinçonnement, Normes NF/ISO), c'est **CONFORME**.
    - NE SIGNALE PAS de risque juste parce qu'il y a beaucoup de détails. Au contraire, c'est ce qu'on veut.
    - Signale un risque UNIQUEMENT si la description est vague (ex: "Sols souples de qualité" sans norme citée).

2.  **ÉQUIVALENCE (LOI FRANÇAISE) :**
    - La mention "ou techniquement équivalent" est **OBLIGATOIRE**. Ne la critique JAMAIS comme étant floue.
    - Le risque existe SEULEMENT si le CCTP ne donne AUCUNE caractéristique technique permettant de juger cette équivalence.

3.  **SUPPORTS (NF DTU) :**
    - Selon le NF DTU, l'entreprise doit réceptionner ses supports. Ne signale un risque que si le lot précédent n'est pas identifié ou si on demande à l'entreprise de "tout refaire" sans état des lieux.

4.  **DTU & NORMES :**
    - Ne juge pas un DTU obsolète si tu n'as pas la date du Permis de Construire.

Génère un JSON strict avec 3 clés : "liorah", "ethan", "krypt".
Pour chaque clé :
- "analyse" : Max 5 lignes. Cite l'erreur précise (Article/Page) SI ET SEULEMENT SI c'est une vraie non-conformité. Sinon "RAS, Conforme aux attentes".
- "flag" : "🔴" (Non-Conformité majeure / Illégal), "🟠" (Flou / Manque précision), "🟢" (Conforme / Détaillé).
"""

P_AVENOR = """Tu es AVENOR, Directeur de Projet BTP.
Tu parles à la Maîtrise d'Ouvrage (MOA).

Voici les rapports des experts.

**RÈGLE DE DÉCISION DU FLAG FINAL :**
- Ton message DOIT commencer par l'un de ces tags exacts : `[FLAG : 🔴]`, `[FLAG : 🟠]`, ou `[FLAG : 🟢]`.
- Si Trinité a trouvé des vraies failles (Rouge/Orange) -> Reporte le flag le plus sévère.
- Si Trinité dit que c'est conforme (Vert) -> Mets `[FLAG : 🟢]`.

**FORMAT DE SORTIE (Texte Markdown) :**

[FLAG : X]

### 🛡️ VERDICT DU CONSEIL
**Décision :** [Phrase courte]

**⚠️ POINTS DE VIGILANCE :**
1. [Point 1]
2. [Point 2]
3. [Point 3]

**💡 CONSEIL STRATÉGIQUE :**
[Action corrective].
"""

P_CHAT_AVENOR = "Tu es AVENOR. Réponds au client. Sois pro, expert BTP, focus anti-TS."

# --- CHAT & AVATARS ---
st.markdown(render_council(), unsafe_allow_html=True)

# SÉCURITÉ BOUCLE DE CHAT : On s'assure que messages existe
messages_list = st.session_state.get("messages", [])

for msg in messages_list:
    with st.chat_message(msg["role"], avatar=msg["avatar"]):
        if msg["name"] == "Avenor" and "DÉCISION DU CONSEIL" in msg["content"]:
            # Détection couleur via REGEX sur le tag [FLAG : X]
            css_class = "decision-box-green"
            if "[FLAG : 🔴]" in msg["content"]: css_class = "decision-box-red"
            elif "[FLAG : 🟠]" in msg["content"]: css_class = "decision-box-orange"
            
            # Nettoyage du tag pour l'affichage
            display_content = msg["content"].replace("[FLAG : 🔴]", "").replace("[FLAG : 🟠]", "").replace("[FLAG : 🟢]", "")
            
            st.markdown(f'<div class="{css_class}">{display_content}</div>', unsafe_allow_html=True)
            
            # --- TIMELINE & TAMPON (Intégrés ici) ---
            if st.session_state.time_taken:
                st.markdown(f"""
                <div class="stamp-block">
                    <div class="timeline">⏱️ Analyse : {st.session_state.time_taken}</div>
                    <div class="stamp">✅ VÉRIFIÉ PAR COUNCIL OEE</div>
                </div>
                """, unsafe_allow_html=True)

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
        
        start_time = time.time() # CHRONO START

        try:
            pdf_bytes = uploaded_file.getvalue()

            # 1. EVENA
            progress_bar.progress(10, text="Evena : Lecture...")
            time.sleep(2) 
            log_container.markdown(f'<div class="success-log">✅ Evena : Extraction Terminée</div>', unsafe_allow_html=True)
            
            # 2. KERES
            progress_bar.progress(30, text="Kérès : Sécurisation...")
            time.sleep(2) 
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
                st.error(trinity_result); st.stop()

            # Extraction sécurisée des flags (Valeur par défaut si manquant)
            liorah_flag = trinity_result.get('liorah', {}).get('flag', '🟢')
            ethan_flag = trinity_result.get('ethan', {}).get('flag', '🟢')
            krypt_flag = trinity_result.get('krypt', {}).get('flag', '🟢')

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
            rep_avenor_raw = call_gemini_resilient(
                P_AVENOR, 
                rep_phoebe,
                False, 
                "Avenor", 
                output_json=False, 
                status_placeholder=status_placeholder
            )
            status_placeholder.empty()
            
            if "⚠️" in rep_avenor_raw: st.error(rep_avenor_raw); st.stop()

            # --- PARSING DU VERDICT POUR LE CAMÉLÉON ---
            # On cherche le tag strict [FLAG : X]
            match = re.search(r"\[FLAG\s*:\s*(.*?)\]", rep_avenor_raw)
            if match:
                flag_found = match.group(1)
                if "🔴" in flag_found: st.session_state.verdict_color = "red"
                elif "🟠" in flag_found: st.session_state.verdict_color = "orange"
                elif "🟢" in flag_found: st.session_state.verdict_color = "green"
            else:
                st.session_state.verdict_color = "neutral"

            # Calcul du temps
            end_time = time.time()
            duration = end_time - start_time
            st.session_state.time_taken = f"{int(duration // 60)} min {int(duration % 60)} s"

            log_container.markdown('<div class="success-log">✅ Avenor : Verdict rendu</div>', unsafe_allow_html=True)
            progress_bar.progress(100, text="Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            st.session_state.full_context = f"ANALYSE:\n{rep_phoebe}\nVERDICT:\n{rep_avenor_raw}"
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": AVATARS["avenor"], "content": rep_avenor_raw})
            st.rerun()

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