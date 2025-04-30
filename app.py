import streamlit as st
import datetime
# Importer les modules du projet
from modules import config
from modules import loader
from modules import utils
from modules import gemini_client
from modules import summarizer
from modules import chatbot
from modules import quiz
from modules import analyzer
from modules import exporter

# --- Configuration de la Page Streamlit ---
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide", # Utiliser toute la largeur
    initial_sidebar_state="expanded" # Garder la sidebar ouverte au début
)
gemini_client.configure_gemini()

# Initialiser les états de session nécessaires s'ils n'existent pas
if 'document_text' not in st.session_state:
    st.session_state['document_text'] = None
if 'document_name' not in st.session_state:
    st.session_state['document_name'] = None
if 'current_summary' not in st.session_state:
    st.session_state['current_summary'] = None
# Les états pour le chat et le quiz sont initialisés dans leurs modules respectifs

# --- CSS Personnalisé ---
# try:
#     with open("static/style.css") as f:
#         st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
# except FileNotFoundError:
#     pass # Ne rien faire si le fichier CSS n'existe pas

# --- Sidebar ---
with st.sidebar:
    st.image("https://www.gstatic.com/mobilesdk/160503_mobilesdk/logo/2x/firebase_28dp.png", width=50) # Exemple d'icône/logo
    st.title(config.APP_TITLE)
    st.caption("Prototypez rapidement avec l'IA Gemini")

    st.markdown("---")

    # --- Section 1 : Chargement du Document ---
    st.header("1. Chargement")
    uploaded_file = loader.display_file_uploader()

    # Si un nouveau fichier est chargé, extraire le texte et réinitialiser les états dépendants
    if uploaded_file is not None:
        # Vérifier si c'est un nouveau fichier ou le même fichier rechargé
        # (Streamlit recharge souvent, il faut une logique pour éviter les retraitements inutiles)
        # Une façon simple est de comparer le nom et la taille, mais pas infaillible.
        # On peut stocker l'ID du fichier uploadé si disponible.
        # Pour l'instant, on re-extrait si uploaded_file n'est pas None.
        new_doc_name = uploaded_file.name
        if new_doc_name != st.session_state.get('document_name', None):
            st.info("Nouveau document détecté. Extraction du texte...", icon="🔄")
            extracted_text = loader.extract_text_from_uploaded_file(uploaded_file)
            if extracted_text:
                st.session_state['document_text'] = extracted_text
                st.session_state['document_name'] = new_doc_name
                # Réinitialiser les éléments dérivés du texte précédent
                st.session_state['current_summary'] = None
                chatbot.clear_chat_history() # Effacer l'historique du chat lié au doc précédent
                quiz.reset_quiz_state() # Réinitialiser le quiz
                if 'analysis_results' in st.session_state: del st.session_state['analysis_results']
                st.success("Document traité. Vous pouvez utiliser les fonctionnalités.", icon="👍")
                # st.rerun() # Forcer un rerun pour que le reste de l'UI se mette à jour immédiatement
            else:
                # Si l'extraction échoue pour le nouveau fichier
                st.session_state['document_text'] = None
                st.session_state['document_name'] = None
                st.error("Échec de l'extraction du texte du nouveau document.", icon="❌")
        # else:
            # st.info("Le même document est toujours chargé.", icon="📄") # Optionnel

    # Afficher un aperçu du texte chargé (s'il existe)
    if st.session_state.get('document_text', None):
        with st.expander("Aperçu du Texte Extrait", expanded=False):
            st.text_area("Contenu", st.session_state['document_text'][:2000] + "...", height=150, key="text_preview_sidebar", disabled=True)
    else:
        st.info("Aucun document chargé ou texte extrait.")

    st.markdown("---")
    # Ajouter d'autres options globales dans la sidebar si besoin
    # st.selectbox("Modèle Gemini", config.AVAILABLE_MODELS) # Si on veut laisser choisir le modèle
    # st.slider("Température IA", 0.0, 1.0, 0.7) # Paramètres globaux IA


# --- Zone Principale (Contenu) ---
st.header(f"Document Actif : `{st.session_state.get('document_name', 'Aucun')}`")

