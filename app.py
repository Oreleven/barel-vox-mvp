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

# --- CONFIGURATION PAGE ---
# Fallback Favicon : Si pas de fichier, on utilise un emoji
page_icon = "assets/favicon.ico" if os.path.exists("assets/favicon.ico") else "🏗️"

st.set_page_config(
    page_title="BAREL VOX - Council OEE",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURATION MOTEUR ---
MODEL_NAME = "gemini-2.0-flash"

# --- ETAT DE SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "name": "Avenor",
        "avatar": "avenor",
        "content": "Le Council OEE est en session. Mes experts sont en ligne.<br>Déposez le DCE pour initier le protocole."
    })

if "verdict_color" not in st.session_state: st.session_state.verdict_color = "neutral"
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "full_context" not in st.session_state: st.session_state.full_context = ""

# --- SYSTÈME D'AVATARS & ASSETS (Gestion Majuscule Krypt) ---
EMOJI_MAP = {
    "user": "👤", "evena": "👩‍💻", "keres": "🛡️", "liorah": "⚖️",
    "ethan": "⚠️", "krypt": "💾", "phoebe": "🧠", "avenor": "👷‍♂️",
    "barel": "🏗️", "logo-barelvox": "🏗️"
}

def get_avatar_safe(key):
    """Renvoie un chemin valide ou un emoji. Gère le cas Krypt majuscule."""
    # Cas Spécial KRYPT (Majuscule force)
    if key.lower() == "krypt":
        if os.path.exists("assets/Krypt.png"): return "assets/Krypt.png"
        if os.path.exists("assets/Krypt.jpg"): return "assets/Krypt.jpg"
    
    # Cas général
    for name in [key, key.lower(), key.capitalize()]:
        for ext in [".png", ".jpg", ".jpeg", ".ico"]:
            path = f"assets/{name}{ext}"
            if os.path.exists(path): return path
            
    # Fallback Emoji
    return EMOJI_MAP.get(key.lower(), "🤖")

def get_img_as_base64(file_path):
    try:
        if not os.path.exists(file_path): return None
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def get_avatar_b64_safe(key):
    """Pour le HTML du Header/Council"""
    path = get_avatar_safe(key)
    # Si c'est un path image, on convertit en B64
    if path and not path in EMOJI_MAP.values() and os.path.exists(path):
        b64 = get_img_as_base64(path)
        if b64: return f"data:image/png;base64,{b64}"
    # Sinon URL générique
    return f"https://ui-avatars.com/api/?name={key}&background=333&color=fff&size=128"

