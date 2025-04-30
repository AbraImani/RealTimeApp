import os
import streamlit as st
from dotenv import load_dotenv 

load_dotenv() 
GEMINI_API_KEY = st.secrets.get("gemini_api_key", os.getenv("GOOGLE_API_KEY"))

if not GEMINI_API_KEY:
    st.error("Clé API Gemini non configurée. Veuillez la définir dans les secrets Streamlit (`secrets.toml`) ou comme variable d'environnement `GOOGLE_API_KEY`.", icon="🚨")
    st.stop()

DEFAULT_TEXT_MODEL_NAME = "gemini-1.5-flash"
DEFAULT_VISION_MODEL_NAME = "gemini-2.0-flash-experimental" # Nom incorrect, devrait être un modèle vision comme gemini-1.5-pro ou flash
APP_TITLE = "RealTime AI Prototyper"
PAGE_ICON = "🚀" 

# --- Constantes pour les fonctionnalités ---
SUMMARY_LEVELS = {
    "Court": "un résumé très bref (1-2 phrases)",
    "Moyen": "un résumé concis (environ 5 phrases)",
    "Long": "un résumé détaillé (plusieurs paragraphes)"
}

QUIZ_TYPES = {
    "QCM": "Questions à Choix Multiples",
    "Vrai/Faux": "Questions Vrai ou Faux",
    "Ouvertes": "Questions à Réponse Ouverte"
}

QUIZ_DIFFICULTY = {
    "Facile": "niveau débutant",
    "Moyen": "niveau intermédiaire",
    "Difficile": "niveau expert"
}

# --- Configuration Base de données ---
DATABASE_NAME = "ai_prototyper_data.db"

MAX_FILE_SIZE_MB = 100 
AVAILABLE_MODELS = [DEFAULT_TEXT_MODEL_NAME, "gemini-1.0-pro", "gemini-1.5-pro-latest"]

print(f"Configuration chargée. Modèle texte par défaut : {DEFAULT_TEXT_MODEL_NAME}")
