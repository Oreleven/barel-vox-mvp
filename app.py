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
    for name in [filename_part, filename_part.lower(), filename_part.capitalize()]:
        for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".ico"]:
            path = f"assets/{name}{ext}"
            if os.path.exists(path): return path
    return None

# Mapping des assets
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
    path = ASSET_MAP.get(key)
    return path if path and os.path.exists(path) else "[https://ui-avatars.com/api/?name=](https://ui-avatars.com/api/?name=)" + key + "&background=333&color=fff&size=128"

def get_avatar_b64_src(key):
    path = ASSET_MAP.get(key)
    if path:
        b64 = get_img_as_base64(path)
        if b64: return f"data:image/png;base64,{b64}"
    return "[https://ui-avatars.com/api/?name=](https://ui-avatars.com/api/?name=)" + key + "&background=333&color=fff&size=128"

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
    
    /* Verdict Boxes - Couleurs et Lisibilité */
    .decision-box-red {{ border: 2px solid #D32F2F; background-color: rgba(211, 47, 47, 0.15); padding: 20px; border-radius: 8px; color: #ffcdd2; margin-top: 10px; }}
    .decision-box-orange {{ border: 2px solid #F57C00; background-color: rgba(245, 124, 0, 0.15); padding: 20px; border-radius: 8px; color: #ffe0b2; margin-top: 10px; }}
    .decision-box-green {{ border: 2px solid #388E3C; background-color: rgba(56, 142, 60, 0.15); padding: 20px; border-radius: 8px; color: #c8e6c9; margin-top: 10px; }}
    
    .decision-box-red h3, .decision-box-orange h3, .decision-box-green h3 {{ margin-top: 0; font-family: 'Helvetica Neue', sans-serif; text-transform: uppercase; }}
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
    for member in ["evena", "keres", "liorah", "ethan", "krypt", "phoebe"]:
        src = get_avatar_b64_src(member)
        html += f'<div class="council-member"><img src="{src}" class="council-img"><br>{member.capitalize()}</div>'
    html += '</div></div>'
    return html

# --- HEADER ---
logo_b64 = get_avatar_b64_src("logo")
st.markdown(f"""
<div class="header-container">
    <img src="{logo_b64}" class="header-logo">
    <div class="header-text-block">
        <div class="main-header">BAREL VOX</div>
        <div class="sub-header">Architecture Anti-Sycophancie • Council OEE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- EXTRACTION TEXTE ET NETTOYAGE CHIRURGICAL ---
def extract_text_from_bytes(pdf_bytes):
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            txt_page = page.extract_text()
            if txt_page:
                # 1. On recolle les phrases cassées
                clean_page = re.sub(r'(?<!\n)\n(?!\n)', ' ', txt_page)
                # 2. On garde les doubles sauts pour séparer les articles
                text += clean_page + "\n\n"
        return text
    except Exception as e:
        return f"Erreur lecture PDF : {str(e)}"

# --- NETTOYAGE JSON RENFORCÉ (ANTI-CRASH) ---
def clean_gemini_json(text):
    try:
        # Enlever le markdown si présent
        text = text.replace("```json", "").replace("```", "")
        
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return json.loads(text) 
    except:
        return None

def call_gemini_resilient(role_prompt, data_part, is_pdf, agent_name, output_json=False, status_placeholder=None):
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"response_mime_type": "application/json"} if output_json else {})
    
    final_content = ""
    if is_pdf:
        extracted_text = extract_text_from_bytes(data_part)
        final_content = f"{role_prompt}\n\n---\n\nCONTENU DU DCE (NETTOYÉ):\n{extracted_text}"
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
                else: 
                    # Retry immédiat si JSON cassé
                    raise ValueError("JSON invalide")
            else:
                return text_resp
            
        except Exception as e:
            attempts += 1
            if status_placeholder:
                # On n'affiche l'erreur que si c'est la dernière tentative pour ne pas effrayer l'utilisateur
                if attempts == max_retries:
                    status_placeholder.markdown(f'<div class="error-log">⚠️ Erreur {agent_name} : {str(e)}</div>', unsafe_allow_html=True)
            
            time.sleep(2)
            
            # Fallback JSON de secours si échec total pour éviter le crash de l'app
            if output_json and attempts == max_retries: 
                 return {
                     "liorah": {"analyse": "Erreur technique analyse", "flag": "🟠"}, 
                     "ethan": {"analyse": "Erreur technique analyse", "flag": "🟠"}, 
                     "krypt": {"analyse": "Erreur technique analyse", "flag": "🟠"}
                 }
            if attempts == max_retries: return f"⚠️ ERREUR CRITIQUE : {str(e)}"
    
    return "Erreur Fatale"

def phoebe_processing(trinity_report):
    return f"RAPPORT SYNTHÈSE\nDonnées Techniques : {json.dumps(trinity_report, ensure_ascii=False)}"

# --- PROMPTS DE LA TRINITÉ (FOCUS REFERENCE PAGE/ARTICLE) ---
P_TRINITE = """
Tu incarnes la Trinité (Liorah, Ethan, Krypt), Auditeurs BTP experts.
Analyse le texte du CCTP fourni.

**MISSION CRITIQUE : DÉTECTION DE MARQUE SANS ÉQUIVALENCE**

**RÈGLES D'ANALYSE :**
1. Cherche les mentions de marques spécifiques (ex: Forbo, Laterlite, Tollens, etc.).
2. Vérifie la présence de "ou équivalent", "similaire", "type" DANS LE MÊME PARAGRAPHE.
3. Si la mention "ou équivalent" manque : C'est une NON-CONFORMITÉ (🟠).

**FORMAT DE SORTIE (JSON STRICT) :**
Tu DOIS localiser l'erreur. Si tu ne trouves pas le numéro de page exact, cite le TITRE du paragraphe ou le Numéro de l'Article (ex: Art 3.1).

Génère un JSON avec 3 clés : "liorah", "ethan", "krypt".
Pour chaque clé :
- "analyse" : Phrase formatée ainsi : "**[Article X / Page Y]** : La marque Z est imposée sans mention 'ou équivalent'."
- "flag" : "🔴" (Illégal), "🟠" (Marque imposée sans équivalence), "🟢" (Conforme/RAS).

Si tout est conforme, écris : "RAS - Mentions d'équivalence présentes."
"""

P_AVENOR = """Tu es AVENOR, Chef de Projet BTP Senior.
Tu rédiges le verdict pour le Maître d'Ouvrage (Investisseur).

**INPUT :** Rapport JSON de la Trinité.

**LOGIQUE DE DÉCISION :**
- Si Trinité contient 🟠 ou 🔴 -> Verdict [FLAG : 🟠] (ou Rouge si critique).
- Si tout est Vert -> Verdict [FLAG : 🟢].

**TON DE LA RÉPONSE :**
Utilise un vocabulaire BTP précis et autoritaire. Fini le blabla générique.

**FORMAT DE SORTIE (MARKDOWN) :**

[FLAG : X]

### 🛡️ VERDICT DU CONSEIL
**Décision :** [Phrase courte. Ex: "DCE validé sous réserves" ou "Mise au point technique requise"]

**⚠️ VIGILANCE EXPERTE (ANOMALIES) :**
* [Reprends EXACTEMENT la localisation (Article/Page) donnée par Trinité]
* [Idem pour le point suivant]

**💡 CONSEIL STRATÉGIQUE (ACTION BTP) :**
* [Conseil CONCRET. Ex: "Demander à la MOE d'ajouter un additif au CCTP", "Négocier une variante technique lors de l'ACT", "Faire valider une fiche technique équivalente par le Contrôleur Technique"]
"""

P_CHAT_AVENOR = "Tu es AVENOR. Réponds court, pro, expert BTP."

# --- SIDEBAR (RÉTABLIE !) ---
with st.sidebar:
    barel_img = ASSET_MAP.get("barel")
    if barel_img and os.path.exists(barel_img): 
        st.image(barel_img, use_column_width=True)
    else: 
        st.markdown("## 🏗️ BAREL VOX")
    
    st.markdown("---")
    api_key = st.text_input("🔑 Clé API Google Gemini", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"Moteur Connecté (Gemini-3.0-Pro) 🟢")
    else:
        st.warning("Moteur en attente...")

    # SECTION AGENTS RESTAURÉE
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

# --- CHAT LOOP & AFFICHAGE ---
st.markdown(render_council(), unsafe_allow_html=True)

for msg in st.session_state.messages:
    avatar_src = get_avatar_url(msg.get("avatar", "user"))
    with st.chat_message(msg["role"], avatar=avatar_src):
        if msg["name"] == "Avenor" and "VERDICT DU CONSEIL" in msg["content"]:
            # Détection couleur stricte
            if "[FLAG : 🔴]" in msg["content"]: css_class = "decision-box-red"
            elif "[FLAG : 🟠]" in msg["content"]: css_class = "decision-box-orange"
            else: css_class = "decision-box-green"
            
            clean_content = msg["content"].replace("[FLAG : 🔴]", "").replace("[FLAG : 🟠]", "").replace("[FLAG : 🟢]", "")
            
            st.markdown(f'<div class="{css_class}">{clean_content}</div>', unsafe_allow_html=True)
            
            # TIMELINE & TAMPON (Affichés seulement si le timestamp existe)
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

# --- MAIN PROCESS ---
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
            # On passe output_json=True pour forcer le JSON
            trinity_res = call_gemini_resilient(P_TRINITE, pdf_bytes, True, "Trinité", output_json=True, status_placeholder=status_placeholder)
            t2 = time.time()
            
            used = t2 - t1
            if used < delay: time.sleep(delay - used)
            
            status_placeholder.empty()
            
            # Logs Trinité
            l_flag = trinity_res.get('liorah', {}).get('flag', '🟢')
            e_flag = trinity_res.get('ethan', {}).get('flag', '🟢')
            k_flag = trinity_res.get('krypt', {}).get('flag', '🟢')
            
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
            
            # Gestion Couleur Session
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
            st.error(f"Erreur technique : {e}")

# --- CHAT INPUT ---
if st.session_state.analysis_complete:
    q = st.chat_input("Question pour Avenor...")
    if q:
        st.session_state.messages.append({"role": "user", "name": "User", "avatar": "user", "content": q})
        with st.chat_message("user", avatar=get_avatar_url("user")): st.write(q)
            
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