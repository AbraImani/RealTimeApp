import streamlit as st
import json
import random
import re # Pour le nettoyage potentiel du JSON
from . import gemini_client
from . import config
from . import utils

# Clés pour st.session_state (inchangées)
QUIZ_QUESTIONS_KEY = "quiz_questions"
QUIZ_ANSWERS_KEY = "quiz_user_answers"
QUIZ_SCORE_KEY = "quiz_score"
QUIZ_CURRENT_QUESTION_KEY = "quiz_current_question_index"
QUIZ_FEEDBACK_KEY = "quiz_feedback"
QUIZ_GENERATED_KEY = "quiz_generated"
LAST_QUIZ_RAW_RESPONSE_KEY = "last_quiz_raw_response"
DOCUMENT_CONTEXT_KEY = "document_text" # Assumer que le texte du doc est ici

# --- Fonctions de Génération (generate_quiz_questions reste identique à la version précédente) ---
def generate_quiz_questions(text: str,
                            num_questions: int = 5,
                            quiz_type: str = "QCM",
                            difficulty: str = "Moyen",
                            model_name: str = config.DEFAULT_TEXT_MODEL_NAME) -> list | None:
    """
    Génère une liste de questions de quiz basées sur le texte fourni.
    (Identique à la version précédente avec prompt amélioré)
    """
    if not text:
        st.warning("Le texte source pour le quiz est vide.", icon="⚠️")
        return None

    if not gemini_client.configure_gemini():
         st.error("Impossible de générer le quiz car le client Gemini n'est pas configuré.", icon="❌")
         return None

    quiz_type_desc = config.QUIZ_TYPES.get(quiz_type, "Questions à Choix Multiples")
    difficulty_desc = config.QUIZ_DIFFICULTY.get(difficulty, "moyen")

    # Limiter la taille du contexte pour la génération (évite erreurs/coûts excessifs)
    max_gen_context = 10000
    context_truncated = len(text) > max_gen_context
    text_for_prompt = text[:max_gen_context]

    prompt_parts = [
        f"Objectif : Générer un quiz de {num_questions} questions de type '{quiz_type_desc}' (difficulté: {difficulty_desc}) basé **strictement** sur le document suivant.",
        "--- DEBUT DOCUMENT ---",
        text_for_prompt,
        "--- FIN DOCUMENT ---" + (" (TRONQUÉ)" if context_truncated else ""),
        "\n--- FORMAT DE SORTIE EXIGE ---",
        "1. Réponds **UNIQUEMENT** avec une liste JSON valide commençant par `[` et se terminant par `]`.",
        "2. N'ajoute **AUCUN** texte, commentaire, explication ou formatage (comme ```json) avant ou après la liste JSON.",
        "3. Assure-toi que chaque objet JSON dans la liste est séparé par une virgule `,` (sauf le dernier).",
        "4. Assure-toi que toutes les chaînes de caractères dans le JSON sont correctement échappées (guillemets doubles `\"`).",
        "5. La structure de chaque objet JSON dépend du type de quiz demandé :"
    ]
    if quiz_type == "QCM":
        prompt_parts.extend([
            "   Pour QCM : `{ \"question\": \"...\", \"options\": [\"...\", \"...\", ...], \"correct_answer\": \"...\", \"explanation\": \"...\" }`",
            "   - 'options' doit être une liste d'au moins 3 chaînes.",
            "   - 'correct_answer' doit correspondre EXACTEMENT à l'une des chaînes dans 'options'."
        ])
    elif quiz_type == "Vrai/Faux":
        prompt_parts.extend([
            "   Pour Vrai/Faux : `{ \"question\": \"...\", \"correct_answer\": true/false, \"explanation\": \"...\" }`",
            "   - 'correct_answer' doit être un booléen JSON (`true` ou `false`, sans guillemets)."
        ])
    elif quiz_type == "Ouvertes":
        prompt_parts.extend([
            "   Pour Ouvertes : `{ \"question\": \"...\", \"ideal_answer_points\": [\"...\", \"...\", ...], \"explanation\": \"...\" }`",
            "   - 'ideal_answer_points' est une liste de chaînes décrivant les points clés attendus."
        ])
    prompt_parts.append("\n--- EXEMPLE (pour QCM) ---")
    prompt_parts.append("""
[
  {"question": "Exemple Q1?", "options": ["A", "B", "C"], "correct_answer": "B", "explanation": "Expl. Q1"},
  {"question": "Exemple Q2?", "options": ["X", "Y", "Z"], "correct_answer": "X", "explanation": "Expl. Q2"}
]
""")
    prompt_parts.append("\n--- IMPORTANT ---")
    prompt_parts.append(f"Génère exactement {num_questions} questions. Commence ta réponse directement par `[`.")
    full_prompt = "\n".join(prompt_parts)

    response = gemini_client.generate_text(prompt=full_prompt, model_name=model_name, temperature=0.4, max_output_tokens=3072)
    st.session_state[LAST_QUIZ_RAW_RESPONSE_KEY] = response

    if not response:
        st.error("La génération du quiz a échoué (pas de réponse de l'IA).", icon="❌")
        return None

    try:
        processed_response = response.strip()
        if processed_response.startswith("```json"): processed_response = processed_response[7:]
        if processed_response.startswith("```"): processed_response = processed_response[3:]
        if processed_response.endswith("```"): processed_response = processed_response[:-3]
        processed_response = processed_response.strip()
        json_start = processed_response.find('[')
        json_end = processed_response.rfind(']') + 1
        if json_start == -1 or json_end == -1:
            st.error("Erreur Format JSON : Impossible d'extraire une liste JSON (`[...]`) de la réponse de l'IA.", icon="❌")
            return None

        json_str = processed_response[json_start:json_end]
        quiz_data = json.loads(json_str)

        if not isinstance(quiz_data, list) or len(quiz_data) == 0:
            st.error("Erreur Format JSON : L'IA n'a pas retourné une liste de questions valide.", icon="❌")
            return None

        # Validation basique (peut être renforcée)
        first_q = quiz_data[0]
        q_type_detected = detect_quiz_type(first_q) # Utiliser la détection pour vérifier
        required_keys = []
        if q_type_detected == "QCM": required_keys = ['question', 'options', 'correct_answer', 'explanation']
        elif q_type_detected == "Vrai/Faux": required_keys = ['question', 'correct_answer', 'explanation']
        elif q_type_detected == "Ouvertes": required_keys = ['question', 'ideal_answer_points']

        if not required_keys or not all(key in first_q for key in required_keys):
             st.error(f"Erreur Format JSON : Les clés attendues pour le type '{q_type_detected}' ne sont pas toutes présentes.", icon="❌")
             return None

        st.success(f"Quiz de {len(quiz_data)} questions ({quiz_type}) généré avec succès !", icon="🧠")
        random.shuffle(quiz_data)
        return quiz_data

    except json.JSONDecodeError as e:
        st.error(f"Erreur de décodage JSON : L'IA a retourné un format invalide. Détails : {e}", icon="❌")
        return None
    except Exception as e:
        st.error(f"Erreur inattendue lors du traitement de la réponse du quiz : {e}", icon="🔥")
        return None


