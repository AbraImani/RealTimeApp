import streamlit as st
from . import gemini_client
from . import config
from . import utils

# Clé pour stocker l'historique dans st.session_state
CHAT_HISTORY_KEY = "gemini_chat_history"
# Clé pour stocker l'instance de chat si l'API le supporte
CHAT_SESSION_KEY = "gemini_chat_session"

# Limite de caractères du document à injecter dans le contexte du chat
# Augmentée, mais attention aux limites réelles du modèle utilisé !
# Les modèles comme Gemini 1.5 Pro ont des fenêtres de contexte beaucoup plus grandes,
# mais gemini-1.5-flash ou gemini-1.0-pro sont plus limités.
# Une valeur comme 15000 est un compromis. Pour des documents très volumineux,
# une approche RAG serait nécessaire.
MAX_CONTEXT_LENGTH = 15000

def initialize_chat():
    """Initialise l'historique du chat dans st.session_state si nécessaire."""
    if CHAT_HISTORY_KEY not in st.session_state:
        st.session_state[CHAT_HISTORY_KEY] = []

def display_chat_history():
    """Affiche l'historique de la conversation dans l'interface Streamlit."""
    if CHAT_HISTORY_KEY in st.session_state:
        for message in st.session_state[CHAT_HISTORY_KEY]:
            # Utiliser "assistant" pour le rôle du modèle pour correspondre à st.chat_message
            role = message["role"] if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(message["content"])

def add_message_to_history(role: str, content: str):
    """Ajoute un message à l'historique du chat."""
    if CHAT_HISTORY_KEY in st.session_state:
        # S'assurer que le rôle est 'user' ou 'model' pour la compatibilité API future
        api_role = "user" if role == "user" else "model"
        st.session_state[CHAT_HISTORY_KEY].append({"role": api_role, "content": content})

def clear_chat_history():
    """Efface l'historique du chat."""
    st.session_state[CHAT_HISTORY_KEY] = []
    st.success("Historique du chat effacé.", icon="🧹")

def get_chat_response(user_input: str,
                      document_context: str | None,
                      model_name: str = config.DEFAULT_TEXT_MODEL_NAME) -> str | None:
    """
    Obtient une réponse du chatbot Gemini en utilisant l'historique et le contexte.

    Args:
        user_input (str): La dernière question ou message de l'utilisateur.
        document_context (str | None): Le texte du document à utiliser comme contexte.
        model_name (str): Le nom du modèle Gemini à utiliser.

    Returns:
        str: La réponse générée par le modèle, ou None en cas d'erreur.
    """
    if not user_input:
        return None

    if not gemini_client.configure_gemini():
         st.error("Impossible d'obtenir une réponse car le client Gemini n'est pas configuré.", icon="❌")
         return None

    prompt_parts = []
    prompt_parts.append("Tu es un assistant IA expert dans l'analyse de documents. Réponds aux questions de l'utilisateur en te basant PRÉCISÉMENT et UNIQUEMENT sur le contexte du document fourni ci-dessous et l'historique de la conversation. Si l'information demandée n'est pas explicitement présente dans le document, indique que tu ne peux pas répondre avec les informations fournies. Ne spécule pas et ne cherche pas d'informations externes.")

    # Ajouter le contexte du document (s'il existe)
    if document_context:
        context_to_inject = document_context
        if len(document_context) > MAX_CONTEXT_LENGTH:
             # Tronquer le contexte et informer l'utilisateur plus clairement
             truncated_context = document_context[:MAX_CONTEXT_LENGTH]
             st.warning(
                 f"Le document est très long ({len(document_context)} caractères). "
                 f"Seuls les {MAX_CONTEXT_LENGTH} premiers caractères seront utilisés comme contexte pour cette conversation afin d'éviter les erreurs et de respecter les limites de l'IA. "
                 "Pour une analyse complète de documents très volumineux, des techniques plus avancées (non implémentées ici) seraient nécessaires.",
                 icon="⚠️"
             )
             context_to_inject = truncated_context
        else:
             # Optionnel : informer que tout le contexte est utilisé
             # st.info(f"Utilisation du contexte complet du document ({len(document_context)} caractères).", icon="ℹ️")
             pass

        prompt_parts.append("\n--- CONTEXTE DU DOCUMENT (Baser la réponse sur ce texte) ---")
        prompt_parts.append(context_to_inject)
        prompt_parts.append("--- FIN DU CONTEXTE DU DOCUMENT ---")

    else:
         prompt_parts.append("\n[INFO] Aucun document n'est chargé pour fournir un contexte.")


    # Ajouter l'historique de la conversation (format simple)
    prompt_parts.append("\n--- HISTORIQUE DE LA CONVERSATION ---")
    if CHAT_HISTORY_KEY in st.session_state and st.session_state[CHAT_HISTORY_KEY]:
        for msg in st.session_state[CHAT_HISTORY_KEY]:
            role_prefix = "Utilisateur" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role_prefix}: {msg['content']}")
    else:
        prompt_parts.append("(Début de la conversation)")
    prompt_parts.append("--- FIN DE L'HISTORIQUE ---")

    # Ajouter la dernière question de l'utilisateur
    prompt_parts.append(f"\nUtilisateur: {user_input}")
    # Indiquer à l'IA où commencer sa réponse et rappeler l'instruction clé
    prompt_parts.append("\nAssistant (Répondre en se basant **uniquement** sur le contexte fourni):")

    full_prompt = "\n".join(prompt_parts)

    # Appeler l'API Gemini
    response = gemini_client.generate_text(
        prompt=full_prompt,
        model_name=model_name,
        temperature=0.2, # Température modérée pour rester factuel mais fluide
        max_output_tokens=2500 # Augmenter un peu si nécessaire
    )

    if response:
        return response.strip()
    else:
        return None

