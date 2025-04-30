import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io
from collections import Counter
import re

# Importer le client Gemini si l'extraction de mots-clés se fait via l'IA
from . import gemini_client
from . import config
from . import utils

# Mots vides supplémentaires courants en français (à compléter)
FRENCH_STOPWORDS = set(STOPWORDS) | {
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'à', 'et', 'est', 'il', 'elle',
    'on', 'nous', 'vous', 'ils', 'elles', 'ce', 'cet', 'cette', 'ces', 'mon', 'ma',
    'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'nos', 'votre', 'vos',
    'leur', 'leurs', 'qui', 'que', 'quoi', 'dont', 'où', 'quand', 'comment', 'pourquoi',
    'avec', 'sans', 'pour', 'par', 'sur', 'sous', 'dans', 'hors', 'vers', 'depuis',
    'pendant', 'comme', 'si', 'ou', 'mais', 'donc', 'car', 'ni', 'plus', 'moins',
    'très', 'aussi', 'alors', 'afin', 'ainsi', 'après', 'avant', 'bien', 'chaque',
    'chez', 'contre', 'déjà', 'depuis', 'encore', 'enfin', 'entre', 'jamais',
    'jusque', 'même', 'parce', 'peut', 'peu', 'presque', 'puis', 'quel', 'quelle',
    'quels', 'quelles', 'sans', 'seulement', 'sont', 'sous', 'souvent', 'suivant',
    'tandis', 'tant', 'tel', 'telle', 'tels', 'telles', 'toujours', 'tout', 'toute',
    'toutes', 'tous', 'trop', 'très', 'vers', 'voici', 'voilà', 'être', 'avoir', 'faire',
    'dire', 'pouvoir', 'aller', 'voir', 'vouloir', 'venir', 'falloir', 'devoir', 'savoir',
    'mettre', 'prendre', 'trouver', 'donner', 'parler', 'aimer', 'passer', 'penser',
    'regarder', 'utiliser', 'document', 'texte', 'fichier', 'contenu', 'page', 'section',
    'article', 'chapitre', 'selon', 'suite', 'figure', 'tableau', 'exemple', 'partie',
    'cas', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
}


# @st.cache_data(show_spinner="Extraction des mots-clés par l'IA...")
def extract_keywords_with_gemini(text: str,
                                 num_keywords: int = 10,
                                 model_name: str = config.DEFAULT_TEXT_MODEL_NAME) -> list[str] | None:
    """
    Extrait les mots-clés principaux d'un texte en utilisant Gemini.

    Args:
        text (str): Le texte à analyser.
        num_keywords (int): Le nombre de mots-clés souhaité.
        model_name (str): Le nom du modèle Gemini à utiliser.

    Returns:
        list[str]: Une liste des mots-clés extraits, ou None si erreur.
    """
    if not text:
        st.warning("Le texte pour l'extraction de mots-clés est vide.", icon="⚠️")
        return None

    # Vérifier si le client Gemini est prêt
    if not gemini_client.configure_gemini():
         st.error("Impossible d'extraire les mots-clés car le client Gemini n'est pas configuré.", icon="❌")
         return None

    # Construire le prompt
    prompt = f"""
    Analyse le document suivant et identifie les {num_keywords} mots-clés ou expressions clés les plus importants et représentatifs de son contenu principal.
    Ignore les mots courants et concentre-toi sur les termes spécifiques et significatifs.

    --- DEBUT DOCUMENT ---
    {text[:8000]}
    --- FIN DOCUMENT ---

    Instructions de formatage :
    Réponds **UNIQUEMENT** avec une liste de mots-clés séparés par des virgules. N'ajoute AUCUN autre texte, en-tête ou numérotation.

    Exemple de sortie attendue :
    mot-clé 1, expression clé 2, terme spécifique 3, concept 4, ...

    Liste des mots-clés :
    """ # L'IA devrait continuer après "Liste des mots-clés :"

    # Appeler l'API Gemini
    response = gemini_client.generate_text(
        prompt=prompt,
        model_name=model_name,
        temperature=0.3, # Plus factuel pour l'extraction
        max_output_tokens=256 # Suffisant pour une liste de mots-clés
    )

    if response:
        # Nettoyer la réponse : supprimer les en-têtes potentiels et séparer par virgule
        response = response.strip()
        # Supprimer une éventuelle ligne d'en-tête restante
        if response.lower().startswith("liste des mots-clés"):
            response = response.split(":", 1)[-1].strip()
        elif response.lower().startswith("voici les mots-clés"):
             response = response.split(":", 1)[-1].strip()

        # Séparer par virgule et nettoyer chaque mot-clé
        keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
        if keywords:
            st.success(f"{len(keywords)} mots-clés extraits par l'IA.", icon="🔑")
            return keywords
        else:
             st.warning("L'IA n'a pas retourné de mots-clés dans le format attendu.", icon="🤔")
             st.text_area("Réponse brute de l'IA (Mots-clés)", response, height=100)
             return None
    else:
        st.error("L'extraction des mots-clés par l'IA a échoué.", icon="❌")
        return None