# --- Nouvelle Fonction pour évaluer les réponses ouvertes ---
# @st.cache_data # Attention au cache ici, l'évaluation peut dépendre de l'état actuel
def evaluate_open_ended_answer(user_answer: str, question_data: dict, document_context: str | None) -> str:
    """
    Évalue une réponse ouverte en utilisant Gemini et retourne le feedback.

    Args:
        user_answer (str): La réponse fournie par l'utilisateur.
        question_data (dict): Les données de la question (incluant 'question' et 'ideal_answer_points').
        document_context (str | None): Le contexte du document original.

    Returns:
        str: Le feedback généré par l'IA.
    """
    if not user_answer or not question_data:
        return "Impossible d'évaluer : données manquantes."

    if not gemini_client.configure_gemini():
        return "Évaluation impossible : client Gemini non configuré."

    question_text = question_data.get('question', '')
    ideal_points = question_data.get('ideal_answer_points', [])
    explanation = question_data.get('explanation', '') # Contexte additionnel de la question

    # Préparer le contexte (limité pour l'évaluation)
    eval_context = ""
    if document_context:
        # Stratégie simple : prendre un extrait autour de mots clés de la question ?
        # Ou juste les N premiers caractères comme pour le chat ? Prenons une limite raisonnable.
        max_eval_context = 4000
        eval_context = document_context[:max_eval_context]
        if len(document_context) > max_eval_context:
             eval_context += "\n[... CONTEXTE TRONQUÉ ...]"

    # Construire le prompt d'évaluation
    prompt_parts = [
        "Rôle : Tu es un assistant pédagogique chargé d'évaluer la réponse d'un utilisateur à une question ouverte, en te basant **strictement** sur les points clés attendus et le contexte du document fourni.",
        "\n--- CONTEXTE DU DOCUMENT (Source de vérité) ---",
        eval_context if eval_context else "[Aucun contexte fourni]",
        "--- FIN DU CONTEXTE ---",
        "\n--- QUESTION POSÉE ---",
        question_text,
        "\n--- POINTS CLÉS ATTENDUS DANS LA RÉPONSE IDÉALE ---",
        "- " + "\n- ".join(ideal_points) if ideal_points else "[Aucun point clé spécifié]",
        f"\n--- EXPLICATION/CONTEXTE DE LA QUESTION (si disponible) ---",
        explanation if explanation else "[Aucune]",
        "\n--- RÉPONSE DE L'UTILISATEUR À ÉVALUER ---",
        user_answer,
        "\n--- INSTRUCTIONS D'ÉVALUATION ---",
        "1. Compare la réponse de l'utilisateur aux points clés attendus ET au contexte du document.",
        "2. Évalue la pertinence, l'exactitude et la complétude de la réponse.",
        "3. Fournis un feedback constructif et détaillé en français.",
        "4. Commence ton feedback par une appréciation générale (ex: 'Correct.', 'Partiellement correct.', 'Incorrect.', 'Bonne tentative, mais...').",
        "5. Explique pourquoi la réponse est correcte/incorrecte/partielle, en citant si possible des éléments du contexte ou des points clés.",
        "6. Si la réponse est proche mais manque des éléments, suggère des améliorations ou les points manquants.",
        "7. Sois concis mais précis.",
        "\n--- FEEDBACK DÉTAILLÉ (Commence ici) ---"
    ]
    full_prompt = "\n".join(prompt_parts)

    # Appeler Gemini pour l'évaluation
    feedback_response = gemini_client.generate_text(
        prompt=full_prompt,
        temperature=0.5, # Équilibré pour l'évaluation
        max_output_tokens=512 # Assez pour un feedback détaillé
    )

    if feedback_response:
        return feedback_response.strip()
    else:
        return "[Erreur lors de la génération du feedback par l'IA]"


