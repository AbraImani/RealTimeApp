import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import datetime
import sqlite3
from . import config # Pour le nom de la DB
from . import quiz

# --- Fonctions d'Export ---

def export_to_csv(data, filename_prefix: str = "export") -> bytes | None:
    """
    Exporte des données (typiquement une liste de dictionnaires ou un DataFrame) en CSV.

    Args:
        data: Les données à exporter (list[dict] ou pd.DataFrame).
        filename_prefix (str): Préfixe pour le nom du fichier CSV.

    Returns:
        bytes: Le contenu du fichier CSV en bytes, ou None si erreur.
    """
    if data is None or (isinstance(data, list) and not data):
        st.warning("Aucune donnée à exporter en CSV.", icon="⚠️")
        return None

    try:
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            st.error("Format de données non supporté pour l'export CSV.", icon="❌")
            return None

        # Convertir le DataFrame en CSV dans un buffer mémoire
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig') # utf-8-sig pour compatibilité Excel
        csv_buffer.seek(0)

        # Retourner les bytes du CSV
        return csv_buffer.getvalue().encode('utf-8-sig')

    except Exception as e:
        st.error(f"Erreur lors de la génération du fichier CSV : {e}", icon="🔥")
        return None


class PDF(FPDF):
    """Classe héritée de FPDF pour ajouter en-tête et pied de page."""
    def header(self):
        # Utiliser une police supportant l'UTF-8 si possible ou gérer l'encodage
        try:
            self.set_font('Arial', 'B', 12)
        except RuntimeError:
            self.set_font('Times', 'B', 12)
        title = config.APP_TITLE + ' - Export'
        # Encoder en latin-1 pour FPDF par défaut
        title_encoded = title.encode('latin-1', 'replace').decode('latin-1')
        self.cell(0, 10, title_encoded, 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font('Arial', 'I', 8)
        except RuntimeError:
            self.set_font('Times', 'I', 8)

        page_num_text = f'Page {self.page_no()}/{{nb}}'
        self.cell(0, 10, page_num_text, 0, 0, 'C')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.set_x(10) # Position à gauche
        self.cell(0, 10, timestamp, 0, 0, 'L')


def export_summary_to_pdf(summary_text: str, document_name: str | None = None) -> bytes | None:
    """
    Exporte un texte de résumé en fichier PDF.

    Args:
        summary_text (str): Le résumé à exporter.
        document_name (str | None): Le nom du document original (optionnel).

    Returns:
        bytes: Le contenu du fichier PDF en bytes, ou None si erreur.
    """
    if not summary_text:
        st.warning("Aucun résumé à exporter en PDF.", icon="⚠️")
        return None

    try:
        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Essayer d'utiliser une police standard
        try:
            pdf.set_font('Arial', 'B', 14)
        except RuntimeError:
            pdf.set_font('Times', 'B', 14)


        title = "Résumé Généré"
        if document_name:
            title += f" pour : {document_name}"
        # Encoder pour FPDF
        title_encoded = title.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, title_encoded, 0, 1, 'L')
        pdf.ln(5)

        # Ajouter le texte du résumé
        try:
            pdf.set_font('Arial', '', 11)
        except RuntimeError:
            pdf.set_font('Times', '', 11)

        # Encoder le texte principal
        summary_text_latin1 = summary_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, summary_text_latin1)
        pdf.ln(10)

        # Générer le PDF en bytes
        pdf_output = pdf.output(dest='S').encode('latin-1') # 'S' pour string/bytes
        return pdf_output

    except Exception as e:
        st.error(f"Erreur lors de la génération du fichier PDF du résumé : {e}", icon="🔥")
        return None


