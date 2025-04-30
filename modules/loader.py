import streamlit as st
from . import utils # Importation des fonctions utilitaires d'extraction
from . import config # Pour la taille max des fichiers

# Types de fichiers acceptés et leurs fonctions d'extraction associées
SUPPORTED_FILE_TYPES = {
    "pdf": utils.extract_text_from_pdf,
    "docx": utils.extract_text_from_docx,
    "txt": utils.extract_text_from_txt,
    "json": utils.extract_text_from_json,
}

# Extensions autorisées pour l'upload
ALLOWED_EXTENSIONS = list(SUPPORTED_FILE_TYPES.keys())

def display_file_uploader() -> st.runtime.uploaded_file_manager.UploadedFile | None:
    """
    Affiche le widget Streamlit pour l'upload de fichiers et retourne le fichier uploadé.
    Gère la validation de base (type, taille).

    Returns:
        UploadedFile: L'objet fichier uploadé par l'utilisateur, ou None si aucun fichier valide n'est uploadé.
    """
    uploaded_file = st.file_uploader(
        f"Chargez votre document ({', '.join(ALLOWED_EXTENSIONS).upper()})",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=False,  # à True si l'upload multiple est souhaité
        help=f"Formats supportés : {', '.join(ALLOWED_EXTENSIONS)}. Taille max : {config.MAX_FILE_SIZE_MB} MB."
    )

    if uploaded_file is not None:
        # Validation de la taille (Streamlit gère aussi maxUploadSize dans config.toml)
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            st.error(f"Le fichier est trop volumineux ({file_size_mb:.2f} MB). La taille maximale autorisée est {config.MAX_FILE_SIZE_MB} MB.", icon="🚨")
            return None # Retourne None si le fichier est trop gros

        # Afficher une information sur le fichier chargé
        st.info(f"Fichier chargé : `{uploaded_file.name}` ({uploaded_file.type}, {file_size_mb:.2f} MB)", icon="📁")
        return uploaded_file
    else:
        # st.info("Veuillez charger un document pour commencer.") # Message optionnel
        return None

def extract_text_from_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> str | None:
    """
    Extrait le texte du fichier uploadé en utilisant la fonction appropriée basée sur son extension.

    Args:
        uploaded_file: L'objet fichier retourné par st.file_uploader.

    Returns:
        str: Le texte extrait du fichier, ou None si l'extraction échoue ou si le type n'est pas supporté.
    """
    if uploaded_file is None:
        return None

    file_extension = utils.get_file_extension(uploaded_file.name)

    if file_extension in SUPPORTED_FILE_TYPES:
        # Lire le contenu du fichier en bytes
        file_content = uploaded_file.getvalue()

        # Afficher une barre de progression pendant l'extraction (peut être rapide)
        with st.spinner(f"Extraction du texte du fichier {file_extension.upper()}..."):
            extraction_function = SUPPORTED_FILE_TYPES[file_extension]
            try:
                extracted_text = extraction_function(file_content)
                if extracted_text:
                    st.success(f"Texte extrait avec succès du fichier {uploaded_file.name}.", icon="✅")
                    # Nettoyage optionnel du texte extrait
                    # cleaned_text = utils.clean_text(extracted_text)
                    # return cleaned_text
                    return extracted_text
                else:
                    # L'erreur spécifique est déjà affichée par la fonction d'extraction
                    st.error(f"Impossible d'extraire le texte du fichier {uploaded_file.name}. Le fichier est peut-être vide, corrompu ou non supporté correctement.", icon="❌")
                    return None
            except Exception as e:
                st.error(f"Une erreur inattendue est survenue lors de l'extraction : {e}", icon="🔥")
                return None
    else:
        st.error(f"Type de fichier non supporté : '{file_extension}'. Formats acceptés : {', '.join(ALLOWED_EXTENSIONS)}", icon="🚫")
        return None

# Exemple d'utilisation est dans app.py
# def main_loader_logic():
#     uploaded_file = display_file_uploader()
#     if uploaded_file:
#         extracted_text = extract_text_from_uploaded_file(uploaded_file)
#         if extracted_text:
#             st.subheader("Texte Extrait (Aperçu)")
#             st.text_area("Contenu", extracted_text[:2000] + "...", height=200, key="extracted_text_preview")
#             # Stocker le texte extrait dans st.session_state pour l'utiliser ailleurs
#             st.session_state['document_text'] = extracted_text
#             st.session_state['document_name'] = uploaded_file.name
#         else:
#             # Gérer le cas où l'extraction a échoué mais le fichier a été uploadé
#             if 'document_text' in st.session_state:
#                 del st.session_state['document_text'] # Nettoyer l'état précédent
#             if 'document_name' in st.session_state:
#                 del st.session_state['document_name']

