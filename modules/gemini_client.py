import google.generativeai as genai
import streamlit as st
from PIL import Image # Pour le traitement d'images si multimodal
import io
from . import config

_gemini_client_initialized = False
_generative_model = None
_vision_model = None

def configure_gemini():
    """
    Configure l'API Google Gemini avec la clé API.
    Doit être appelée une fois au début.
    """
    global _gemini_client_initialized
    if not _gemini_client_initialized:
        try:
            if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "NO_KEY_CONFIGURED":
                 # L'erreur est déjà gérée dans config.py ou app.py, on ne bloque pas ici
                 # mais les fonctions suivantes échoueront probablement.
                 st.warning("Clé API Gemini non disponible. Les fonctionnalités IA sont désactivées.", icon="⚠️")
                 return False # Indique que la configuration a échoué

            genai.configure(api_key=config.GEMINI_API_KEY)
            _gemini_client_initialized = True
            st.success("Client Gemini configuré avec succès.", icon="✅")
            return True
        except Exception as e:
            st.error(f"Erreur lors de la configuration de l'API Gemini : {e}", icon="🔥")
            _gemini_client_initialized = False
            return False
    return True # Déjà initialisé

def get_generative_model(model_name: str = config.DEFAULT_TEXT_MODEL_NAME):
    """
    Récupère une instance initialisée du modèle génératif Gemini spécifié.
    Configure le client si ce n'est pas déjà fait.

    Args:
        model_name (str): Le nom du modèle à utiliser (par défaut depuis config).

    Returns:
        genai.GenerativeModel: Une instance du modèle, ou None si erreur/non configuré.
    """
    global _generative_model
    if not _gemini_client_initialized:
        if not configure_gemini():
            return None # La configuration a échoué

    # Initialiser le modèle spécifique si pas déjà fait ou si le nom change
    # Note: Pourrait être simplifié si on utilise toujours le même modèle texte
    try:
        # Pour l'instant, on réutilise la même instance si le nom est le même
        # Si on voulait changer de modèle dynamiquement, il faudrait gérer ça
        if _generative_model is None or _generative_model.model_name != f"models/{model_name}":
             _generative_model = genai.GenerativeModel(model_name)
        return _generative_model
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation du modèle Gemini '{model_name}': {e}", icon="🤖")
        return None

# --- Fonctions d'interaction avec l'API ---

@st.cache_data(show_spinner="Génération de la réponse par l'IA...") # Cache la réponse pour les mêmes inputs
def generate_text(prompt: str,
                  model_name: str = config.DEFAULT_TEXT_MODEL_NAME,
                  temperature: float = 0.7,
                  max_output_tokens: int = 1024) -> str | None:
    """
    Génère du texte en utilisant le modèle Gemini spécifié.

    Args:
        prompt (str): Le prompt à envoyer au modèle.
        model_name (str): Le nom du modèle à utiliser.
        temperature (float): Contrôle l'aléatoire de la sortie (0.0 - 1.0).
        max_output_tokens (int): Nombre maximum de tokens à générer.

    Returns:
        str: Le texte généré par le modèle, ou None en cas d'erreur.
    """
    model = get_generative_model(model_name)
    if not model:
        st.error("Le modèle génératif Gemini n'est pas disponible.", icon="❌")
        return None

    try:
        # Configuration de la génération
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens
            # top_p=0.9, # Autres paramètres possibles
            # top_k=40
        )

        # Appel à l'API Gemini
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            # safety_settings=... # Configuration de sécurité si nécessaire
            )

        # Vérifier si la réponse contient du texte
        if response and response.candidates and response.candidates[0].content.parts:
             # Accéder correctement au texte généré
             # La structure peut varier légèrement selon la version de l'API et le type de réponse
            generated_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
            if generated_text:
                return generated_text.strip()
            else:
                 # Gérer le cas où la réponse est bloquée ou vide
                 block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Inconnue"
                 safety_ratings = response.prompt_feedback.safety_ratings if response.prompt_feedback else "N/A"
                 st.warning(f"La réponse de Gemini était vide ou bloquée. Raison: {block_reason}. Safety Ratings: {safety_ratings}", icon="⚠️")
                 return None

        else:
            # Gérer le cas d'une réponse inattendue ou vide
            st.warning(f"Réponse inattendue ou vide reçue de Gemini: {response}", icon="🤔")
            return None

    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API Gemini : {e}", icon="🔥")
        # Afficher des détails supplémentaires si disponibles (ex: erreur API spécifique)
        # if hasattr(e, 'response'): st.error(f"Détails de l'erreur API: {e.response.text}")
        return None