@st.cache_data(show_spinner="Génération du nuage de mots...")
def generate_word_cloud(text: str, max_words: int = 100) -> io.BytesIO | None:
    """
    Génère un nuage de mots à partir du texte fourni.

    Args:
        text (str): Le texte source.
        max_words (int): Nombre maximum de mots à afficher dans le nuage.

    Returns:
        io.BytesIO: Un buffer contenant l'image PNG du nuage de mots, ou None si erreur.
    """
    if not text:
        st.warning("Le texte pour le nuage de mots est vide.", icon="⚠️")
        return None

    try:
        # Prétraitement simple du texte pour le nuage de mots
        # Convertir en minuscules et supprimer la ponctuation simple
        text_processed = re.sub(r'[^\w\s]', '', text.lower())

        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            stopwords=FRENCH_STOPWORDS,
            max_words=max_words,
            contour_width=1,
            contour_color='steelblue',
            colormap='viridis' # Choisir une palette de couleurs
        ).generate(text_processed)

        # Créer la figure matplotlib
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off') # Ne pas afficher les axes

        # Sauvegarder l'image dans un buffer mémoire
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0) # Rembobiner le buffer pour la lecture
        plt.close() # Fermer la figure pour libérer la mémoire

        st.success("Nuage de mots généré.", icon="☁️")
        return img_buffer

    except Exception as e:
        st.error(f"Erreur lors de la génération du nuage de mots : {e}", icon="🔥")
        return None


@st.cache_data(show_spinner="Calcul des fréquences de mots...")
def get_word_frequencies(text: str, num_top_words: int = 20) -> list[tuple[str, int]] | None:
    """
    Calcule la fréquence des mots les plus courants dans le texte (après filtrage).

    Args:
        text (str): Le texte source.
        num_top_words (int): Le nombre de mots les plus fréquents à retourner.

    Returns:
        list[tuple[str, int]]: Une liste de tuples (mot, fréquence), ou None si erreur.
    """
    if not text:
        st.warning("Le texte pour l'analyse de fréquence est vide.", icon="⚠️")
        return None

    try:
        # Prétraitement : minuscules, suppression ponctuation, séparation mots
        text_processed = re.sub(r'[^\w\s]', '', text.lower())
        words = text_processed.split()

        # Filtrer les mots vides et les mots trop courts
        filtered_words = [word for word in words if word not in FRENCH_STOPWORDS and len(word) > 2]

        # Compter les fréquences
        word_counts = Counter(filtered_words)

        # Obtenir les N mots les plus fréquents
        most_common = word_counts.most_common(num_top_words)

        if most_common:
             st.success(f"Fréquence des {len(most_common)} mots les plus courants calculée.", icon="📊")
             return most_common
        else:
             st.warning("Aucun mot significatif trouvé pour l'analyse de fréquence.", icon="🤔")
             return None

    except Exception as e:
        st.error(f"Erreur lors du calcul de la fréquence des mots : {e}", icon="🔥")
        return None


