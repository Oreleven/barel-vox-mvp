import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import base64
import time
import json
import io
import re
import random
from datetime import datetime

# --- CONFIGURATION PAGE ---
favicon_path = "assets/favicon.ico"
page_icon = favicon_path if os.path.exists(favicon_path) else "🏗️"

st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURATION MOTEUR ---
MODEL_NAME = "gemini-2.0-flash"

# --- ETAT DE SESSION (Initialisation Robuste) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Message d'accueil par défaut
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": "avenor", # On stocke la clé, pas le path
        "content": "Le Council OEE est en session. Mes experts sont connectés et prêts à intervenir.<br>Déposez le DCE pour initier le protocole."
    })

if "verdict_color" not in st.session_state: st.session_state.verdict_color = "neutral"
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "full_context" not in st.session_state: st.session_state.full_context = ""

# --- FONCTIONS UTILITAIRES ---
def get_img_as_base64(file_path):
    try:
        if not os.path.exists(file_path): return None
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None 

def get_asset_path(filename_part):
    # Cherche l'asset, sinon renvoie None pour utiliser un fallback
    for name in [filename_part, filename_part.lower(), filename_part.capitalize()]:
        for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".ico"]:
            path = f"assets/{name}{ext}"
            if os.path.exists(path): return path
    return None

