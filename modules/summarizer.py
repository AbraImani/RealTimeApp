import streamlit as st
from . import gemini_client
from . import config
from . import utils

# Limite de caractères pour l'aperçu du texte soumis à l'IA
MAX_CONTEXT_PREVIEW = 500

# @st.cache_data(show_spinner="Génération du résumé en cours...") # Mise en cache possible mais attention si le texte change
def generate_summary(text: str,
                     level: str = "Moyen",
                     keywords: str | None = None,
                     model_name: str = config.DEFAULT_TEXT_MODEL_NAME) -> str | None:
    """
    Génère un résumé du texte fourni en utilisant Gemini.

    Args:
        text (str): Le texte à résumer.
        level (str): Le niveau de détail souhaité ("Court", "Moyen", "Long").
        keywords (str | None): Mots-clés optionnels pour orienter le résumé.
        model_name (str): Le nom du modèle Gemini à utiliser.

    Returns:
        str: Le résumé généré, ou None en cas d'erreur.
    """
    if not text:
        st.warning("Le texte à résumer est vide.", icon="⚠️")
        return None

    # Vérifier si le client Gemini est prêt
    if not gemini_client.configure_gemini():
         st.error("Impossible de générer le résumé car le client Gemini n'est pas configuré.", icon="❌")
         return None


    # Construire le prompt pour Gemini
    prompt_parts = ["Voici un document :", "--- DEBUT DOCUMENT ---", text, "--- FIN DOCUMENT ---"]

    # Ajouter les instructions de résumé
    summary_instruction = config.SUMMARY_LEVELS.get(level, config.SUMMARY_LEVELS["Moyen"]) # Niveau par défaut si invalide
    prompt_parts.append(f"\nInstructions : Génère {summary_instruction} de ce document.")

    # Ajouter les mots-clés si fournis
    if keywords:
        prompt_parts.append(f"Le résumé doit se concentrer particulièrement sur les aspects liés à : '{keywords}'.")

    prompt_parts.append("\nFormat de sortie attendu : Uniquement le texte du résumé.")

    full_prompt = "\n".join(prompt_parts)

    # Afficher un aperçu du prompt (optionnel, pour le débogage)
    # with st.expander("Voir le prompt envoyé à l'IA"):
    #    st.text(full_prompt[:MAX_CONTEXT_PREVIEW] + "...") # Limiter la taille affichée

    # Appeler l'API Gemini via le client
    summary = gemini_client.generate_text(
        prompt=full_prompt,
        model_name=model_name,
        temperature=0.2, # Température plus basse pour des résumés factuels
        max_output_tokens=1024 # Ajuster si nécessaire pour les résumés longs
    )

    if summary:
        st.success("Résumé généré avec succès !", icon="📝")
        # Nettoyage simple (peut être amélioré)
        summary = summary.strip()
        # Supprimer les phrases introductives parfois ajoutées par l'IA
        phrases_a_supprimer = ["Voici un résumé", "Le résumé demandé est", "En résumé,"]
        for phrase in phrases_a_supprimer:
            if summary.lower().startswith(phrase.lower()):
                summary = summary[len(phrase):].strip().lstrip(':').strip()
        return summary
    else:
        # L'erreur est déjà loggée par gemini_client.generate_text
        st.error("La génération du résumé a échoué.", icon="❌")
        return None

def display_summarizer_options(text_available: bool):
    """
    Affiche les options de résumé dans l'interface Streamlit.

    Args:
        text_available (bool): Indique si du texte est disponible pour le résumé.

    Returns:
        tuple: (level, keywords, summarize_button_pressed)
               level (str): Niveau de résumé choisi.
               keywords (str): Mots-clés saisis.
               summarize_button_pressed (bool): True si le bouton "Générer Résumé" est cliqué.
    """
    st.subheader("2. Résumé Automatique")

    if not text_available:
        st.info("Chargez un document pour activer les options de résumé.", icon="📄")
        return None, None, False

    col1, col2 = st.columns([2, 3])

    with col1:
        summary_level = st.select_slider(
            "Longueur du résumé :",
            options=list(config.SUMMARY_LEVELS.keys()),
            value="Moyen", # Valeur par défaut
            key="summary_level_slider"
        )

    with col2:
        thematic_keywords = st.text_input(
            "Mots-clés pour résumé thématique (optionnel) :",
            placeholder="Ex: intelligence artificielle, éthique",
            key="summary_keywords"
        )

    summarize_button = st.button("Générer le Résumé", key="summarize_button", type="primary", use_container_width=True)

    return summary_level, thematic_keywords, summarize_button

# Exemple d'intégration dans app.py :
# if 'document_text' in st.session_state and st.session_state['document_text']:
#     level, keywords, button_pressed = display_summarizer_options(text_available=True)
#     if button_pressed:
#         summary = generate_summary(
#             st.session_state['document_text'],
#             level=level,
#             keywords=keywords
#         )
#         if summary:
#             st.session_state['current_summary'] = summary # Stocker pour affichage/export
#             st.markdown("### Résumé Généré")
#             st.markdown(summary)
#         else:
#             # Gérer l'échec
#             pass
# else:
#      display_summarizer_options(text_available=False)

# if 'current_summary' in st.session_state:
#      st.markdown("### Résumé Actuel")
#      st.markdown(st.session_state['current_summary'])
#      # Ajouter bouton export/TTS ici
