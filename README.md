# RealTime AI Prototyper avec Gemini & Streamlit

Cette application Streamlit permet de prototyper rapidement des fonctionnalités d'IA en utilisant l'API Google Gemini. Elle prend en charge l'importation de documents multi-formats (PDF, DOCX, TXT, JSON), le résumé automatique, le chat contextuel, la génération de quiz, l'analyse de texte et l'exportation des résultats.

## Fonctionnalités (Version Initiale)

* **Importation de Documents :** Uploadez des fichiers PDF, DOCX, TXT ou JSON.
* **Résumé Automatique :** Générez des résumés de longueur variable (court, moyen, long) ou basés sur des mots-clés.
* **Chat Contextuel :** Discutez avec l'IA Gemini en utilisant le contenu du document importé comme contexte (avec une limite de caractères).
* **Quiz Génératif :** Créez automatiquement des quiz (QCM, Vrai/Faux, Ouvertes) basés sur le document.
* **Analyse & Insights :** Extrayez des mots-clés, visualisez un nuage de mots (matplotlib) et obtenez des insights basiques.
* **Export :** Exportez les résumés ou les résultats de quiz en CSV ou PDF. Sauvegarde optionnelle en base de données SQLite.

## Structure du projet `RealTime_AI_Prototyper`

1. **.streamlit/**  
   * **config.toml** : fichier de configuration optionnel pour personnaliser l’interface Streamlit.

2. **modules/**  
   Répertoire central contenant tous les composants métiers, chacun dans son propre module :  
   * **config.py** : gestion des paramètres (clés API, variables d’environnement…)  
   * **utils.py** : fonctions utilitaires réutilisables (nettoyage et formatage de texte…)  
   * **loader.py** : chargement, prétraitement et validation des documents d’entrée  
   * **gemini_client.py** : encapsulation des appels à l’API Gemini pour les traitements LLM  
   * **summarizer.py** : génération automatique de résumés de documents  
   * **chatbot.py** : orchestration du chatbot avec gestion de contexte  
   * **quiz.py** : création et évaluation de quiz à partir du contenu  
   * **analyzer.py** : analyses textuelles (extraction de mots-clés, nuages, graphiques…)  
   * **exporter.py** : export des résultats au format CSV, PDF ou insertion SQLite  

3. **static/**  
   * **style.css** : feuille de style CSS personnalisée (images et autres ressources statiques dans ce dossier).

4. **tests/**  
   * **test_utils.py** : suite de tests unitaires pour vérifier les utilitaires et garantir la fiabilité de chaque module.

5. **app.py**  
   Point d’entrée principal : lance l’interface Streamlit et orchestre l’ensemble des modules.

6. **requirements.txt**  
   Liste des dépendances Python nécessaires à l’installation du projet.

7. **README.md**  
   Ce document : instructions d’installation, d’exécution et guide d’utilisation du prototype.

## Installation

1.  **Clonez le dépôt ou téléchargez les fichiers :**
    Assurez-vous d'avoir tous les fichiers Python (`app.py`, ceux dans `modules/`) et le fichier `requirements.txt` (version initiale) dans un dossier nommé `RealTime_AI_Prototyper`.

2.  **Créez un environnement virtuel (recommandé) :**
    Ouvrez un terminal ou une invite de commande, naviguez jusqu'au dossier `RealTime_AI_Prototyper` et exécutez :
    ```bash
    python -m venv venv
    # Activez l'environnement :
    # Sur Linux/macOS:
    source venv/bin/activate
    # Sur Windows:
    .\venv\Scripts\activate
    ```

3.  **Installez les dépendances (version initiale) :**
    Assurez-vous que votre fichier `requirements.txt` contienne bien les dépendances de la première version :
    ```plaintext
    # requirements.txt (contenu initial)
    streamlit>=1.28.0,<2.0.0
    google-generativeai>=0.3.0,<0.4.0
    pypdf2>=3.0.0,<4.0.0
    python-docx>=1.0.0,<2.0.0
    pandas>=2.0.0,<3.0.0
    matplotlib>=3.7.0,<4.0.0
    wordcloud>=1.9.0,<2.0.0
    scikit-learn>=1.3.0,<2.0.0
    fpdf2>=2.7.0,<3.0.0
    pytest>=7.0.0,<8.0.0
    ```
    Puis, installez-les :
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurez votre clé API Gemini :**
    * Obtenez votre clé API depuis [Google AI Studio](https://aistudio.google.com/app/apikey).
    * **Méthode Recommandée (`secrets.toml`) :**
        * Créez un dossier nommé `.streamlit` à la racine de votre projet (`RealTime_AI_Prototyper/.streamlit/`).
        * Dans ce dossier `.streamlit`, créez un fichier nommé `secrets.toml`.
        * Ajoutez la ligne suivante dans `secrets.toml`, en remplaçant `"VOTRE_CLE_API_ICI"` par votre clé :
            ```toml
            # .streamlit/secrets.toml
            gemini_api_key = "VOTRE_CLE_API_ICI"
            ```
    * **Alternative (Variable d'environnement) :** Définissez une variable d'environnement `GOOGLE_API_KEY` avec votre clé.
    * **Alternative (Non recommandée - Code) :** Modifiez directement `modules/config.py` pour y insérer votre clé (attention si vous partagez le code).

## Utilisation

Lancez l'application Streamlit depuis le dossier racine `RealTime_AI_Prototyper` :

```bash
streamlit run app.py

Ouvrez votre navigateur à l'adresse indiquée (généralement http://localhost:8501).

Développement & Tests
Tests : La structure de test est basique. Pour exécuter (si des tests sont écrits) :

pytest tests