# Utiliser des onglets pour organiser les fonctionnalités
tab_summary, tab_chat, tab_quiz, tab_analysis = st.tabs([
    "📝 Résumé",
    "💬 Chat Contextuel",
    "🧠 Quiz Génératif",
    "📊 Analyse & Insights"
])

# Variable pour vérifier si du texte est prêt à être utilisé
text_ready = bool(st.session_state.get('document_text', None))
doc_text = st.session_state.get('document_text', None)
doc_name = st.session_state.get('document_name', "document") # Nom par défaut pour l'export

# --- Onglet Résumé ---
with tab_summary:
    st.markdown("## Génération de Résumé")
    level, keywords, summarize_pressed = summarizer.display_summarizer_options(text_available=text_ready)

    if summarize_pressed and text_ready:
        summary = summarizer.generate_summary(
            text=doc_text,
            level=level,
            keywords=keywords
            # model_name=st.session_state.get('selected_model', config.DEFAULT_TEXT_MODEL_NAME) # Si modèle sélectionnable
        )
        if summary:
            st.session_state['current_summary'] = summary
            # Pas besoin de réafficher ici, l'affichage ci-dessous le fera
        else:
            st.error("La génération du résumé a échoué.")
            st.session_state['current_summary'] = None # Assurance de la réinitialisation

    # Afficher le résumé actuel s'il existe
    current_summary = st.session_state.get('current_summary', None)
    if current_summary:
        st.markdown("### Résumé Actuel")
        st.markdown(current_summary)
        # Options d'export pour le résumé
        exporter.display_export_options('summary', current_summary, doc_name)
        # Ajouter ici l'option TTS si implémentée
        # if st.button("🔊 Lire le résumé"):
        #     # Code pour Text-to-Speech
        #     pass
    elif text_ready and not summarize_pressed:
         st.info("Configurez les options ci-dessus et cliquez sur 'Générer le Résumé'.")


# --- Onglet Chat Contextuel ---
with tab_chat:
    st.markdown("## Conversation avec l'IA")
    chatbot.display_chat_interface(document_context=doc_text)
    # Option d'export de l'historique du chat ? (exporter.py)


# --- Onglet Quiz Génératif ---
with tab_quiz:
    st.markdown("## Génération de Quiz")
    num_q, q_type, q_diff, generate_pressed = quiz.display_quiz_options(text_available=text_ready)

    if generate_pressed and text_ready:
        questions = quiz.generate_quiz_questions(doc_text, num_q, q_type, q_diff)
        if questions:
            st.session_state[quiz.QUIZ_QUESTIONS_KEY] = questions
            # Ajouter le type à chaque question pour référence facile
            for q in st.session_state[quiz.QUIZ_QUESTIONS_KEY]:
                q['type'] = quiz.detect_quiz_type(q)
            st.session_state[quiz.QUIZ_GENERATED_KEY] = True
            st.session_state[quiz.QUIZ_CURRENT_QUESTION_KEY] = 0 # Démarrer à la première question
            st.rerun() # Recharger pour afficher l'interface du quiz
        else:
             st.error("La génération du quiz a échoué.")
             quiz.reset_quiz_state() # S'assurer que l'état est propre

    # Afficher l'interface du quiz (questions ou résultats)
    quiz.display_quiz_interface()

    # Ajouter les options d'export pour les résultats si le quiz est terminé
    if st.session_state.get(quiz.QUIZ_GENERATED_KEY, False) and \
       st.session_state.get(quiz.QUIZ_CURRENT_QUESTION_KEY, 0) >= len(st.session_state.get(quiz.QUIZ_QUESTIONS_KEY, [])):
        exporter.display_export_options('quiz_results', None, doc_name) # Les données sont récupérées depuis session_state


# --- Onglet Analyse & Insights ---
with tab_analysis:
    st.markdown("## Analyse du Document")
    analyzer.display_analysis_interface(text_available=text_ready, document_text=doc_text)

# --- Pied de page (Optionnel) ---
st.markdown("---")
st.caption(f"© {datetime.datetime.now().year} - {config.APP_TITLE} | Abraham Imani Bahati | Modèle IA : {config.DEFAULT_TEXT_MODEL_NAME}")