# --- Fonctions d'initialisation et d'options (inchangées) ---
def initialize_quiz_state():
    if QUIZ_QUESTIONS_KEY not in st.session_state: st.session_state[QUIZ_QUESTIONS_KEY] = []
    if QUIZ_ANSWERS_KEY not in st.session_state: st.session_state[QUIZ_ANSWERS_KEY] = {}
    if QUIZ_SCORE_KEY not in st.session_state: st.session_state[QUIZ_SCORE_KEY] = 0
    if QUIZ_CURRENT_QUESTION_KEY not in st.session_state: st.session_state[QUIZ_CURRENT_QUESTION_KEY] = 0
    if QUIZ_FEEDBACK_KEY not in st.session_state: st.session_state[QUIZ_FEEDBACK_KEY] = {}
    if QUIZ_GENERATED_KEY not in st.session_state: st.session_state[QUIZ_GENERATED_KEY] = False
    if LAST_QUIZ_RAW_RESPONSE_KEY not in st.session_state: st.session_state[LAST_QUIZ_RAW_RESPONSE_KEY] = None
    # Assurer que la clé pour le contexte existe aussi
    if DOCUMENT_CONTEXT_KEY not in st.session_state: st.session_state[DOCUMENT_CONTEXT_KEY] = None


def reset_quiz_state():
    st.session_state[QUIZ_QUESTIONS_KEY] = []
    st.session_state[QUIZ_ANSWERS_KEY] = {}
    st.session_state[QUIZ_SCORE_KEY] = 0
    st.session_state[QUIZ_CURRENT_QUESTION_KEY] = 0
    st.session_state[QUIZ_FEEDBACK_KEY] = {}
    st.session_state[QUIZ_GENERATED_KEY] = False
    st.session_state[LAST_QUIZ_RAW_RESPONSE_KEY] = None