# --- Fonction multimodale ---

# @st.cache_data(show_spinner="Analyse de l'image par l'IA...")
# def analyze_image(prompt: str, image_bytes: bytes, model_name: str = config.DEFAULT_VISION_MODEL_NAME) -> str | None:
#     """
#     Analyse une image avec un prompt texte en utilisant un modèle de vision Gemini.

#     Args:
#         prompt (str): La question ou l'instruction concernant l'image.
#         image_bytes (bytes): Le contenu binaire de l'image.
#         model_name (str): Le nom du modèle de vision à utiliser.

#     Returns:
#         str: La réponse textuelle de l'analyse, ou None en cas d'erreur.
#     """
#     global _vision_model
#     if not _gemini_client_initialized:
#         if not configure_gemini():
#             return None

#     try:
#         # Initialiser le modèle vision si nécessaire
#         if _vision_model is None or _vision_model.model_name != f"models/{model_name}":
#              _vision_model = genai.GenerativeModel(model_name)

#         # Préparer l'image pour l'API
#         img = Image.open(io.BytesIO(image_bytes))

#         # Appel à l'API multimodale
#         response = _vision_model.generate_content([prompt, img])

#         if response and response.candidates and response.candidates[0].content.parts:
#             generated_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
#             return generated_text.strip() if generated_text else None
#         else:
#             st.warning(f"Réponse inattendue ou vide reçue du modèle de vision Gemini: {response}", icon="🤔")
#             return None

#     except Exception as e:
#         st.error(f"Erreur lors de l'analyse de l'image avec Gemini : {e}", icon="🔥")
#         return None

# --- Fonctions de Chat (si l'API supporte un mode conversationnel direct) ---

def start_chat_session(model_name: str = config.DEFAULT_TEXT_MODEL_NAME, history: list = None):
    """
    Démarre une session de chat avec le modèle Gemini.

    Args:
        model_name (str): Le nom du modèle à utiliser.
        history (list): Un historique optionnel de messages précédents.
                        Format attendu par l'API Gemini (ex: [{'role': 'user', 'parts': ['message']}, {'role': 'model', 'parts': ['response']}])

    Returns:
        genai.ChatSession: Une instance de session de chat, ou None si erreur.
    """
    model = get_generative_model(model_name)
    if not model:
        st.error("Le modèle génératif Gemini n'est pas disponible pour le chat.", icon="❌")
        return None

    try:
        # S'assurer que l'historique est dans le bon format si fourni
        formatted_history = []
        if history:
            for msg in history:
                # Vérifier et adapter le format si nécessaire
                # Ceci est un exemple, la structure exacte peut varier
                if isinstance(msg, dict) and 'role' in msg and 'parts' in msg:
                     # Assurez-vous que 'parts' est une liste de strings ou d'objets Part valides
                     parts_content = msg['parts']
                     if isinstance(parts_content, str):
                         formatted_history.append({'role': msg['role'], 'parts': [parts_content]})
                     elif isinstance(parts_content, list):
                          # Vérifier que les éléments de la liste sont des strings ou des objets Part
                          # Pour simplifier, on suppose ici qu'ils sont des strings
                          if all(isinstance(p, str) for p in parts_content):
                              formatted_history.append({'role': msg['role'], 'parts': parts_content})
                          else:
                              st.warning(f"Format de message invalide dans l'historique: {msg}", icon="⚠️")
                              # Ignorer ce message ou tenter de le corriger
                     else:
                         st.warning(f"Format de 'parts' invalide dans l'historique: {msg}", icon="⚠️")

                else:
                     st.warning(f"Format de message invalide dans l'historique: {msg}", icon="⚠️")


        chat = model.start_chat(history=formatted_history if formatted_history else None)
        return chat
    except Exception as e:
        st.error(f"Erreur lors du démarrage de la session de chat Gemini : {e}", icon="🔥")
        return None