def export_quiz_results_to_pdf(questions: list, answers: dict, feedback: dict, score: int, total_evaluated: int, document_name: str | None = None) -> bytes | None:
    """
    Exporte les résultats d'un quiz (questions, réponses, feedback, score) en PDF.

    Args:
        questions (list): Liste des questions du quiz.
        answers (dict): Dictionnaire des réponses de l'utilisateur {index: reponse}.
        feedback (dict): Dictionnaire du feedback {index: (is_correct, feedback_text)}.
        score (int): Score obtenu (QCM/VF).
        total_evaluated (int): Nombre total de questions QCM/VF.
        document_name (str | None): Nom du document source (optionnel).

    Returns:
        bytes: Le contenu du PDF en bytes, ou None si erreur.
    """
    if not questions:
        st.warning("Aucun résultat de quiz à exporter en PDF.", icon="⚠️")
        return None

    try:
        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # --- Titre ---
        try:
            pdf.set_font('Arial', 'B', 14)
        except RuntimeError:
            pdf.set_font('Times', 'B', 14)
        title = "Résultats du Quiz"
        if document_name:
            title += f" - Document : {document_name}"
        title_encoded = title.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, title_encoded, 0, 1, 'L')
        pdf.ln(5)

        # --- Score ---
        try:
            pdf.set_font('Arial', 'B', 12)
        except RuntimeError:
            pdf.set_font('Times', 'B', 12)
        if total_evaluated > 0:
            percentage = (score / total_evaluated) * 100
            score_text = f"Score Final (QCM/Vrai-Faux) : {score}/{total_evaluated} ({percentage:.1f}%)"
        else:
            score_text = "Score : Aucune question QCM/Vrai-Faux évaluée"
        score_text_encoded = score_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 10, score_text_encoded, 0, 1, 'L')
        pdf.ln(5)

        # --- Détails par question ---
        for i, q_data in enumerate(questions):
            # Police pour la question
            try:
                pdf.set_font('Arial', 'B', 11)
            except RuntimeError:
                pdf.set_font('Times', 'B', 11)
            q_text = q_data.get('question', 'N/A').encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, f"Question {i+1}: {q_text}")
            pdf.ln(2)

            # Police pour les détails
            try:
                pdf.set_font('Arial', '', 10)
            except RuntimeError:
                pdf.set_font('Times', '', 10)

            user_ans = answers.get(i, "*Non répondue*")
            fb_data = feedback.get(i)
            q_type = quiz.detect_quiz_type(q_data)

            # Formater la réponse utilisateur
            if isinstance(user_ans, bool): user_ans_str = "Vrai" if user_ans else "Faux"
            elif user_ans is None: user_ans_str = "*Non répondue*"
            else: user_ans_str = str(user_ans)
            user_ans_str_encoded = user_ans_str.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, f"Votre réponse : {user_ans_str_encoded}")

            # Afficher la correction et l'explication
            correct_ans_str_encoded = "N/A"
            if q_type == "QCM" or q_type == "Vrai/Faux":
                correct_ans = q_data.get('correct_answer')
                if isinstance(correct_ans, bool): correct_ans_str = "Vrai" if correct_ans else "Faux"
                else: correct_ans_str = str(correct_ans)
                correct_ans_str_encoded = correct_ans_str.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 5, f"Réponse correcte : {correct_ans_str_encoded}")
            elif q_type == "Ouvertes":
                 ideal_points = q_data.get('ideal_answer_points', ['N/A'])
                 ideal_points_str = ", ".join(ideal_points).encode('latin-1', 'replace').decode('latin-1')
                 pdf.multi_cell(0, 5, f"Points clés attendus : {ideal_points_str}")


            explanation = q_data.get('explanation', 'N/A').encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, f"Explication : {explanation}")

            # Afficher le feedback
            if fb_data:
                 fb_text = fb_data[1].encode('latin-1', 'replace').decode('latin-1')
                 status_icon = "[Correct]" if fb_data[0] else "[Incorrect]" if fb_data[0] is False else "[Ouverte]"
                 try:
                     pdf.set_font('Arial', 'I', 10)
                 except RuntimeError:
                     pdf.set_font('Times', 'I', 10)
                 pdf.multi_cell(0, 5, f"Feedback : {status_icon} {fb_text}")

            pdf.ln(5) # Espace entre les questions

        # Générer le PDF en bytes
        pdf_output = pdf.output(dest='S').encode('latin-1')
        return pdf_output

    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF des résultats du quiz : {e}", icon="🔥")
        return None


# --- Fonctions Base de Données (SQLite - Optionnel) ---
# ... (init_db, save_summary_to_db, etc. restent identiques) ...
def init_db(db_name: str = config.DATABASE_NAME):
    """Initialise la base de données SQLite et crée les tables si elles n'existent pas."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            keywords TEXT,
            summary_text TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            quiz_type TEXT,
            difficulty TEXT,
            num_questions INTEGER,
            score INTEGER,
            total_evaluated INTEGER,
            results_details TEXT -- Stocker les questions/réponses/feedback en JSON ?
        )
        """)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Erreur lors de l'initialisation de la base de données SQLite : {e}", icon="🔥")