def display_quiz_options(text_available: bool):
    st.subheader("4. Quiz Génératif")
    if not text_available:
        st.info("Chargez un document pour activer la génération de quiz.", icon="📄")
        last_raw_response = st.session_state.get(LAST_QUIZ_RAW_RESPONSE_KEY)
        if last_raw_response:
             with st.expander("Afficher la dernière réponse brute de l'IA (pour débogage)"):
                  st.text_area("Réponse Brute", last_raw_response, height=200, key="last_quiz_raw_debug_no_text")
        return None, None, None, False

    col1, col2, col3 = st.columns(3)
    with col1:
        num_questions = st.number_input("Nombre de questions :", min_value=1, max_value=50, value=5, step=1, key="quiz_num_questions", help="Attention: Demander un très grand nombre de questions augmente le risque d'erreurs de formatage par l'IA.")
    with col2:
        quiz_type = st.selectbox("Type de questions :", options=list(config.QUIZ_TYPES.keys()), key="quiz_type_select")
    with col3:
        quiz_difficulty = st.selectbox("Difficulté :", options=list(config.QUIZ_DIFFICULTY.keys()), index=1, key="quiz_difficulty_select")

    generate_button = st.button("Générer le Quiz", key="generate_quiz_button", type="primary", use_container_width=True)
    if generate_button: reset_quiz_state()

    last_raw_response = st.session_state.get(LAST_QUIZ_RAW_RESPONSE_KEY)
    if last_raw_response and not st.session_state.get(QUIZ_GENERATED_KEY, False):
         with st.expander("Afficher la dernière réponse brute de l'IA (pour débogage)"):
              st.text_area("Réponse Brute", last_raw_response, height=200, key="last_quiz_raw_debug")

    return num_questions, quiz_type, quiz_difficulty, generate_button

# --- Fonctions d'affichage et d'évaluation (modifiées pour évaluation ouverte) ---

def detect_quiz_type(question_data: dict) -> str:
    """Détecte le type de question basé sur les clés présentes (version améliorée)."""
    if not isinstance(question_data, dict): return "Inconnu"
    has_options = "options" in question_data and isinstance(question_data["options"], list)
    has_correct_answer = "correct_answer" in question_data
    has_ideal_points = "ideal_answer_points" in question_data and isinstance(question_data["ideal_answer_points"], list)
    if has_options and has_correct_answer: return "QCM"
    if has_correct_answer and isinstance(question_data["correct_answer"], bool): return "Vrai/Faux"
    if has_correct_answer and isinstance(question_data["correct_answer"], str) and question_data["correct_answer"].lower() in ['true', 'false']: return "Vrai/Faux"
    if has_ideal_points: return "Ouvertes"
    return "Inconnu"