def display_analysis_interface(text_available: bool, document_text: str | None):
    """
    Affiche l'interface pour les options d'analyse et les résultats.

    Args:
        text_available (bool): Indique si du texte est disponible.
        document_text (str | None): Le texte du document chargé.
    """
    st.subheader("5. Analyse & Insights")

    if not text_available or not document_text:
        st.info("Chargez un document pour activer les fonctionnalités d'analyse.", icon="📄")
        return

    analysis_options = st.multiselect(
        "Choisissez les analyses à effectuer :",
        ["Extraction Mots-clés (IA)", "Nuage de Mots", "Fréquence des Mots"],
        default=["Extraction Mots-clés (IA)", "Nuage de Mots"], # Options par défaut
        key="analysis_selection"
    )

    run_analysis_button = st.button("Lancer l'Analyse", key="run_analysis_button", use_container_width=True)

    if run_analysis_button:
        st.session_state['analysis_results'] = {} # Réinitialiser les résultats

        if "Extraction Mots-clés (IA)" in analysis_options:
            keywords = extract_keywords_with_gemini(document_text, num_keywords=15)
            st.session_state['analysis_results']['keywords'] = keywords if keywords else "Échec de l'extraction"

        if "Nuage de Mots" in analysis_options:
            wordcloud_img = generate_word_cloud(document_text, max_words=100)
            st.session_state['analysis_results']['wordcloud'] = wordcloud_img

        if "Fréquence des Mots" in analysis_options:
            frequencies = get_word_frequencies(document_text, num_top_words=20)
            st.session_state['analysis_results']['frequencies'] = frequencies

    # Afficher les résultats stockés dans session_state
    if 'analysis_results' in st.session_state:
        results = st.session_state['analysis_results']
        st.markdown("---")
        st.markdown("### Résultats de l'Analyse")

        if 'keywords' in results:
            st.markdown("**Mots-clés extraits par l'IA :**")
            if isinstance(results['keywords'], list):
                # Afficher sous forme de badges ou liste
                st.write(", ".join(f"`{kw}`" for kw in results['keywords']))
            else:
                st.error(results['keywords']) # Afficher le message d'échec

        if 'wordcloud' in results and results['wordcloud']:
            st.markdown("**Nuage de Mots :**")
            st.image(results['wordcloud'], caption="Nuage des mots les plus fréquents", use_column_width=True)

        if 'frequencies' in results and results['frequencies']:
            st.markdown("**Mots les plus fréquents :**")
            # Afficher sous forme de tableau ou graphique simple
            freq_data = results['frequencies']
            # Créer un DataFrame pandas pour affichage facile
            try:
                import pandas as pd
                df_freq = pd.DataFrame(freq_data, columns=['Mot', 'Fréquence'])
                st.dataframe(df_freq, use_container_width=True, hide_index=True)

                # Optionnel : petit graphique à barres
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.barh(df_freq['Mot'], df_freq['Fréquence'], color='skyblue')
                ax.invert_yaxis() # Afficher le plus fréquent en haut
                ax.set_title('Top Mots par Fréquence')
                ax.set_xlabel('Fréquence')
                st.pyplot(fig)
                plt.close(fig) # Fermer la figure

            except ImportError:
                 st.warning("La bibliothèque Pandas est nécessaire pour afficher le tableau des fréquences. Veuillez l'installer (`pip install pandas`).", icon="⚠️")
                 # Afficher comme liste si pandas n'est pas là
                 for word, freq in freq_data:
                     st.write(f"- `{word}` : {freq}")
            except Exception as e:
                 st.error(f"Erreur lors de l'affichage des fréquences : {e}", icon="🔥")


# --- Intégration dans app.py ---
# doc_text = st.session_state.get('document_text', None)
# display_analysis_interface(text_available=bool(doc_text), document_text=doc_text)