def display_chat_interface(document_context: str | None):
    """
    Affiche l'interface complète du chat dans Streamlit.

    Args:
        document_context (str | None): Le texte du document chargé.
    """
    st.subheader("3. Chat Contextuel")

    initialize_chat()

    chat_enabled = bool(document_context)
    if not chat_enabled:
        st.info("Chargez un document pour démarrer une conversation contextuelle.", icon="📄")

    # Zone d'affichage de l'historique
    chat_container = st.container(height=400, border=True)
    with chat_container:
        display_chat_history()

    # Zone de saisie utilisateur
    user_input = st.chat_input(
        "Posez votre question sur le document...",
        key="chat_user_input",
        disabled=not chat_enabled # Désactiver si pas de contexte
    )

    if user_input and chat_enabled:
        # 1. Ajouter et afficher le message utilisateur
        # Utiliser "user" pour l'affichage st.chat_message
        add_message_to_history("user", user_input)
        with chat_container:
             with st.chat_message("user"):
                 st.markdown(user_input)

        # 2. Obtenir la réponse de l'IA
        with st.spinner("L'assistant réfléchit..."):
            ai_response = get_chat_response(user_input, document_context)

        # 3. Ajouter et afficher la réponse de l'IA
        if ai_response:
            # Utiliser "assistant" pour l'affichage st.chat_message
            add_message_to_history("assistant", ai_response)
            with chat_container:
                 with st.chat_message("assistant"):
                     st.markdown(ai_response)
        else:
            # Afficher un message d'erreur si la réponse a échoué
            error_message = "Désolé, une erreur s'est produite lors de la génération de la réponse. Vérifiez la configuration de l'API ou réessayez."
            add_message_to_history("assistant", error_message) # Ajouter l'erreur à l'historique aussi
            with chat_container:
                 with st.chat_message("assistant"):
                     st.error(error_message, icon="😕")

        # Forcer un rerun peut parfois aider à rafraîchir l'UI immédiatement
        # st.rerun()

    # Bouton pour effacer l'historique
    if st.button("Effacer l'historique du Chat", key="clear_chat_button"):
        clear_chat_history()
        st.rerun() # Forcer le rafraîchissement de l'interface