def display_quiz_interface():
    """Affiche l'interface du quiz (questions, réponses, score)."""
    initialize_quiz_state()
    questions = st.session_state.get(QUIZ_QUESTIONS_KEY, [])
    quiz_successfully_generated = st.session_state.get(QUIZ_GENERATED_KEY, False)

    if not questions or not quiz_successfully_generated:
        if not st.session_state.get(LAST_QUIZ_RAW_RESPONSE_KEY):
             st.info("Générez un quiz à partir d'un document pour commencer.", icon="💡")
        return

    current_index = st.session_state.get(QUIZ_CURRENT_QUESTION_KEY, 0)
    total_questions = len(questions)

    if current_index >= total_questions:
        display_quiz_results()
        return

    st.progress((current_index + 1) / total_questions, text=f"Question {current_index + 1}/{total_questions}")
    question_data = questions[current_index]
    question_text = question_data.get("question", "Erreur: Texte de question manquant")
    quiz_type = detect_quiz_type(question_data)

    if quiz_type == "Inconnu":
         st.error(f"Erreur interne: Type de question non reconnu pour la question {current_index + 1}.", icon="🆘")

    st.markdown(f"**Question {current_index + 1}:**")
    st.markdown(f"> {question_text}")

    user_answer = None
    answer_key = f"q_{current_index}_answer"
    widget_disabled = (quiz_type == "Inconnu")

    try:
        if quiz_type == "QCM":
            options = question_data.get("options", [])
            if not options or not isinstance(options, list): options = ["Erreur format"]
            user_answer = st.radio("Choisissez votre réponse :", options, key=answer_key, index=None, disabled=widget_disabled)
        elif quiz_type == "Vrai/Faux":
            user_answer = st.radio("Votre réponse :", [True, False], format_func=lambda x: "Vrai" if x else "Faux", key=answer_key, index=None, disabled=widget_disabled)
        elif quiz_type == "Ouvertes":
            user_answer = st.text_area("Votre réponse :", key=answer_key, placeholder="Entrez votre réponse ici...", disabled=widget_disabled)
    except Exception as display_e:
         st.error(f"Erreur lors de l'affichage des options de réponse : {display_e}", icon="🆘")
         widget_disabled = True # Désactiver soumission si affichage échoue

    submit_button = st.button("Valider et Suivant", key=f"submit_q_{current_index}", type="primary", disabled=widget_disabled)

    if submit_button:
        # Vérifier si une réponse a été donnée (non vide pour Ouvertes)
        response_given = user_answer is not None
        if quiz_type == "Ouvertes" and isinstance(user_answer, str) and not user_answer.strip():
             response_given = False

        if response_given:
            st.session_state[QUIZ_ANSWERS_KEY][current_index] = user_answer
            is_correct = None # Reste None pour Ouvertes
            feedback_text = "Feedback non disponible."

            try:
                if quiz_type == "QCM" or quiz_type == "Vrai/Faux":
                    correct_answer = question_data.get("correct_answer")
                    # Évaluation QCM/VF (logique précédente)
                    if quiz_type == "QCM":
                        is_correct = (user_answer == correct_answer)
                    elif quiz_type == "Vrai/Faux":
                        correct_bool = None
                        if isinstance(correct_answer, bool): correct_bool = correct_answer
                        elif isinstance(correct_answer, str):
                            if correct_answer.lower() == 'true': correct_bool = True
                            elif correct_answer.lower() == 'false': correct_bool = False
                        if correct_bool is not None: is_correct = (user_answer == correct_bool)
                        else: explanation = f"[Erreur format réponse attendue: {correct_answer}] " + question_data.get('explanation', '')

                    # Générer feedback QCM/VF
                    explanation = question_data.get('explanation', 'Pas d\'explication.')
                    if is_correct is True:
                        st.session_state[QUIZ_SCORE_KEY] += 1
                        feedback_text = f"✅ **Correct !** {explanation}"
                    elif is_correct is False:
                        correct_ans_display = correct_answer if not isinstance(correct_answer, bool) else ("Vrai" if correct_answer else "Faux")
                        feedback_text = f"❌ **Incorrect.** La bonne réponse était : `{correct_ans_display}`. {explanation}"
                    else: # Erreur format réponse correcte
                         feedback_text = f"⚠️ Impossible d'évaluer (format réponse attendue invalide). {explanation}"

                elif quiz_type == "Ouvertes":
                    # --- Appel à l'évaluation IA ---
                    with st.spinner("Évaluation de la réponse par l'IA..."):
                        document_context = st.session_state.get(DOCUMENT_CONTEXT_KEY)
                        feedback_text = evaluate_open_ended_answer(user_answer, question_data, document_context)
                    # is_correct reste None, on se base sur le texte du feedback

                # Stocker et afficher le feedback
                st.session_state[QUIZ_FEEDBACK_KEY][current_index] = (is_correct, feedback_text)
                if is_correct is True: st.success(feedback_text)
                elif is_correct is False: st.error(feedback_text)
                else: st.info(feedback_text) # Pour Ouvertes ou erreurs VF

                # Passer à la question suivante
                st.session_state[QUIZ_CURRENT_QUESTION_KEY] += 1
                st.rerun()

            except Exception as eval_e:
                 st.error(f"Erreur lors de l'évaluation/feedback : {eval_e}", icon="🆘")
                 st.session_state[QUIZ_FEEDBACK_KEY][current_index] = (None, f"Erreur évaluation: {eval_e}")
                 st.session_state[QUIZ_CURRENT_QUESTION_KEY] += 1
                 st.rerun()
        else:
            st.warning("Veuillez sélectionner ou entrer une réponse avant de valider.", icon="⚠️")