def save_summary_to_db(summary_text: str, level: str, keywords: str | None, document_name: str | None, db_name: str = config.DATABASE_NAME):
    """Sauvegarde un résumé dans la base de données SQLite."""
    if not summary_text: return False
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO summaries (document_name, level, keywords, summary_text)
        VALUES (?, ?, ?, ?)
        """, (document_name, level, keywords, summary_text))
        conn.commit()
        conn.close()
        st.success("Résumé sauvegardé dans la base de données.", icon="💾")
        return True
    except sqlite3.Error as e:
        st.error(f"Erreur lors de la sauvegarde du résumé en base de données : {e}", icon="🔥")
        return False

# --- Interface Streamlit pour l'Export ---

def display_export_options(export_type: str, data_to_export, filename_base: str):
    """
    Affiche les boutons d'exportation CSV et PDF pour un type de données donné.
    Ajout de clés uniques aux boutons.

    Args:
        export_type (str): Type de données ('summary', 'quiz_results', etc.).
        data_to_export: Les données spécifiques à exporter (texte, liste, etc.).
        filename_base (str): Base pour le nom de fichier (ex: nom du document).
    """
    st.markdown("---")
    st.markdown("**Exporter :**")
    col1, col2, col3 = st.columns([1, 1, 2]) # Ajuster les largeurs au besoin

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_prefix = f"{filename_base}_{export_type}_{timestamp}"

    # Générer des clés uniques basées sur le type d'export
    csv_button_key = f"export_csv_{export_type}_button"
    pdf_button_key = f"export_pdf_{export_type}_button"
    db_button_key = f"export_db_{export_type}_button" # Pour le bouton DB optionnel

    with col1:
        # Export CSV
        csv_bytes = None
        csv_enabled = False
        if export_type == 'quiz_results': # CSV pertinent pour les résultats structurés
            questions = st.session_state.get(quiz.QUIZ_QUESTIONS_KEY, [])
            if questions: # Vérifier s'il y a des questions avant de préparer les données
                answers = st.session_state.get(quiz.QUIZ_ANSWERS_KEY, {})
                feedback = st.session_state.get(quiz.QUIZ_FEEDBACK_KEY, {})
                csv_data = []
                for i, q in enumerate(questions):
                    fb_data = feedback.get(i, (None, 'N/A'))
                    csv_data.append({
                        "Question_Num": i + 1,
                        "Question": q.get('question', 'N/A'),
                        "Type": quiz.detect_quiz_type(q),
                        "Options": ", ".join(q.get('options', [])) if 'options' in q else 'N/A',
                        "Reponse_Correcte": q.get('correct_answer', 'N/A'),
                        "Reponse_Utilisateur": answers.get(i, 'N/A'),
                        "Est_Correct": fb_data[0],
                        "Feedback": fb_data[1],
                        "Explication": q.get('explanation', 'N/A')
                    })
                csv_bytes = export_to_csv(csv_data, filename_prefix)
                if csv_bytes:
                    csv_enabled = True

        if csv_enabled:
            st.download_button(
                label="📥 CSV",
                data=csv_bytes,
                file_name=f"{filename_prefix}.csv",
                mime='text/csv',
                key=csv_button_key, # Clé unique
                help="Exporter les résultats détaillés en CSV."
            )
        else:
            # Afficher un bouton désactivé même si non pertinent pour ce type
            st.button(
                "📥 CSV",
                key=csv_button_key, # Clé unique
                disabled=True,
                help="Export CSV non disponible ou données manquantes."
            )

    with col2:
        # Export PDF
        pdf_bytes = None
        pdf_enabled = False
        if export_type == 'summary' and isinstance(data_to_export, str):
            pdf_bytes = export_summary_to_pdf(data_to_export, filename_base)
        elif export_type == 'quiz_results':
             questions = st.session_state.get(quiz.QUIZ_QUESTIONS_KEY, [])
             if questions: # Vérifier s'il y a des questions
                 answers = st.session_state.get(quiz.QUIZ_ANSWERS_KEY, {})
                 feedback = st.session_state.get(quiz.QUIZ_FEEDBACK_KEY, {})
                 score = st.session_state.get(quiz.QUIZ_SCORE_KEY, 0)
                 evaluated = sum(1 for fb in feedback.values() if fb[0] is not None)
                 pdf_bytes = export_quiz_results_to_pdf(questions, answers, feedback, score, evaluated, filename_base)

        if pdf_bytes:
            pdf_enabled = True
            st.download_button(
                label="📄 PDF",
                data=pdf_bytes,
                file_name=f"{filename_prefix}.pdf",
                mime='application/pdf',
                key=pdf_button_key, # Clé unique
                help=f"Exporter {export_type.replace('_', ' ')} en PDF."
            )
        else:
            st.button(
                "📄 PDF",
                key=pdf_button_key, # Clé unique
                disabled=True,
                help="Impossible de générer le PDF ou données manquantes."
            )

    # with col3: # Optionnel : Sauvegarde DB
    #     db_enabled = False
    #     help_text_db = "Sauvegarde en base de données non disponible."
    #     if export_type == 'summary' and isinstance(data_to_export, str):
    #         db_enabled = True
    #         help_text_db = "Sauvegarder le résumé en base de données"
    #         if st.button("💾 DB", key=db_button_key, help=help_text_db, disabled=not db_enabled):
    #              level = st.session_state.get('summary_level_slider', 'Moyen')
    #              keywords = st.session_state.get('summary_keywords', None)
    #              save_summary_to_db(data_to_export, level, keywords, filename_base)
    #     elif export_type == 'quiz_results':
    #          # Implémenter la logique pour activer/désactiver et sauvegarder les quiz
    #          questions_exist = bool(st.session_state.get(quiz.QUIZ_QUESTIONS_KEY, []))
    #          db_enabled = questions_exist # Activer si des questions existent
    #          help_text_db = "Sauvegarder les résultats du quiz en base de données" if db_enabled else help_text_db
    #          if st.button("💾 DB", key=db_button_key, help=help_text_db, disabled=not db_enabled):
    #              st.warning("Sauvegarde DB des quiz non implémentée.")
    #              # Implémenter save_quiz_results_to_db(...) ici
    #     else:
    #          # Bouton désactivé pour les autres cas
    #          st.button("💾 DB", key=db_button_key, help=help_text_db, disabled=True)