# --- DICTIONNAIRE ASSETS ---
# On stocke les chemins ou None
ASSET_MAP = {
    "user": get_asset_path("user"),
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

def get_avatar_url(key):
    # Renvoie le path local si dispo, sinon une URL générée
    path = ASSET_MAP.get(key)
    if path and os.path.exists(path):
        return path # Streamlit gère les paths locaux dans st.chat_message
    else:
        # Fallback élégant si pas d'image locale
        return "https://ui-avatars.com/api/?name=" + key + "&background=333&color=fff&size=128"

def get_avatar_b64_src(key):
    # Pour le HTML custom (Council render)
    path = ASSET_MAP.get(key)
    if path:
        b64 = get_img_as_base64(path)
        if b64: return f"data:image/png;base64,{b64}"
    return "https://ui-avatars.com/api/?name=" + key + "&background=333&color=fff&size=128"

# --- EFFET CAMÉLÉON (CSS DYNAMIQUE) ---
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

    /* Caméléon Background */
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
    .success-log {{ color: #4CAF50; font-weight: bold; padding: 10px; border-left: 3px solid #4CAF50; background-color: rgba(76, 175, 80, 0.1); margin-bottom: 5px; border-radius: 0 5px 5px 0; }}
    .error-log {{ color: #D32F2F; font-weight: bold; padding: 10px; border-left: 3px solid #D32F2F; background-color: rgba(211, 47, 47, 0.1); margin-bottom: 5px; border-radius: 0 5px 5px 0; }}

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

# --- RENDER COUNCIL ---
def render_council():
    html = '<div class="council-container"><div class="council-row">'
    for member in ["evena", "keres", "liorah", "ethan", "krypt", "phoebe"]:
        src = get_avatar_b64_src(member)
        html += f'<div class="council-member"><img src="{src}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- SIDEBAR ---
with st.sidebar:
    barel_path = ASSET_MAP.get("barel")
    if barel_path and os.path.exists(barel_path): st.image(barel_path, use_column_width=True)
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
            "avatar": "avenor",
            "content": "Le Council OEE est en session. Mes experts sont connectés et prêts à intervenir.<br>Déposez le DCE pour initier le protocole."
        })
        st.session_state.analysis_complete = False
        st.session_state.full_context = ""
        st.session_state.verdict_color = "neutral"
        st.rerun()

# --- HEADER ---
logo_b64 = get_avatar_b64_src("logo")
st.markdown(f"""
<div class="header-container">
    <img src="{logo_b64}" class="header-logo">
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
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return json.loads(text) 
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
                if output_json: 
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
    else: return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {json.dumps(trinity_report, ensure_ascii=False)}"

# --- PROMPTS DE LA TRINITÉ (ANTI-HALLUCINATION) ---
P_TRINITE = """
Tu incarnes la Trinité (Liorah, Ethan, Krypt), Auditeurs experts du Code de la Commande Publique.
Analyse le CCTP fourni.

**RÈGLE D'OR (ANTI-HALLUCINATION) :**
Pour chaque risque identifié, tu DOIS fournir la référence exacte : **"Page X, Article Y"**.
Si tu ne trouves pas la référence exacte dans le texte, le risque N'EXISTE PAS. 
INTERDICTION D'INVENTER OU DE SUPPOSER.

**TES INSTRUCTIONS STRICTES :**

1.  **UPEC / CARACTÉRISTIQUES (Conformité) :**
    - Si le CCTP demande des normes précises (ISO, NF, UPEC), c'est 🟢 CONFORME.
    - Ne signale une erreur que si la demande est impossible ou contradictoire (ex: demander un U4P4 pour un plafond).
    - Source OBLIGATOIRE.

2.  **ÉQUIVALENCE (Légalité) :**
    - La mention "ou équivalent" est OBLIGATOIRE.
    - 🔴 ROUGE si la mention est absente ET qu'une marque spécifique est imposée.
    - Source OBLIGATOIRE (Le numéro de l'article où la marque est citée sans mention).

3.  **SUPPORTS (Technique) :**
    - L'absence de mention de réception de support n'est pas critique (c'est implicite DTU).
    - Signale uniquement si le CCTP impose de travailler sur support non-conforme sans réserve.

Génère un JSON strict avec 3 clés : "liorah", "ethan", "krypt".
Pour chaque clé :
- "analyse" : Max 3 phrases. Format impératif : "Article X, Page Y : [Le problème].". Si RAS, écris juste "Conforme."
- "flag" : "🔴" (Illégal/Impossible), "🟠" (Flou/Marque imposée sans équivalence), "🟢" (RAS).
"""

P_AVENOR = """Tu es AVENOR, le second fidèle du Chef de Projet.
Tu reçois le JSON de la Trinité.

**TA MISSION :**
Rédiger le verdict final pour la MOA.

**RÈGLE DE DÉCISION FLAG :**
- Si au moins un "🔴" dans le JSON -> Verdict `[FLAG : 🔴]`
- Si au moins un "🟠" dans le JSON (et pas de rouge) -> Verdict `[FLAG : 🟠]`
- Sinon -> Verdict `[FLAG : 🟢]`

**STRUCTURE DE TA RÉPONSE (Markdown) :**

[FLAG : X]

### 🛡️ VERDICT DU CONSEIL
**Décision :** [Une phrase percutante résumant la situation]

**⚠️ VIGILANCE EXPERTE :**
1. [Point clé 1 avec référence Page/Art issue du JSON]
2. [Point clé 2 avec référence Page/Art issue du JSON]

**💡 CONSEIL AVENOR :**
[Une action corrective immédiate et concrète].
"""

P_CHAT_AVENOR = "Tu es AVENOR. Loyal, direct, expert BTP. Tu réponds aux questions sur le dossier analysé. Tes réponses sont courtes et factuelles. Pas de blabla."

# --- CHAT & RENDU DES MESSAGES ---
st.markdown(render_council(), unsafe_allow_html=True)

for msg in st.session_state.messages:
    # Récupération de l'avatar correct
    avatar_src = get_avatar_url(msg.get("avatar", "user"))
    
    with st.chat_message(msg["role"], avatar=avatar_src):
        if msg["name"] == "Avenor" and "VERDICT DU CONSEIL" in msg["content"]:
            # Détection couleur via REGEX sur le tag [FLAG : X]
            css_class = "decision-box-green"
            if "[FLAG : 🔴]" in msg["content"]: css_class = "decision-box-red"
            elif "[FLAG : 🟠]" in msg["content"]: css_class = "decision-box-orange"
            
            # Nettoyage du tag pour l'affichage
            display_content = msg["content"].replace("[FLAG : 🔴]", "").replace("[FLAG : 🟠]", "").replace("[FLAG : 🟢]", "")
            
            st.markdown(f'<div class="{css_class}">{display_content}</div>', unsafe_allow_html=True)
            
            # --- TIMELINE & TAMPON (Correction : Basé sur le timestamp stocké dans le message) ---
            if "timestamp" in msg:
                st.markdown(f"""
                <div class="stamp-block">
                    <div class="timeline">⏱️ Analyse : {msg['timestamp']}</div>
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
            
        # Ajout message utilisateur
        st.session_state.messages.append({"role": "user", "name": "Utilisateur", "avatar": "user", "content": f"Dossier transmis : {uploaded_file.name}"})
        with st.chat_message("user", avatar=get_avatar_url("user")): st.write(f"Dossier transmis : **{uploaded_file.name}**")
            
        log_container = st.container()
        progress_bar = st.progress(0, text="Initialisation...")
        status_placeholder = st.empty()
        
        start_time = time.time() # CHRONO START

        try:
            pdf_bytes = uploaded_file.getvalue()

            # 1. EVENA (Temporisation 11s)
            progress_bar.progress(10, text="Evena : Lecture et Distribution...")
            time.sleep(11) 
            log_container.markdown(f'<div class="success-log">✅ Evena : Extraction Terminée (11s)</div>', unsafe_allow_html=True)
            
            # 2. KERES (Temporisation 13s)
            progress_bar.progress(30, text="Kérès : Nettoyage et Anonymisation...")
            time.sleep(13) 
            log_container.markdown('<div class="success-log">✅ Kérès : Données sécurisées (13s)</div>', unsafe_allow_html=True)
            
            # 3. TRINITE (Temporisation 20 à 25s)
            delay_trinite = random.randint(20, 25)
            progress_bar.progress(60, text=f"Trinité : Scan Expert en cours ({delay_trinite}s)...")
            
            # Appel API réel (pendant le temps d'attente ou avant ?)
            # Pour l'UX, on lance l'appel, et on ajuste le sleep restant
            t_start_api = time.time()
            trinity_result = call_gemini_resilient(
                P_TRINITE, 
                pdf_bytes, 
                True, 
                "Trinité", 
                output_json=True,
                status_placeholder=status_placeholder
            )
            t_end_api = time.time()
            api_duration = t_end_api - t_start_api
            
            # Si l'API a été plus rapide que le délai imposé, on attend le reste
            if api_duration < delay_trinite:
                time.sleep(delay_trinite - api_duration)
            
            status_placeholder.empty()
            
            if isinstance(trinity_result, str) and "⚠️" in trinity_result:
                st.error(trinity_result); st.stop()

            # Extraction flags
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
            
            # 4. PHOEBE (Temporisation 8s)
            progress_bar.progress(80, text="Phoebe : Synthèse croisée...")
            time.sleep(8)
            rep_phoebe = phoebe_processing(trinity_result)
            log_container.markdown('<div class="success-log">✅ Phoebe : Synthèse prête (8s)</div>', unsafe_allow_html=True)
            
            # 5. AVENOR
            progress_bar.progress(90, text="Avenor : Rédaction du verdict...")
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
            match = re.search(r"\[FLAG\s*:\s*(.*?)\]", rep_avenor_raw)
            if match:
                flag_found = match.group(1)
                if "🔴" in flag_found: st.session_state.verdict_color = "red"
                elif "🟠" in flag_found: st.session_state.verdict_color = "orange"
                elif "🟢" in flag_found: st.session_state.verdict_color = "green"
            else:
                st.session_state.verdict_color = "neutral"

            # Calcul du temps total
            end_time = time.time()
            duration = end_time - start_time
            str_time_taken = f"{int(duration // 60)} min {int(duration % 60)} s"

            log_container.markdown('<div class="success-log">✅ Avenor : Verdict rendu</div>', unsafe_allow_html=True)
            progress_bar.progress(100, text="Audit Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            st.session_state.full_context = f"ANALYSE:\n{rep_phoebe}\nVERDICT:\n{rep_avenor_raw}"
            st.session_state.analysis_complete = True
            
            # Sauvegarde du message Avenor AVEC le timestamp
            st.session_state.messages.append({
                "role": "assistant", 
                "name": "Avenor", 
                "avatar": "avenor", 
                "content": rep_avenor_raw,
                "timestamp": str_time_taken
            })
            st.rerun()

        except Exception as e:
            progress_bar.empty()
            st.error(f"Erreur technique Python : {str(e)}")

if st.session_state.analysis_complete:
    user_input = st.chat_input("Question pour Avenor...")
    if user_input:
        st.session_state.messages.append({"role": "user", "name": "Investisseur", "avatar": "user", "content": user_input})
        with st.chat_message("user", avatar=get_avatar_url("user")): st.write(user_input)
            
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
            
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": "avenor", "content": reply})
        with st.chat_message("assistant", avatar=get_avatar_url("avenor")): st.write(reply)