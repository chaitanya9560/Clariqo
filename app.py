"""
Clariqo - Redesigned SaaS Application.
Full-featured, interactive, modern educational AI platform powered by:
- Streamlit
- Configured Groq API with optional legacy Gemini support
- FAISS Vector Store + Sentence Transformers (all-MiniLM-L6-v2)
- Multi-step PDF Ingestion & Semantic Chunking
- Interactive Step-by-Step Quiz Taker & Instant Scoring
- Student Learning Memory & Progress Analytics
- Dynamic Study Plan Generator with Progress Checklist
- Agentic AI Tool Routing & Intent Detection
"""

import time
from datetime import date, timedelta
from pathlib import Path
from html import escape
import streamlit as st

# Configure page metadata & layout
st.set_page_config(
    page_title="Clariqo",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Core imports
import config
import rag
import quiz
import memory
import study_plan
import tools
import study_chat
import study_uploads
import ui_components as ui

# Inject modern SaaS styling
ui.inject_custom_css()

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
PAGES = [
    "🏠 Dashboard",
    "📚 Study Materials",
    "💬 Ask AI",
    "📝 Quiz",
    "📊 My Progress",
    "📅 Study Plan"
]

from workspace import current_workspace

if current_workspace() is not None:
    st.info("Public demo: your PDFs, chat and progress belong to this browser session. "
            "This temporary workspace can reset when the session ends or the server restarts. "
            "Relevant prompts and PDF excerpts are sent to the AI provider when you use AI features.")

saved_learning = memory.load_memory()

if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Dashboard"
if "nav_radio_selection" not in st.session_state:
    st.session_state.nav_radio_selection = "🏠 Dashboard"
if "pending_page" in st.session_state:
    page = st.session_state.pop("pending_page")
    st.session_state.current_page = page
    st.session_state.nav_radio_selection = page
if "chat_history" not in st.session_state:
    st.session_state.chat_history = saved_learning["chat_history"]
if "prefilled_prompt" not in st.session_state:
    st.session_state.prefilled_prompt = ""
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_results" not in st.session_state:
    st.session_state.quiz_results = None
if "quiz_topic" not in st.session_state:
    st.session_state.quiz_topic = ""
if "quiz_current_index" not in st.session_state:
    st.session_state.quiz_current_index = 0
if "quiz_run_id" not in st.session_state:
    st.session_state.quiz_run_id = 0
if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = saved_learning["generated_plan"]
if "completed_study_days" not in st.session_state:
    st.session_state.completed_study_days = set(saved_learning["completed_study_days"])
if "active_material" not in st.session_state:
    st.session_state.active_material = None
if "preview_material" not in st.session_state:
    st.session_state.preview_material = None

def activate_study_plan(plan):
    stored = memory.save_study_plan(plan)
    st.session_state.generated_plan = stored
    st.session_state.completed_study_days = set()
    for key in list(st.session_state):
        if key.startswith('check_day_'):
            del st.session_state[key]


def navigate_to(page_name: str):
    """Safely switches pages and triggers a clean rerun."""
    # Apply widget changes before the sidebar is created on the next run.
    st.session_state.pending_page = page_name
    st.rerun()

def on_nav_change():
    """Callback when sidebar radio selection changes."""
    st.session_state.current_page = st.session_state.nav_radio_selection

# ==============================================================================
# SIDEBAR NAVIGATION & SYSTEM BRANDING
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
        <div style="width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, #4F46E5, #8B5CF6); display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
            🎓
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.1rem; color: #0F172A; line-height: 1.2;">Clariqo</div>
            <div style="font-size: 0.75rem; font-weight: 600; color: #64748B;">AI Education Suite</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Personalized learning with your own materials.")
    st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    st.radio(
        "Navigation",
        PAGES,
        key="nav_radio_selection",
        on_change=on_nav_change,
        label_visibility="collapsed"
    )

    # System Status Snippet in Sidebar
    st.markdown("<hr style='margin: 1.2rem 0 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    v_status = rag.get_vector_store_status()
    st.markdown("""
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem; font-size: 0.82rem;">
        <div style="font-weight: 700; color: #334155; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.4rem;">
            <span style="color: #10B981;">●</span> Vector Store Status
        </div>
        <div style="color: #64748B;">
            Indexed: <strong>{total_chunks}</strong> chunks<br>
            Materials: <strong>{files_count}</strong> file(s)
        </div>
    </div>
    """.format(
        total_chunks=v_status["total_chunks"],
        files_count=len(v_status["indexed_files"])
    ), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; margin-top: 1.5rem; font-size: 0.78rem; color: #94A3B8;">
        <strong>Clariqo</strong><br>
        Powered by {config.AI_PROVIDER_NAME} + RAG
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 1. 🏠 MAIN DASHBOARD (LANDING PAGE)
# ==============================================================================
if st.session_state.current_page == "🏠 Dashboard":
    ui.render_hero_header(
        title="Clariqo",
        subtitle="Your intelligent companion for smarter, personalized learning.",
        badge="Enterprise AI Learning"
    )

    # Prominent AI Status Card
    v_status = rag.get_vector_store_status()
    ui.render_ai_status_card(
        is_ready=v_status["is_ready"],
        model_name=config.AI_MODEL_NAME,
        total_chunks=v_status["total_chunks"],
        total_files=len(v_status["indexed_files"])
    )

    # Statistics / Metric Cards
    progress = memory.get_progress_summary()
    total_materials = len(v_status["indexed_files"])
    total_questions = progress.get("total_questions_asked", 0)
    total_quizzes = progress.get("total_quizzes_taken", 0)
    avg_score = progress.get("average_quiz_score", 0.0)
    weak_count = len(progress.get("weak_topics", []))

    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        ui.render_metric_card(
            icon="📚",
            label="Study Materials",
            value=f"{total_materials}",
            subtext=f"{v_status['total_chunks']} chunks indexed"
        )
    with m_col2:
        ui.render_metric_card(
            icon="💬",
            label="Questions Asked",
            value=f"{total_questions}",
            subtext="Chat and study questions"
        )
    with m_col3:
        ui.render_metric_card(
            icon="📝",
            label="Quizzes Taken",
            value=f"{total_quizzes}",
            subtext="MCQ practice tests"
        )
    with m_col4:
        ui.render_metric_card(
            icon="🎯",
            label="Average Score",
            value=f"{avg_score}%",
            subtext="Across all tests"
        )
    with m_col5:
        ui.render_metric_card(
            icon="⚠️",
            label="Weak Topics",
            value=f"{weak_count}",
            subtext="Requires review" if weak_count > 0 else "No weak areas flagged"
        )

    # Quick Action Section
    st.markdown('<div class="quick-action-header">How can I help you today?</div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)

    with q1:
        st.markdown("""
        <div class="action-card">
            <div>
                <div class="action-title">💬 Ask a Question</div>
                <div class="action-desc">Get instant answers grounded strictly in your uploaded study notes and textbook PDFs.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Asking ➔", key="btn_dash_ask", use_container_width=True):
            navigate_to("💬 Ask AI")

    with q2:
        st.markdown("""
        <div class="action-card">
            <div>
                <div class="action-title">📝 Generate Quiz</div>
                <div class="action-desc">Test your active recall with 5 or 10 AI-generated multiple choice questions with explanations.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Take a Quiz ➔", key="btn_dash_quiz", use_container_width=True):
            navigate_to("📝 Quiz")

    with q3:
        st.markdown("""
        <div class="action-card">
            <div>
                <div class="action-title">📊 View Progress</div>
                <div class="action-desc">Track your score history, mastery progression, and inspect identified weak topic areas.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Analytics ➔", key="btn_dash_prog", use_container_width=True):
            navigate_to("📊 My Progress")

    with q4:
        st.markdown("""
        <div class="action-card">
            <div>
                <div class="action-title">📅 Create Study Plan</div>
                <div class="action-desc">Generate an actionable day-by-day exam preparation schedule with completion tracking.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Create Plan ➔", key="btn_dash_plan", use_container_width=True):
            navigate_to("📅 Study Plan")

    # Recent Activity Snapshot
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.2, 1])

    with c_left:
        st.markdown("#### 🕒 Recent Questions")
        recent_q = progress.get("recent_questions", [])
        if recent_q:
            for item in recent_q[:4]:
                ui.render_recent_question_card(item)
        else:
            ui.render_empty_state("💬", "No questions asked yet", "Ask your first question in the 'Ask AI' section to build your learning history.")

    with c_right:
        st.markdown("#### ⚠️ Focus & Weak Areas")
        weak_topics = progress.get("weak_topics", [])
        if weak_topics:
            for wt in weak_topics[:4]:
                ui.render_weak_topic_bar(wt, progress['focus_scores'].get(wt))
        else:
            st.markdown("""
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:1.4rem; text-align:center;">
                <div style="font-size:1.5rem; margin-bottom:0.4rem;">🎉</div>
                <div style="font-weight:700; color:#166534; font-size:0.95rem;">No Weak Topics Flagged!</div>
                <div style="font-size:0.82rem; color:#15803D; margin-top:0.2rem;">Complete quizzes to identify focus areas and track subject mastery.</div>
            </div>
            """, unsafe_allow_html=True)


# ==============================================================================
# 2. 📚 STUDY MATERIALS PAGE
# ==============================================================================
elif st.session_state.current_page == "📚 Study Materials":
    ui.render_hero_header(
        title="Study Materials",
        subtitle="Upload your notes, textbooks, or study PDFs and let AI learn from them.",
        badge="Document Ingestion & RAG"
    )

    col_up, col_idx = st.columns([1.6, 1.2])

    with col_up:
        st.markdown("#### 📤 Upload Study PDF")
        uploaded_files = st.file_uploader(
            "Upload lecture notes, textbooks, or research PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload college materials, slides, or chapters containing digital selectable text."
        )

        stepper_placeholder = st.empty()

        if uploaded_files:
            st.info(f"📁 {len(uploaded_files)} file(s) selected for processing.")
            process_btn = st.button("🚀 Process & Index Materials", type="primary", use_container_width=True)

            if process_btn:
                for uploaded_file in uploaded_files:
                    if uploaded_file.size > 20 * 1024 * 1024:
                        st.error(f"'{uploaded_file.name}' is too large. The PDF limit is 20 MB per file.")
                        continue
                    # Animated visual progress stepper
                    with st.spinner(f"Indexing '{uploaded_file.name}'..."):
                        stepper_placeholder.markdown(ui.render_stepper(0), unsafe_allow_html=True)
                        time.sleep(0.3)
                        stepper_placeholder.markdown(ui.render_stepper(1), unsafe_allow_html=True)
                        time.sleep(0.3)
                        stepper_placeholder.markdown(ui.render_stepper(2), unsafe_allow_html=True)
                        
                        try:
                            # Real processing
                            stepper_placeholder.markdown(ui.render_stepper(3), unsafe_allow_html=True)
                            result = study_uploads.save_and_index_pdf(uploaded_file)
                            stepper_placeholder.markdown(ui.render_stepper(4), unsafe_allow_html=True)
                            time.sleep(0.2)
                            stepper_placeholder.markdown(ui.render_stepper(5), unsafe_allow_html=True)

                            st.markdown(f"""
                            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:12px; padding:1.2rem; margin:1rem 0;">
                                <div style="color:#065F46; font-weight:800; font-size:1.05rem; display:flex; align-items:center; gap:0.4rem;">
                                    <span>✓</span> Material successfully indexed
                                </div>
                                <div style="color:#047857; font-size:0.88rem; margin-top:0.2rem;">
                                    Your material is searchable. AI answers also require an available AI connection.
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Document summary card
                            st.markdown(f"""
                            <div class="doc-card">
                                <div style="display:flex; align-items:center;">
                                    <div class="doc-icon-wrap">📄</div>
                                    <div>
                                        <div class="doc-name">{escape(result['file_name'])}</div>
                                        <div class="doc-meta">
                                            <span>Pages: <strong>{result['total_pages']}</strong></span>
                                            <span>&bull;</span>
                                            <span>Chunks: <strong>{result['total_chunks']}</strong></span>
                                            <span>&bull;</span>
                                            <span>Indexed Status: <strong>Ready</strong></span>
                                        </div>
                                    </div>
                                </div>
                                <span class="doc-status-badge">✓ Active</span>
                            </div>
                            """, unsafe_allow_html=True)

                        except ValueError as ve:
                            st.error(f"⚠️ {ve}")
                        except Exception as ex:
                            st.error(f"❌ Error indexing '{uploaded_file.name}': {ex}")

        else:
            ui.render_empty_state("📁", "No PDF selected yet", "Drag and drop study PDFs or lecture slides above to extract text and build your semantic index.")

    with col_idx:
        st.markdown("#### 📑 Indexed Materials Library")
        details = rag.get_indexed_files_details()

        if details:
            st.caption("Choose a saved PDF to use it again without uploading it.")
            for doc in details:
                ui.render_document_card(doc)
                filename = doc["file_name"]
                stored_pdf = config.get_uploads_dir() / Path(filename).name
                selected = st.session_state.active_material == filename
                if st.button("Selected PDF ✓" if selected else "Use this PDF", key=f"use_pdf_{filename}", disabled=selected):
                    st.session_state.active_material = filename
                    st.session_state.current_quiz = None
                    st.session_state.quiz_results = None
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_current_index = 0
                    st.session_state.quiz_run_id += 1
                    st.rerun()
                if stored_pdf.is_file():
                    if st.button("Preview PDF", key=f"preview_pdf_{filename}"):
                        st.session_state.preview_material = filename
                        st.rerun()
                    st.download_button("Download PDF", data=stored_pdf.read_bytes(), file_name=Path(filename).name, mime="application/pdf", key=f"download_pdf_{filename}")
                else:
                    st.caption("The original PDF file is missing. Upload it again to enable preview and download.")

            if st.session_state.active_material:
                st.info(f"Selected PDF: {st.session_state.active_material}")
                if st.button("Ask about selected PDF"):
                    navigate_to("💬 Ask AI")
                if st.button("Quiz selected PDF"):
                    navigate_to("📝 Quiz")
                if st.button("Use all saved PDFs"):
                    st.session_state.active_material = None
                    st.rerun()

            preview = st.session_state.preview_material
            if preview:
                preview_path = config.get_uploads_dir() / Path(preview).name
                if preview_path.is_file():
                    st.write(f"Preview: {preview}")
                    try:
                        import pypdfium2 as pdfium
                        with pdfium.PdfDocument(str(preview_path)) as pdf:
                            page_number = st.number_input("PDF page", min_value=1, max_value=len(pdf), value=1, step=1, key=f"preview_page_{preview}")
                            page = pdf[page_number - 1]
                            try:
                                scale = min(1.5, 1200 / max(page.get_size()))
                                bitmap = page.render(scale=scale)
                                try:
                                    st.image(bitmap.to_pil(), use_container_width=True)
                                finally:
                                    bitmap.close()
                            finally:
                                page.close()
                            st.caption(f"Page {page_number} of {len(pdf)}")
                    except Exception:
                        st.warning("This PDF could not be previewed. Use Download PDF to open the original file.")
                    if st.button("Close PDF preview"):
                        st.session_state.preview_material = None
                        st.rerun()

            st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
            if st.button("🗑️ Clear Vector Index", help="Deletes all indexed study chunks to start fresh"):
                rag.clear_vector_store()
                st.session_state.active_material = None
                st.session_state.preview_material = None
                st.session_state.current_quiz = None
                st.session_state.quiz_results = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_current_index = 0
                st.session_state.quiz_run_id += 1
                st.success("Vector store index cleared.")
                st.rerun()
        else:
            ui.render_empty_state("📚", "No study material yet", "Upload a PDF to start learning with AI.")


# ==============================================================================
# 3. 💬 ASK AI PAGE (CHATGPT CONVERSATIONAL RAG & AGENT)
# ==============================================================================
elif st.session_state.current_page == "💬 Ask AI":
    ui.render_hero_header(
        title="Ask AI",
        subtitle="Chat naturally, learn from your PDFs, or find answers on the internet.",
        badge="Conversational Study Assistant"
    )

    if st.session_state.active_material:
        st.info(f"Using saved PDF: {st.session_state.active_material}")

    # Mode Selector Bar
    col_mode, col_clear = st.columns([3, 1])
    with col_mode:
        interaction_mode = st.radio(
            "Mode",
            ["Chat", "PDF only", "Study tools"],
            horizontal=True,
            help="Chat uses your PDFs first, then searches the internet when needed. PDF only stays within uploaded materials. Study tools can create quizzes and plans."
        )
    with col_clear:
        if st.button("🧹 Clear Chat History", use_container_width=True):
            memory.save_chat_history([])
            st.session_state.chat_history = []
            st.session_state.prefilled_prompt = ""
            st.rerun()

    # Suggested Prompts Chips
    st.markdown("<div style='font-size:0.82rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin: 0.5rem 0 0.3rem 0;'>Suggested questions:</div>", unsafe_allow_html=True)
    chip1, chip2, chip3, chip4, chip5 = st.columns(5)
    selected_chip = None

    with chip1:
        if st.button("📌 Topic overview", use_container_width=True):
            selected_chip = "What is this topic about?"
    with chip2:
        if st.button("💡 Simple terms", use_container_width=True):
            selected_chip = "Explain this in simple terms"
    with chip3:
        if st.button("🔍 Give an example", use_container_width=True):
            selected_chip = "Give me an example"
    with chip4:
        if st.button("📑 Summarize chapter", use_container_width=True):
            selected_chip = "Summarize this chapter"
    with chip5:
        if st.button("🎯 Exam points", use_container_width=True):
            selected_chip = "What are the important exam points?"

    # Empty Chat State
    if not st.session_state.chat_history:
        ui.render_empty_state("💬", "Start your study conversation", "Ask any question about your course materials or click a suggested prompt chip above.")

    # Native Markdown rendering supports equations, tables, lists and code safely.
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(ui.normalize_answer_markdown(msg["content"]))
        else:
            with st.chat_message("assistant"):
                if msg.get('error'):
                    st.error(msg['content'])
                    continue
                origin_labels = {"pdf": "From your PDF", "web": "From the internet", "conversation": "Conversation"}
                if msg.get("origin") in origin_labels:
                    st.caption(origin_labels[msg["origin"]])
                st.markdown(ui.normalize_answer_markdown(msg["content"]))
                for source in msg.get("web_sources", []):
                    title = source["title"].replace("[", "").replace("]", "")
                    st.markdown(f"- [{title}](<{source['url']}>)")
                ui.render_source_chips(msg.get("sources", []))

            # Optional RAG Flow Breakdown inside expander
            if msg.get("rag_flow"):
                with st.expander("🔍 How AI Found This Answer", expanded=False):
                    flow = msg["rag_flow"]
                    ui.render_rag_pipeline_flow(
                        query=flow.get("query", ""),
                        chunk_count=flow.get("chunk_count", 0),
                        top_score=flow.get("top_score", 0.0)
                    )

    # Chat Input Box
    chat_input_val = st.chat_input("Ask anything, or continue our conversation...")
    prompt_to_run = selected_chip or chat_input_val or st.session_state.prefilled_prompt
    if selected_chip or st.session_state.prefilled_prompt:
        st.session_state.prefilled_prompt = ""

    if prompt_to_run:
        if not config.is_ai_configured():
            st.error(f"{config.AI_PROVIDER_NAME} API key is missing. Add it in the project .env file, then restart the website.")
            st.stop()

        # Preserve earlier messages before appending the current question.
        prior_history = [m for m in st.session_state.chat_history if not m.get("failed") and not m.get("error")][-6:]
        st.session_state.chat_history.append({"role": "user", "content": prompt_to_run})

        # Process with AI
        with st.spinner("AI Agent understanding your request & analyzing materials..."):
            try:
                topic = Path(st.session_state.active_material).stem if st.session_state.active_material else 'General Study'
                memory.add_question(prompt_to_run, topic=topic)
                memory.save_chat_history(st.session_state.chat_history)
                if interaction_mode == "Study tools" and tools.analyze_intent(prompt_to_run) != "search_study_material":
                    agent_res = tools.route_and_execute(prompt_to_run, file_name=st.session_state.active_material)
                    tool_selected = agent_res.get("tool_selected", "search_study_material")
                    resp_text = agent_res.get("response", "")
                    sources = agent_res.get("sources", [])
                    if tool_selected == "generate_quiz":
                        st.session_state.current_quiz = agent_res["tool_output"]
                        st.session_state.quiz_topic = agent_res["tool_input"]["topic"]
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_results = None
                        st.session_state.quiz_current_index = 0
                        st.session_state.quiz_run_id += 1

                    if tool_selected == 'create_study_plan':
                        activate_study_plan(agent_res['tool_output'])

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": resp_text,
                        "tool": tool_selected,
                        "sources": sources,
                        "rag_flow": {
                            "query": prompt_to_run,
                            "chunk_count": len(sources),
                            "top_score": sources[0]["score"] if sources else 0.0
                        } if sources else None
                    })

                else:
                    if interaction_mode == "PDF only":
                        rag_res = rag.answer_question(prompt_to_run, file_name=st.session_state.active_material, history=prior_history, record_question=False)
                        rag_res["origin"] = "pdf"
                    else:
                        rag_res = study_chat.reply(prompt_to_run, history=prior_history, file_name=st.session_state.active_material, record_question=False)
                    resp_text = rag_res.get("answer", "")
                    sources = rag_res.get("sources", [])

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": resp_text,
                        "sources": sources,
                        "web_sources": rag_res.get("web_sources", []),
                        "origin": rag_res.get("origin"),
                        "rag_flow": {
                            "query": prompt_to_run,
                            "chunk_count": len(sources),
                            "top_score": sources[0]["score"] if sources else 0.0
                        } if sources else None
                    })

                memory.save_chat_history(st.session_state.chat_history)
                st.rerun()

            except Exception as err:
                st.session_state.chat_history[-1]['failed'] = True
                message = f"Could not complete this request: {err}"
                st.session_state.chat_history.append({'role': 'assistant', 'content': message, 'error': True})
                try:
                    memory.save_chat_history(st.session_state.chat_history)
                except OSError:
                    st.warning('Chat could not be saved. Check available disk space and file access.')
                st.error(message)


# ==============================================================================
# 4. 📝 QUIZ PAGE (INTERACTIVE STEP-BY-STEP QUIZ TAKER)
# ==============================================================================
elif st.session_state.current_page == "📝 Quiz":
    ui.render_hero_header(
        title="AI Quiz Generator",
        subtitle="Test your knowledge with AI-generated questions.",
        badge="Active Recall Testing"
    )

    mem_data = memory.load_memory()
    material_files = sorted({d['file_name'] for d in rag.get_indexed_files_details()})
    material_labels = {}
    for name in material_files:
        label = Path(name).stem.replace('_', ' ')
        if label in material_labels:
            previous = material_labels.pop(label)
            material_labels[previous] = previous
            label = name
        material_labels[label] = name
    if st.session_state.active_material and st.session_state.active_material not in material_files:
        st.session_state.active_material = None
    if st.session_state.active_material:
        material_labels = {label: name for label, name in material_labels.items() if name == st.session_state.active_material}
        available_topics = list(material_labels)
    elif material_labels:
        available_topics = list(material_labels) + ['General knowledge / custom topic']
    else:
        available_topics = ['Cloud Computing', 'Computer Networks', 'Database Systems']

    # Quiz Setup Controls
    with st.expander("⚙️ Quiz Controls", expanded=(st.session_state.current_quiz is None and st.session_state.quiz_results is None)):
        qc1, qc2, qc3 = st.columns([2, 1, 1])
        with qc1:
            quiz_topic = st.selectbox("Select Topic / Material", options=available_topics, index=0)
            custom_topic = st.text_input("Or enter custom topic (optional):", placeholder="e.g., Virtualization, Normalization")
            active_topic = custom_topic.strip() if custom_topic.strip() else quiz_topic
            quiz_file = material_labels.get(quiz_topic)
            st.caption(f'Quiz source: {quiz_file}' if quiz_file else 'Quiz source: general knowledge')
        with qc2:
            num_q = st.selectbox("Number of Questions", [5, 10], index=0)
        with qc3:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)

        gen_quiz_btn = st.button("⚡ Generate Quiz", type="primary", use_container_width=True)

    if gen_quiz_btn:
        if not config.is_ai_configured():
            st.error(f"{config.AI_PROVIDER_NAME} API key is missing. Add it in the project .env file, then restart the website.")
        else:
            with st.spinner(f"Generating your quiz on '{active_topic}'..."):
                try:
                    if quiz_topic == 'General knowledge / custom topic' and not custom_topic.strip():
                        raise ValueError('Enter a topic for a general-knowledge quiz.')
                    context_chunks = rag.search_study_material(active_topic, top_k=3, file_name=quiz_file) if quiz_file else []
                    if quiz_file and not context_chunks:
                        raise ValueError('No text was found for the selected PDF. Select another material or upload it again.')
                    context_str = "\n\n".join([c["text"] for c in context_chunks]) if context_chunks else ""
                    
                    questions = quiz.generate_quiz_questions(
                        topic=active_topic,
                        num_questions=num_q,
                        difficulty=difficulty,
                        context=context_str
                    )
                    st.session_state.current_quiz = questions
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_results = None
                    st.session_state.quiz_topic = active_topic
                    st.session_state.quiz_current_index = 0
                    st.session_state.quiz_run_id += 1
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error generating quiz: {ex}")

    # Display Quiz Results Screen
    if st.session_state.quiz_results:
        res = st.session_state.quiz_results
        ui.render_performance_card(
            score=res["score"],
            total=res["total"],
            percentage=res["percentage"]
        )

        # Action Buttons
        ra1, ra2 = st.columns(2)
        with ra1:
            if st.button("🔄 Retry Quiz", use_container_width=True):
                st.session_state.quiz_run_id += 1
                st.session_state.quiz_answers = {}
                st.session_state.quiz_results = None
                st.session_state.quiz_current_index = 0
                st.rerun()
        with ra2:
            if res.get("weak_areas"):
                weak_target = res["weak_areas"][0]
                if st.button(f"📖 Study Weak Topics ({weak_target})", type="primary", use_container_width=True):
                    st.session_state.prefilled_prompt = f"Help me understand and master this weak area: {weak_target}"
                    navigate_to("💬 Ask AI")
            else:
                if st.button("📅 Generate Study Plan for Exam", type="primary", use_container_width=True):
                    navigate_to("📅 Study Plan")

        # Detailed Question Review
        st.markdown("#### 📋 Detailed Question Review")
        for item in res["details"]:
            ui.render_question_review_card(item)

    # Interactive Step-by-Step Question Taker (One Question at a Time)
    elif st.session_state.current_quiz:
        questions = st.session_state.current_quiz
        total_q = len(questions)
        curr_idx = st.session_state.quiz_current_index
        q = questions[curr_idx]

        # Header Progress Bar
        st.markdown(f"""
        <div class="quiz-header-bar">
            <span class="quiz-q-counter">Question {curr_idx + 1} of {total_q}</span>
            <span class="quiz-subtopic-tag">Topic: {escape(q.get('subtopic', st.session_state.quiz_topic))}</span>
        </div>
        """, unsafe_allow_html=True)
        st.progress((curr_idx + 1) / total_q)

        # Question Content Card
        st.markdown(f"""
        <div class="quiz-box">
            <div class="quiz-question-text">{q['id']}. {escape(q['question'])}</div>
        </div>
        """, unsafe_allow_html=True)

        # Options Radio
        options_list = [f"{k}. {v}" for k, v in q["options"].items()]
        prev_ans = st.session_state.quiz_answers.get(q["id"], None)
        selected_index = None
        if prev_ans:
            for idx_opt, opt_str in enumerate(options_list):
                if opt_str.startswith(prev_ans):
                    selected_index = idx_opt
                    break

        user_choice = st.radio(
            "Options",
            options_list,
            index=selected_index,
            key=f"radio_quiz_q_{st.session_state.quiz_run_id}_{q['id']}",
            label_visibility="collapsed"
        )

        if user_choice:
            st.session_state.quiz_answers[q["id"]] = user_choice[0]

        # Navigation Controls (Previous, Jump Pills, Next / Submit)
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        nav_prev_col, nav_pills_col, nav_next_col = st.columns([1, 2, 1])

        with nav_prev_col:
            if curr_idx > 0:
                if st.button("⬅ Previous", use_container_width=True):
                    st.session_state.quiz_current_index -= 1
                    st.rerun()

        with nav_pills_col:
            # Question selector dots
            pill_cols = st.columns(total_q)
            for p_idx in range(total_q):
                is_answered = questions[p_idx]["id"] in st.session_state.quiz_answers
                is_active = (p_idx == curr_idx)
                label = f"{p_idx + 1}{'✓' if is_answered else ''}"
                with pill_cols[p_idx]:
                    if st.button(label, key=f"btn_jump_{p_idx}", type="primary" if is_active else "secondary", use_container_width=True):
                        st.session_state.quiz_current_index = p_idx
                        st.rerun()

        with nav_next_col:
            if curr_idx < total_q - 1:
                if st.button("Next ➡", type="primary", use_container_width=True):
                    st.session_state.quiz_current_index += 1
                    st.rerun()
            else:
                if st.button("📊 Submit Quiz", type="primary", use_container_width=True):
                    with st.spinner("Analyzing your performance & grading answers..."):
                        results = quiz.calculate_quiz_score(
                            questions=st.session_state.current_quiz,
                            user_answers=st.session_state.quiz_answers,
                            topic=st.session_state.quiz_topic
                        )
                        st.session_state.quiz_results = results
                        st.rerun()

    else:
        # Empty State
        ui.render_empty_state("📝", "No quizzes completed yet", "Generate your first quiz above to track your knowledge retention and identify weak topics.")


# ==============================================================================
# 5. 📊 MY PROGRESS PAGE (ANALYTICS & MEMORY)
# ==============================================================================
elif st.session_state.current_page == "📊 My Progress":
    ui.render_hero_header(
        title="My Learning Progress",
        subtitle="Track your mastery, quiz score trends, and weak topic progress over time.",
        badge="Performance Intelligence"
    )

    summary = memory.get_progress_summary()
    total_q = summary.get("total_questions_asked", 0)
    total_quizzes = summary.get("total_quizzes_taken", 0)
    avg_score = summary.get("average_quiz_score", 0.0)
    topics_studied = summary.get("topics_studied", [])
    quiz_history = summary.get("quiz_history", [])
    weak_topics = summary.get("weak_topics", [])

    # Overview Cards
    pm1, pm2, pm3, pm4 = st.columns(4)
    with pm1:
        ui.render_metric_card("💬", "Total Questions", total_q, "Chat messages submitted")
    with pm2:
        ui.render_metric_card("📝", "Quizzes Completed", total_quizzes, "Knowledge evaluations")
    with pm3:
        ui.render_metric_card("🎯", "Average Score", f"{avg_score}%", "Overall correct answers")
    with pm4:
        ui.render_metric_card("📚", "Topics Recorded", len(topics_studied), "Materials and quiz topics")

    if total_quizzes == 0 and total_q == 0:
        ui.render_empty_state("📊", "No learning activity yet.", "Complete a quiz or ask some questions to start tracking your progress.")
    else:
        st.markdown("<div style='margin-top: 1.8rem;'></div>", unsafe_allow_html=True)
        col_charts, col_weak = st.columns([1.4, 1])

        with col_charts:
            st.markdown("#### 📈 Quiz Score Trend")
            if quiz_history:
                # Reverse so earliest is first
                timeline_scores = [q.get("percentage", 0.0) for q in reversed(quiz_history)]
                chart_data = {"Score (%)": timeline_scores}
                st.line_chart(chart_data)
            else:
                st.info("Take quizzes in the 'Quiz' section to plot your score progression.")

            st.markdown("#### 📚 Topics Studied")
            if topics_studied:
                pill_htmls = [f'<span class="source-badge" style="background:#EEF2FF; color:#4F46E5; font-size:0.85rem; padding:0.35rem 0.8rem;">📘 {escape(t)}</span>' for t in topics_studied]
                st.markdown(f'<div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:1.5rem;">{" ".join(pill_htmls)}</div>', unsafe_allow_html=True)
            else:
                st.caption("No topics recorded yet.")

        with col_weak:
            st.markdown("#### ⚠️ Focus & Weak Topics")
            if weak_topics:
                # Calculate scores for weak topics
                for wt in weak_topics:
                    # Find score in history if available
                    ui.render_weak_topic_bar(wt, summary['focus_scores'].get(wt))
            else:
                st.markdown("""
                <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:12px; padding:1.2rem; text-align:center;">
                    <div style="font-size:1.4rem;">🎉</div>
                    <div style="font-weight:700; color:#065F46;">No weak areas flagged</div>
                    <div style="font-size:0.82rem; color:#047857; margin-top:0.2rem;">Complete quizzes to assess your knowledge. A lack of flagged areas does not mean every topic is mastered.</div>
                </div>
                """, unsafe_allow_html=True)

            # Recent Inquiries Log
            st.markdown("#### 🕒 Recent Questions")
            recent_q = summary.get("recent_questions", [])
            if recent_q:
                for rq in recent_q[:5]:
                    st.markdown(f"- 💬 *\"{rq['question']}\"* ({rq.get('topic', 'General')})")
            else:
                st.caption("No questions asked yet.")

        # Learning Memory Expansion
        st.markdown("<hr style='margin: 2rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        with st.expander("🧠 Learning Memory Management", expanded=False):
            st.markdown("Your chat, study plan, completed days and progress are saved on this computer.")
            c_mem1, c_mem2 = st.columns([3, 1])
            with c_mem1:
                st.json(summary)
            with c_mem2:
                if st.button("🗑️ Reset Learning Memory", help="Clears stored questions, quiz history, and weak topics"):
                    memory.clear_memory()
                    st.success("Student memory has been reset.")
                    st.rerun()


# ==============================================================================
# 6. 📅 STUDY PLAN PAGE (INTERACTIVE TIMELINE & PROGRESS CHECKLIST)
# ==============================================================================
elif st.session_state.current_page == "📅 Study Plan":
    ui.render_hero_header(
        title="Personalized Study Plan",
        subtitle="Build an AI-powered study schedule based on your goals and performance.",
        badge="Personalized Exam Roadmap"
    )

    mem_data = memory.load_memory()
    existing_plan = st.session_state.generated_plan or {}
    default_sub = existing_plan.get('subject') or (mem_data["topics_studied"][-1] if mem_data["topics_studied"] else "Cloud Computing")

    syllabus_files = sorted({d['file_name'] for d in rag.get_indexed_files_details()})
    syllabus_options = (['All saved PDFs', 'General plan (no PDF)'] + syllabus_files) if syllabus_files else ['General plan (no PDF)']
    initial_source = st.session_state.active_material if st.session_state.active_material in syllabus_files else syllabus_options[0]
    if existing_plan and not st.session_state.active_material:
        if existing_plan.get('use_materials') is False:
            initial_source = 'General plan (no PDF)'
        elif existing_plan.get('syllabus_file') in syllabus_files:
            initial_source = existing_plan['syllabus_file']
        else:
            source_names = {s['file_name'] for s in existing_plan.get('syllabus_sources', [])}
            if len(source_names) == 1 and next(iter(source_names)) in syllabus_files:
                initial_source = next(iter(source_names))
    syllabus_choice = st.selectbox('Syllabus / Study PDF', syllabus_options, index=syllabus_options.index(initial_source))
    syllabus_file = syllabus_choice if syllabus_choice in syllabus_files else None

    # Input Form
    with st.container():
        sp_col1, sp_col2 = st.columns([1, 1])

        with sp_col1:
            subject = st.text_input("Subject / Course Name", value=default_sub)
            try:
                default_date = max(date.today(), date.fromisoformat(existing_plan['exam_date']))
            except (KeyError, ValueError, TypeError):
                default_date = date.today() + timedelta(days=7)
            exam_date = st.date_input("Target Exam Date", value=default_date, min_value=date.today())
            default_hours = min(8.0, max(1.0, float(existing_plan.get('daily_hours', 2.5))))
            daily_hours = st.slider("Daily Study Hours Available", min_value=1.0, max_value=8.0, value=default_hours, step=0.5)

        with sp_col2:
            levels = ['Beginner', 'Intermediate', 'Advanced']
            previous_level = existing_plan.get('knowledge_level', 'Intermediate')
            knowledge_level = st.selectbox("Current Knowledge Level", levels, index=levels.index(previous_level) if previous_level in levels else 1)
            suggested_weak = mem_data.get("weak_topics", [])
            default_weak = existing_plan.get('weak_topics', suggested_weak)
            selected_weak = st.multiselect(
                "Priority Focus Areas / Weak Topics",
                options=sorted(set(suggested_weak + default_weak + ["Core Theory", "Exam Review"])),
                default=default_weak
            )

        gen_plan_btn = st.button("📅 Generate Study Plan", type="primary", use_container_width=True)

    if gen_plan_btn:
        if not config.is_ai_configured():
            st.error(f"{config.AI_PROVIDER_NAME} API key is missing. Add it in the project .env file, then restart the website.")
        else:
            with st.spinner(f"Creating your personalized study plan for '{subject}'..."):
                try:
                    plan = study_plan.generate_study_plan(
                        subject=subject,
                        exam_date=str(exam_date),
                        daily_hours=daily_hours,
                        knowledge_level=knowledge_level,
                        weak_topics=selected_weak,
                        file_name=syllabus_file,
                        use_materials=syllabus_choice != 'General plan (no PDF)',
                    )
                    activate_study_plan(plan)
                    st.success("Study plan successfully generated!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error generating plan: {ex}")

    # Display Plan Timeline
    if st.session_state.generated_plan:
        plan = st.session_state.generated_plan
        try:
            days_structured = study_plan.parse_study_plan_to_days(plan["plan_markdown"], plan.get("weak_topics", []))
        except ValueError as err:
            st.error(f"This study plan cannot be displayed: {err}")
            st.stop()
        total_days = len(days_structured)
        valid_days = {d['day_number'] for d in days_structured}
        st.session_state.completed_study_days &= valid_days
        completed_count = len(st.session_state.completed_study_days)
        if plan.get('syllabus_sources'):
            st.caption('Plan sources: ' + ', '.join(sorted({s['file_name'] for s in plan['syllabus_sources']})))
        else:
            st.caption('General study plan; no uploaded syllabus was used.')
        if plan.get('syllabus_truncated'):
            st.info('This plan used partial extracts from longer materials. Select a shorter syllabus PDF for more focused coverage.')

        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown(f"### 📋 {plan['subject']} Study Roadmap")

        # Plan Summary Metrics
        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            ui.render_metric_card("📅", "Days Remaining", f"{study_plan.calculate_days_remaining(plan['exam_date'])} days", f"Target: {plan['exam_date']}")
        with sm2:
            ui.render_metric_card("⏱️", "Daily Commitment", f"{plan['daily_hours']} hrs", f"Target level: {plan['knowledge_level']}")
        with sm3:
            ui.render_metric_card("🎯", "Schedule Plan", f"{total_days} Days", "High-retention sprints")
        with sm4:
            ui.render_metric_card("✓", "Plan Completed", f"{completed_count} / {total_days}", f"{int(completed_count / total_days * 100) if total_days > 0 else 0}% completed")

        # Completion Progress Bar
        if total_days > 0:
            st.progress(completed_count / total_days)

        st.markdown("#### 🗓️ Day-by-Day Timeline")

        for day in days_structured:
            d_num = day["day_number"]
            is_done = d_num in st.session_state.completed_study_days
            ui.render_timeline_day_card_header(
                day_number=d_num,
                title=day['title'],
                is_completed=is_done,
                is_weak=day.get("is_weak_topic", False),
                weak_label=day.get("weak_topic_label")
            )

            # Keep tables, numbered tasks and exam tips as well as bullet lists.
            st.markdown(ui.normalize_answer_markdown(day.get("content", "")))

            # Interactive completion checkbox
            checked = st.checkbox(
                f"Mark Day {d_num} as Completed",
                value=is_done,
                key=f"check_day_{d_num}"
            )
            if checked != is_done:
                next_days = set(st.session_state.completed_study_days)
                if checked:
                    next_days.add(d_num)
                else:
                    next_days.discard(d_num)
                try:
                    memory.save_completed_study_days(next_days, plan.get('plan_id'))
                except ValueError as err:
                    st.warning(str(err))
                    st.stop()
                st.session_state.completed_study_days = next_days
                st.rerun()

            st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

        # Download / Export Button
        st.download_button(
            label="📥 Download Study Plan (.md)",
            data=plan["plan_markdown"],
            file_name=f"Study_Plan_{plan['subject'].replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    else:
        ui.render_empty_state("📅", "No study plan yet", "Create a personalized plan based on your exam date and weak topics.")