def display_quiz_results():
    """Affiche les résultats finaux du quiz."""
    st.subheader("🏁 Résultats du Quiz 🏁")
    questions = st.session_state.get(QUIZ_QUESTIONS_KEY, [])
    answers = st.session_state.get(QUIZ_ANSWERS_KEY, {})
    feedback = st.session_state.get(QUIZ_FEEDBACK_KEY, {})
    score = st.session_state.get(QUIZ_SCORE_KEY, 0)
    total_questions = len(questions)
    evaluated_questions = sum(1 for i, fb in feedback.items() if i < total_questions and fb[0] is not None) # QCM/VF évaluées

    if total_questions == 0:
         st.warning("Aucune question trouvée pour afficher les résultats.")
         return

    if evaluated_questions > 0:
        percentage = (score / evaluated_questions) * 100
        st.metric("Score Final (QCM/Vrai-Faux)", f"{score}/{evaluated_questions}", f"{percentage:.1f}%")
    else:
        st.info("Aucune question QCM ou Vrai/Faux n'a été évaluée.")

    st.markdown("---")
    st.markdown("**Récapitulatif détaillé :**")

    for i, question_data in enumerate(questions):
        q_text_short = question_data.get('question', f'Question {i+1}')[:60] + "..."
        with st.expander(f"Question {i+1}: {q_text_short}", expanded=False):
            st.markdown(f"**Question :** {question_data.get('question', 'N/A')}")
            user_ans = answers.get(i, "*Non répondue*")
            fb = feedback.get(i) # Tuple (is_correct, feedback_text)
            q_type = detect_quiz_type(question_data)

            # Affichage réponse utilisateur
            user_ans_display = "*Non répondue*"
            if isinstance(user_ans, bool): user_ans_display = "`Vrai`" if user_ans else "`Faux`"
            elif user_ans is not None: user_ans_display = f"`{str(user_ans)}`" if q_type != "Ouvertes" else str(user_ans)

            if q_type != "Ouvertes":
                 st.write(f"Votre réponse : {user_ans_display}")
            else:
                 st.write("Votre réponse :")
                 # Utiliser st.markdown ou st.text pour les réponses ouvertes
                 st.text(user_ans_display if user_ans_display != "*Non répondue*" else user_ans_display)


            # Affichage feedback (qui contient déjà la correction si nécessaire)
            if fb:
                 feedback_text = fb[1]
                 is_correct = fb[0] # Peut être True, False, ou None (Ouvertes/Erreur)
                 if is_correct is True: st.success(feedback_text)
                 elif is_correct is False: st.error(feedback_text)
                 else: st.info(feedback_text) # Ouvertes ou Erreur d'évaluation VF
            else:
                 # Fallback si pas de feedback (ne devrait pas arriver)
                 st.warning("Feedback non disponible.")
                 # Afficher manuellement la correction pour QCM/VF dans ce cas fallback
                 if q_type == "QCM" or q_type == "Vrai/Faux":
                     correct_ans = question_data.get('correct_answer', 'N/A')
                     correct_ans_display = correct_ans
                     if isinstance(correct_ans, bool): correct_ans_display = "`Vrai`" if correct_ans else "`Faux`"
                     elif correct_ans != 'N/A': correct_ans_display = f"`{correct_ans}`"
                     st.write(f"Réponse correcte (fallback): {correct_ans_display}")
                     st.write(f"Explication (fallback): {question_data.get('explanation', 'N/A')}")
                 elif q_type == "Ouvertes":
                      st.write(f"Points clés attendus (fallback): {', '.join(question_data.get('ideal_answer_points', ['N/A']))}")

    # Boutons finaux
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Recommencer un nouveau quiz", key="restart_quiz_button"):
            reset_quiz_state()
            st.rerun()

