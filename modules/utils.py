import PyPDF2
import docx
import json
import io
import streamlit as st
import re

@st.cache_data(show_spinner=False) # Cache le résultat pour éviter de re-extraire à chaque rerun
def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extrait le texte d'un fichier PDF fourni sous forme de bytes.

    Args:
        file_content: Le contenu binaire du fichier PDF.

    Returns:
        Le texte extrait du PDF, ou une chaîne vide en cas d'erreur.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text: # S'assurer que du texte a été extrait
                text += page_text + "\n\n" # Ajouter un saut de ligne entre les pages
        return text.strip()
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte PDF : {e}", icon="📄")
        return ""

@st.cache_data(show_spinner=False)
def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extrait le texte d'un fichier DOCX fourni sous forme de bytes.

    Args:
        file_content: Le contenu binaire du fichier DOCX.

    Returns:
        Le texte extrait du DOCX, ou une chaîne vide en cas d'erreur.
    """
    try:
        document = docx.Document(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in document.paragraphs])
        return text.strip()
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte DOCX : {e}", icon="📄")
        return ""

@st.cache_data(show_spinner=False)
def extract_text_from_txt(file_content: bytes, encoding='utf-8') -> str:
    """
    Extrait le texte d'un fichier TXT fourni sous forme de bytes.
    Tente de décoder en UTF-8, puis en latin-1 si l'UTF-8 échoue.

    Args:
        file_content: Le contenu binaire du fichier TXT.
        encoding: L'encodage initial à essayer (par défaut 'utf-8').

    Returns:
        Le texte extrait du TXT, ou une chaîne vide en cas d'erreur.
    """
    try:
        return file_content.decode(encoding).strip()
    except UnicodeDecodeError:
        st.warning(f"Impossible de décoder le fichier TXT en {encoding}, tentative avec 'latin-1'...", icon="⚠️")
        try:
            return file_content.decode('latin-1').strip()
        except Exception as e:
            st.error(f"Erreur lors de l'extraction du texte TXT (après tentative latin-1) : {e}", icon="📄")
            return ""
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte TXT : {e}", icon="📄")
        return ""

@st.cache_data(show_spinner=False)
def extract_text_from_json(file_content: bytes) -> str:
    """
    Extrait le texte d'un fichier JSON fourni sous forme de bytes.
    Convertit la structure JSON en une chaîne de caractères formatée.

    Args:
        file_content: Le contenu binaire du fichier JSON.

    Returns:
        Une représentation textuelle du JSON, ou une chaîne vide en cas d'erreur.
    """
    try:
        # D'abord, décoder les bytes en chaîne
        json_string = file_content.decode('utf-8')
        data = json.loads(json_string)
        text = json.dumps(data, indent=2, ensure_ascii=False)
        return text.strip()
    except json.JSONDecodeError as e:
        st.error(f"Erreur de décodage JSON : Le fichier n'est peut-être pas un JSON valide. {e}", icon="📄")
        st.info("Tentative de lecture du fichier JSON comme texte brut.", icon="ℹ️")
        return extract_text_from_txt(file_content)
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte JSON : {e}", icon="📄")
        return ""

def clean_text(text: str) -> str:
    """
    Nettoie le texte en supprimant les espaces blancs excessifs et les caractères spéciaux non désirés.
    (Peut être étendue selon les besoins).

    Args:
        text: Le texte brut à nettoyer.

    Returns:
        Le texte nettoyé.
    """
    if not isinstance(text, str):
        return ""
    # Remplace les multiples espaces/sauts de ligne par un seul espace
    text = re.sub(r'\s+', ' ', text)
    # Supprime les espaces en début et fin de chaîne
    text = text.strip()
    return text

def get_file_extension(filename: str) -> str | None:
    """
    Retourne l'extension d'un nom de fichier en minuscules.

    Args:
        filename: Le nom du fichier.

    Returns:
        L'extension du fichier (ex: 'pdf', 'docx') ou None si pas d'extension.
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None

# --- Fonctions de test ---

def _test_extraction():
    """ Fonction simple pour tester les extractions (à exécuter manuellement si besoin) """
    txt_content = b"Ceci est un fichier texte simple.\nAvec plusieurs lignes."
    json_content = b'{"nom": "Test", "valeur": 123, "liste": [1, 2, 3]}'
    malformed_json = b'{"nom": "Test", "valeur": 123, "liste": [1, 2, 3' # JSON invalide

    print("--- Test TXT ---")
    print(extract_text_from_txt(txt_content))
    print("\n--- Test JSON ---")
    print(extract_text_from_json(json_content))
    print("\n--- Test JSON Malformé ---")
    print(extract_text_from_json(malformed_json))
    print("\n--- Test Nettoyage ---")
    print(clean_text("  Ceci   est \n un   texte \t à nettoyer.  "))