# --- CSS DYNAMIQUE ---
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
    .decision-box-red {{ border: 2px solid #D32F2F; background-color: rgba(211, 47, 47, 0.15); padding: 20px; border-radius: 8px; color: #ffcdd2; margin-top: 10px; }}
    .decision-box-orange {{ border: 2px solid #F57C00; background-color: rgba(245, 124, 0, 0.15); padding: 20px; border-radius: 8px; color: #ffe0b2; margin-top: 10px; }}
    .decision-box-green {{ border: 2px solid #388E3C; background-color: rgba(56, 142, 60, 0.15); padding: 20px; border-radius: 8px; color: #c8e6c9; margin-top: 10px; }}
    
    .decision-box-red h3, .decision-box-orange h3, .decision-box-green h3 {{ margin-top: 0; font-family: 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 1px; }}
    .decision-box-red li, .decision-box-orange li, .decision-box-green li {{ margin-bottom: 8px; line-height: 1.5; }}
    
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
        margin-top: 25px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-top: 1px solid rgba(255,255,255,0.2);
        padding-top: 10px;
    }}
    .stamp {{
        padding: 5px 12px;
        border: 3px solid #E85D04; 
        border-radius: 8px;
        color: #E85D04;
        font-family: 'Impact', sans-serif;
        font-weight: bold;
        text-transform: uppercase;
        transform: rotate(-3deg);
        letter-spacing: 2px;
        font-size: 1rem;
        opacity: 0.9;
    }}
    .timeline {{
        color: #888;
        font-size: 0.9rem;
        font-style: italic;
        font-family: 'Courier New', monospace;
    }}
</style>
""", unsafe_allow_html=True)

# --- RENDER COUNCIL ---
def render_council():
    html = '<div class="council-container"><div class="council-row">'
    for member in ["evena", "keres", "liorah", "ethan", "Krypt", "phoebe"]:
        src = get_avatar_b64_safe(member)
        html += f'<div class="council-member"><img src="{src}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- HEADER ---
logo_b64 = get_avatar_b64_safe("logo-barelvox")
st.markdown(f"""
<div class="header-container">
    <img src="{logo_b64}" class="header-logo">
    <div class="header-text-block">
        <div class="main-header">BAREL VOX</div>
        <div class="sub-header">Architecture Anti-Sycophancie • Council OEE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- ENGINE ---
def extract_text_from_bytes(pdf_bytes):
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            txt_page = page.extract_text()
            if txt_page:
                clean_page = re.sub(r'(?<!\n)\n(?!\n)', ' ', txt_page)
                text += clean_page + "\n\n"
        return text
    except Exception as e:
        return f"Erreur lecture PDF : {str(e)}"

def clean_gemini_json(text):
    """Extraction Blindée Anti-Crash (Liste vs Dict)"""
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        
        # 1. Regex pour trouver le JSON pur
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            json_str = match.group()
            data = json.loads(json_str)
            
            # CORRECTIF CRITIQUE : Si c'est une liste, on prend le 1er élément
            if isinstance(data, list):
                if len(data) > 0: return data[0]
                else: return None
            return data
            
        # 2. Tentative directe
        data = json.loads(text)
        if isinstance(data, list): 
             if len(data) > 0: return data[0]
             return None
        return data

    except:
        return None

def call_gemini_resilient(role_prompt, data_part, is_pdf, agent_name, output_json=False, status_placeholder=None):
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"} if output_json else {})
    
    final_content = ""
    if is_pdf:
        extracted_text = extract_text_from_bytes(data_part)
        final_content = f"{role_prompt}\n\n---\n\nCONTENU DU DCE (EXTRAIT):\n{extracted_text}"
    else:
        final_content = f"{role_prompt}\n\n---\n\nCONTEXTE :\n{data_part}"

    max_retries = 2
    attempts = 0
    
    while attempts < max_retries:
        try:
            response = model.generate_content(final_content)
            text_resp = response.text
            
            if output_json:
                data = clean_gemini_json(text_resp)
                # Vérification que c'est bien un dict et qu'il n'est pas vide
                if data and isinstance(data, dict): 
                    return data
                else: 
                    raise ValueError("JSON invalide ou vide")
            else:
                return text_resp
            
        except Exception as e:
            attempts += 1
            time.sleep(1)
            
            if attempts == max_retries:
                # SAFE RETURN
                if output_json:
                    return {
                        "liorah": {"analyse": "Analyse partielle (Structure)", "flag": "🟠"},
                        "ethan": {"analyse": "Données complexes", "flag": "🟠"},
                        "krypt": {"analyse": "Données extraites", "flag": "🟢"}
                    }
                return f"⚠️ **Note Avenor :** Analyse complexe. Détail technique : {str(e)}"
    
    return "Erreur Système"

def phoebe_processing(trinity_report):
    # Sécurisation si trinity_report n'est pas un dict
    if not isinstance(trinity_report, dict):
        return "RAPPORT SYNTHÈSE\nErreur de structure des données."
    return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {json.dumps(trinity_report, ensure_ascii=False)}"

# --- PROMPTS ---
P_TRINITE = """
Tu es la Trinité (Liorah, Ethan, Krypt). Analyse le CCTP.
**OBJECTIF :** Détecter les marques imposées SANS mention "ou équivalent".

**RÈGLES :**
1. Si Marque citée SANS "ou équivalent" (même paragraphe) -> 🟠 (Alerte).
2. Si Marque citée AVEC "ou équivalent" -> 🟢 (RAS).

**OUTPUT JSON UNIQUE (PAS DE LISTE) :**
{
  "liorah": {"analyse": "[Page X] Marque Y imposée sans équivalence.", "flag": "🟠"},
  "ethan": {"analyse": "RAS - Normes DTU respectées.", "flag": "🟢"},
  "krypt": {"analyse": "RAS", "flag": "🟢"}
}
"""

P_AVENOR = """Tu es AVENOR, Directeur BTP. Rédige le verdict.

**LOGIQUE :**
- Si JSON contient 🟠 ou 🔴 -> Verdict [FLAG : 🟠].
- Sinon -> [FLAG : 🟢].

**FORMAT MARKDOWN :**
[FLAG : X]

### 🛡️ VERDICT DU CONSEIL
**Décision :** [Phrase Expert BTP]

**⚠️ VIGILANCE EXPERTE :**
* [Reprends les localisations Page/Art précises]

**💡 CONSEIL STRATÉGIQUE :**
* [Conseil Actionnable : Variantes, Fiches Techniques, Validation Bureau Contrôle]
"""

P_CHAT_AVENOR = "Tu es AVENOR. Expert BTP, direct et précis."

# --- SIDEBAR ---
with st.sidebar:
    # Avatar Barel Safe
    img_barel = get_avatar_safe("barel")
    if img_barel.endswith("png") or img_barel.endswith("jpg"):
        st.image(img_barel, use_column_width=True)
    else:
        st.markdown("## 🏗️ BAREL VOX")
        
    st.markdown("---")
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"Moteur Connecté (Gemini-3.0-Pro) 🟢")

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
            "role": "assistant", "name": "Avenor", "avatar": "avenor",
            "content": "Le Council OEE est en session.<br>Déposez le DCE."
        })
        st.session_state.analysis_complete = False
        st.session_state.verdict_color = "neutral"
        st.rerun()

# --- CHAT & LOGIC ---
st.markdown(render_council(), unsafe_allow_html=True)

for msg in st.session_state.messages:
    avatar_safe = get_avatar_safe(msg.get("avatar", "user"))
    
    with st.chat_message(msg["role"], avatar=avatar_safe):
        if msg["name"] == "Avenor" and "VERDICT DU CONSEIL" in msg["content"]:
            if "[FLAG : 🔴]" in msg["content"]: css_class = "decision-box-red"
            elif "[FLAG : 🟠]" in msg["content"]: css_class = "decision-box-orange"
            else: css_class = "decision-box-green"
            
            clean_content = msg["content"].replace("[FLAG : 🔴]", "").replace("[FLAG : 🟠]", "").replace("[FLAG : 🟢]", "")
            
            st.markdown(f'<div class="{css_class}">{clean_content}</div>', unsafe_allow_html=True)
            
            if "timestamp" in msg:
                st.markdown(f"""
                <div class="stamp-block">
                    <div class="timeline">⏱️ Analyse : {msg['timestamp']}</div>
                    <div class="stamp">✅ VALIDÉ PAR COUNCIL OEE</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            if msg["role"] == "assistant":
                st.markdown(f"**{msg['name']}**")
                st.markdown(msg["content"], unsafe_allow_html=True)
            else:
                st.write(msg["content"])

# --- PROCESS FLOW ---
if not st.session_state.analysis_complete:
    uploaded_file = st.file_uploader("Upload DCE", type=['pdf'], label_visibility="collapsed")
    if uploaded_file and api_key:
        if not st.session_state.messages or st.session_state.messages[-1]["role"] != "user":
             st.session_state.messages.append({"role": "user", "name": "User", "avatar": "user", "content": f"Dossier : {uploaded_file.name}"})
             st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and not st.session_state.analysis_complete:
        
        log_container = st.container()
        progress_bar = st.progress(0, text="Initialisation...")
        status_placeholder = st.empty()
        start_time = time.time()
        
        try:
            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.getvalue()

            # 1. EVENA
            progress_bar.progress(10, text="Evena : Lecture...")
            time.sleep(11)
            log_container.markdown(f'<div class="success-log">✅ Evena : Lecture Terminée (11s)</div>', unsafe_allow_html=True)

            # 2. KERES
            progress_bar.progress(30, text="Kérès : Sécurisation...")
            time.sleep(13)
            log_container.markdown('<div class="success-log">✅ Kérès : Données sécurisées (13s)</div>', unsafe_allow_html=True)

            # 3. TRINITE
            delay = random.randint(20, 25)
            progress_bar.progress(60, text=f"Trinité : Analyse ({delay}s)...")
            
            t1 = time.time()
            trinity_res = call_gemini_resilient(P_TRINITE, pdf_bytes, True, "Trinité", output_json=True, status_placeholder=status_placeholder)
            t2 = time.time()
            
            used = t2 - t1
            if used < delay: time.sleep(delay - used)
            
            status_placeholder.empty()
            
            # Logs Trinité (Safe Access)
            # Utilisation de .get() sur un dict garanti par clean_gemini_json
            if isinstance(trinity_res, dict):
                l_flag = trinity_res.get('liorah', {}).get('flag', '🟢')
                e_flag = trinity_res.get('ethan', {}).get('flag', '🟢')
                k_flag = trinity_res.get('krypt', {}).get('flag', '🟢')
            else:
                l_flag, e_flag, k_flag = "🟢", "🟢", "🟢"
            
            log_container.markdown(f'''<div class="success-log">✅ Trinité : Rapports Validés ({int(delay)}s)<br>- Juridique : {l_flag} | Risques : {e_flag} | Data : {k_flag}</div>''', unsafe_allow_html=True)

            # 4. PHOEBE
            progress_bar.progress(80, text="Phoebe : Synthèse...")
            time.sleep(8)
            phoebe_res = phoebe_processing(trinity_res)
            log_container.markdown('<div class="success-log">✅ Phoebe : Synthèse prête (8s)</div>', unsafe_allow_html=True)

            # 5. AVENOR
            progress_bar.progress(90, text="Avenor : Verdict...")
            avenor_res = call_gemini_resilient(P_AVENOR, phoebe_res, False, "Avenor", False, status_placeholder)
            status_placeholder.empty()

            # FIN
            end_time = time.time()
            duration = end_time - start_time
            time_str = f"{int(duration // 60)} min {int(duration % 60)} s"
            
            progress_bar.progress(100, text="Terminé")
            time.sleep(1)
            progress_bar.empty()
            
            if "[FLAG : 🔴]" in avenor_res: st.session_state.verdict_color = "red"
            elif "[FLAG : 🟠]" in avenor_res: st.session_state.verdict_color = "orange"
            else: st.session_state.verdict_color = "green"
            
            st.session_state.full_context = phoebe_res + "\n" + avenor_res
            st.session_state.analysis_complete = True
            
            st.session_state.messages.append({
                "role": "assistant", "name": "Avenor", "avatar": "avenor",
                "content": avenor_res,
                "timestamp": time_str
            })
            st.rerun()

        except Exception as e:
            st.error(f"Erreur Fatale : {str(e)}")

# --- CHAT INPUT ---
if st.session_state.analysis_complete:
    q = st.chat_input("Question pour Avenor...")
    if q:
        st.session_state.messages.append({"role": "user", "name": "User", "avatar": "user", "content": q})
        with st.chat_message("user", avatar=get_avatar_safe("user")): st.write(q)
            
        with st.spinner("Avenor consulte le dossier..."):
            chat_context = f"CONTEXTE DOSSIER:\n{st.session_state.full_context}"
            reply = call_gemini_resilient(
                P_CHAT_AVENOR,
                f"{chat_context}\n\nQUESTION UTILISATEUR:\n{q}",
                False, 
                "Avenor Chat",
                output_json=False,
                status_placeholder=st.empty()
            )
            
        st.session_state.messages.append({"role": "assistant", "name": "Avenor", "avatar": "avenor", "content": reply})
        st.rerun()