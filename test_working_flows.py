"""Regression tests with temporary data and clearly mocked AI responses.
Run: .venv/bin/python test_working_flows.py
These tests do not establish live Gemini availability or answer quality.
"""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date, timedelta
import numpy as np
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from streamlit.testing.v1 import AppTest
import config, memory, quiz, rag, study_plan, tools, study_chat


def make_pdf(path, text=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream.set_data(f'BT /F1 12 Tf 40 740 Td ({escaped}) Tj ET'.encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    with open(path, 'wb') as f:
        writer.write(f)


def sample_questions(n=5):
    return [{"question": f"Cloud elasticity question {i+1}: what changes with demand?", "options": {"A": "Building paint", "B": "Computing resources", "C": "Keyboard color", "D": "Exam dates"}, "correct_answer": "B", "explanation": "Elasticity adjusts computing resources to demand.", "subtopic": "Elasticity"} for i in range(n)]


def fake_ai(prompt, system_instruction=None, **kwargs):
    match = re.search(r'Generate exactly (\d+)', prompt)
    if match:
        return json.dumps(sample_questions(int(match.group(1))))
    if 'day-by-day study plan' in prompt:
        count = int(re.search(r'upcoming (\d+) days', prompt).group(1))
        return '\n'.join(f'### Day {i}: ' + ('Elasticity' if i == 2 else 'Cloud fundamentals') + '\n- Read notes and practise' for i in range(1, count + 1))
    return 'Cloud elasticity adjusts computing resources to demand.'


class FixtureEmbedder:
    def encode(self, texts, **kwargs):
        return np.array([[1.0, 0.0] if any(w in t.lower() for w in ['cloud', 'elastic', 'virtual']) else [0.0, 1.0] for t in texts], dtype=np.float32)


class WorkingFlows(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index_dir = self.root / 'index'
        self.index_dir.mkdir()
        self.patches = [
            patch.object(config, 'is_ai_configured', return_value=True),
            patch.object(memory, 'MEMORY_FILE', self.root / 'memory.json'),
            patch.object(rag, 'VECTOR_STORE_DIR', self.index_dir),
            patch.object(rag, 'FAISS_INDEX_FILE', self.index_dir / 'index.faiss'),
            patch.object(rag, 'METADATA_FILE', self.index_dir / 'chunks_metadata.json'),
            patch.object(rag, '_FAISS_INDEX', None),
            patch.object(rag, '_CHUNKS_METADATA', []),
            patch.object(rag, 'get_embedding_model', return_value=FixtureEmbedder()),
            patch.object(config, 'UPLOADS_DIR', self.root),
        ]
        for p in self.patches: p.start()
        self.addCleanup(self.temp.cleanup)
        for p in self.patches: self.addCleanup(p.stop)

    def app(self):
        at = AppTest.from_file('app.py', default_timeout=30).run()
        self.clean(at)
        return at

    def clean(self, at):
        self.assertFalse(at.exception, [e.message for e in at.exception])

    def go(self, at, page):
        at.radio(key='nav_radio_selection').set_value(page).run()
        self.clean(at)
        self.assertEqual(at.session_state.current_page, page)

    def button(self, at, label):
        button = next(b for b in at.button if b.label == label)
        button.click().run()
        self.clean(at)

    def test_dashboard_shortcuts_and_all_sidebar_pages(self):
        targets = {'btn_dash_ask':'💬 Ask AI', 'btn_dash_quiz':'📝 Quiz', 'btn_dash_prog':'📊 My Progress', 'btn_dash_plan':'📅 Study Plan'}
        for key, target in targets.items():
            with self.subTest(shortcut=key):
                at = self.app()
                at.button(key=key).click().run()
                self.clean(at)
                self.assertEqual(at.session_state.current_page, target)
                self.assertEqual(at.radio(key='nav_radio_selection').value, target)
        at = self.app()
        for page in ['📚 Study Materials','💬 Ask AI','📝 Quiz','📊 My Progress','📅 Study Plan','🏠 Dashboard']:
            self.go(at, page)

    def test_pdf_extraction_index_search_reload_clear_and_invalid_files(self):
        pdf = self.root / 'lecture.pdf'
        make_pdf(pdf, 'Cloud elasticity dynamically scales computing resources to match workload demand. Virtualization lets multiple virtual machines share hardware.')
        result = rag.process_and_index_pdf(pdf, 'lecture.pdf')
        self.assertGreater(result['total_chunks'], 0)
        results = rag.search_study_material('What is cloud elasticity?')
        self.assertIn('elasticity', results[0]['text'])
        self.assertEqual(results[0]['page'], 1)
        rag._FAISS_INDEX = None
        rag._CHUNKS_METADATA = []
        self.assertTrue(rag.get_vector_store_status()['is_ready'])
        self.assertEqual(rag.get_indexed_files_details()[0]['file_name'], 'lecture.pdf')
        rag.clear_vector_store()
        self.assertFalse(rag.get_vector_store_status()['is_ready'])
        blank = self.root / 'scan.pdf'
        make_pdf(blank)
        with self.assertRaisesRegex(ValueError, 'no extractable text'):
            rag.extract_text_from_pdf(blank)
        bad = self.root / 'broken.pdf'
        bad.write_bytes(b'not a pdf')
        with self.assertRaises(ValueError): rag.extract_text_from_pdf(bad)
        with self.assertRaises(FileNotFoundError): rag.extract_text_from_pdf(self.root / 'missing.pdf')

    def test_pdf_reindex_does_not_duplicate(self):
        pdf = self.root/'lecture.pdf'
        make_pdf(pdf, 'Cloud elasticity scales computing resources dynamically as workloads change.')
        rag.process_and_index_pdf(pdf, 'lecture.pdf')
        before = rag.get_vector_store_status()['total_chunks']
        rag.process_and_index_pdf(pdf, 'lecture.pdf')
        self.assertEqual(rag.get_vector_store_status()['total_chunks'], before)

    def test_rag_answer_sources_missing_material_and_unrelated_question(self):
        self.assertIn('No study materials', rag.answer_question('Cloud?')['answer'])
        pdf = self.root/'lecture.pdf'
        make_pdf(pdf, 'Cloud elasticity dynamically scales computing resources to match workload demand.')
        rag.process_and_index_pdf(pdf, 'lecture.pdf')
        with patch.object(rag, 'generate_text', side_effect=fake_ai):
            result = rag.answer_question('Explain cloud elasticity')
        self.assertIn('resources', result['answer'])
        self.assertEqual(result['sources'][0]['file_name'], 'lecture.pdf')
        self.assertEqual(len(memory.load_memory()['recent_questions']), 1)
        self.assertIn("couldn't find", rag.answer_question('Bananas?')['answer'])

    def test_quiz_generation_validation_and_api_failure(self):
        with patch.object(quiz, 'generate_text', side_effect=fake_ai):
            self.assertEqual(len(quiz.generate_quiz_questions('Cloud',5)),5)
            self.assertEqual(len(quiz.generate_quiz_questions('Cloud',10)),10)
        invalid = sample_questions()
        invalid[0]['correct_answer'] = 'INVALID'
        for payload in ['not json', json.dumps(sample_questions(1)), json.dumps(invalid)]:
            with self.subTest(payload=payload[:20]), patch.object(quiz,'generate_text',return_value=payload):
                with self.assertRaises(RuntimeError): quiz.generate_quiz_questions('Cloud')
        with patch.object(quiz,'generate_text',side_effect=RuntimeError('Free tier unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'Free tier unavailable'): quiz.generate_quiz_questions('Cloud')

    def test_quiz_actual_controls_scoring_retry_progress_and_results_navigation(self):
        at = self.app()
        self.go(at,'📝 Quiz')
        with patch.object(quiz,'generate_text',side_effect=fake_ai): self.button(at,'⚡ Generate Quiz')
        run_id = at.session_state.quiz_run_id
        for i in range(1,6):
            radio = at.radio(key=f'radio_quiz_q_{run_id}_{i}')
            radio.set_value('B. Computing resources' if i<5 else 'A. Building paint').run()
            self.clean(at)
            if i<5: self.button(at,'Next ➡')
        self.button(at,'⬅ Previous')
        self.assertEqual(at.radio(key=f'radio_quiz_q_{run_id}_4').value,'B. Computing resources')
        self.button(at,'Next ➡')
        self.button(at,'📊 Submit Quiz')
        self.assertEqual(at.session_state.quiz_results['percentage'],80)
        self.assertEqual(len(memory.load_memory()['quiz_history']),1)
        self.button(at,'🔄 Retry Quiz')
        self.assertIsNone(at.radio(key=f'radio_quiz_q_{run_id+1}_1').value)
        self.go(at,'📊 My Progress')
        self.assertEqual(memory.get_progress_summary()['total_quizzes_taken'],1)

    def test_weak_topic_recovery_and_memory_reset(self):
        with patch.object(quiz,'generate_text',side_effect=fake_ai): questions=quiz.generate_quiz_questions('Cloud')
        quiz.calculate_quiz_score(questions,{q['id']:'A' for q in questions},'Cloud')
        self.assertIn('Elasticity',memory.load_memory()['weak_topics'])
        quiz.calculate_quiz_score(questions,{q['id']:'B' for q in questions},'Cloud')
        self.assertNotIn('Elasticity',memory.load_memory()['weak_topics'])
        at=self.app()
        self.go(at,'📊 My Progress')
        self.button(at,'🗑️ Reset Learning Memory')
        self.assertEqual(memory.get_progress_summary()['total_quizzes_taken'],0)

    def test_chat_submission_and_clear(self):
        at=self.app()
        self.go(at,'💬 Ask AI')
        with patch.object(study_chat,'reply',return_value={'answer':'Test response','sources':[]}):
            at.chat_input[0].set_value('Explain cloud elasticity').run()
        self.clean(at)
        self.assertEqual(at.session_state.chat_history[-1]['content'],'Test response')
        self.button(at,'🧹 Clear Chat History')
        self.assertEqual(at.session_state.chat_history,[])

    def test_chat_agent_quiz_transfers_to_quiz_screen(self):
        at=self.app()
        self.go(at,'💬 Ask AI')
        next(r for r in at.radio if r.label=='Mode').set_value('Study tools').run()
        with patch.object(quiz,'generate_text',side_effect=fake_ai):
            at.chat_input[0].set_value('Give me a quiz on Cloud').run()
        self.clean(at)
        self.assertEqual(len(at.session_state.current_quiz),5)
        self.go(at,'📝 Quiz')
        self.assertTrue(any(r.label=='Options' for r in at.radio))

    def test_api_errors_visible_without_fake_success(self):
        at=self.app()
        self.go(at,'📝 Quiz')
        with patch.object(quiz,'generate_text',side_effect=RuntimeError('Free tier unavailable')):
            self.button(at,'⚡ Generate Quiz')
        self.assertIsNone(at.session_state.current_quiz)
        self.assertTrue(any('Free tier unavailable' in e.value for e in at.error))
        self.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',side_effect=RuntimeError('Free tier unavailable')):
            self.button(at,'📅 Generate Study Plan')
        self.assertIsNone(at.session_state.generated_plan)
        self.assertTrue(any('Free tier unavailable' in e.value for e in at.error))

    def test_plan_generate_complete_uncomplete_regenerate(self):
        at=self.app()
        self.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai): self.button(at,'📅 Generate Study Plan')
        self.assertEqual(len(at.checkbox),7)
        at.checkbox(key='check_day_1').check().run()
        self.clean(at)
        self.assertEqual(at.session_state.completed_study_days,{1})
        at.checkbox(key='check_day_1').uncheck().run()
        self.assertEqual(at.session_state.completed_study_days,set())
        at.checkbox(key='check_day_1').check().run()
        with patch.object(study_plan,'generate_text',side_effect=fake_ai): self.button(at,'📅 Generate Study Plan')
        self.assertEqual(at.session_state.completed_study_days,set())
        self.assertFalse(at.checkbox(key='check_day_1').value)

    def test_router_plan_uses_future_date(self):
        with patch.object(study_plan,'generate_text',side_effect=fake_ai): result=tools.route_and_execute('create a study plan')
        self.assertEqual(result['tool_output']['exam_date'],(date.today()+timedelta(days=7)).isoformat())

    def test_missing_key_blocks_ai_without_crashing(self):
        at=self.app()
        with patch.object(config,'is_ai_configured',return_value=False):
            self.go(at,'📝 Quiz')
            self.button(at,'⚡ Generate Quiz')
            self.assertTrue(at.error)
            self.go(at,'📅 Study Plan')
            self.button(at,'📅 Generate Study Plan')
            self.assertTrue(at.error)
            self.go(at,'💬 Ask AI')
            at.chat_input[0].set_value('Explain elasticity').run()
            self.clean(at)
            self.assertTrue(at.error)
            self.assertEqual(at.session_state.chat_history,[])

    def test_quiz_results_buttons_navigate(self):
        for perfect in [True,False]:
            with self.subTest(perfect=perfect):
                at=self.app()
                self.go(at,'📝 Quiz')
                with patch.object(quiz,'generate_text',side_effect=fake_ai): questions=quiz.generate_quiz_questions('Cloud')
                at.session_state.current_quiz=questions
                at.session_state.quiz_results=quiz.calculate_quiz_score(questions,{q['id']:'B' if perfect else 'A' for q in questions},'Cloud')
                at.run()
                self.clean(at)
                if perfect:
                    self.button(at,'📅 Generate Study Plan for Exam')
                    self.assertEqual(at.session_state.current_page,'📅 Study Plan')
                else:
                    with patch.object(study_chat,'reply',return_value={'answer':'Test remediation','sources':[]}):
                        self.button(at,'📖 Study Weak Topics (Elasticity)')
                    self.assertEqual(at.session_state.current_page,'💬 Ask AI')

    def test_replacing_pdf_preserves_other_materials(self):
        a=self.root/'a.pdf'
        b=self.root/'b.pdf'
        make_pdf(a,'Cloud elasticity scales computing resources dynamically with demand.')
        make_pdf(b,'Bananas and apples are fruit. Fruit can be used in a balanced diet.')
        rag.process_and_index_pdf(a,'a.pdf')
        rag.process_and_index_pdf(b,'b.pdf')
        make_pdf(a,'Cloud virtualization lets multiple virtual machines share the same hardware.')
        rag.process_and_index_pdf(a,'a.pdf')
        self.assertEqual(set(rag.get_vector_store_status()['indexed_files']),{'a.pdf','b.pdf'})
        self.assertEqual(rag.get_vector_store_status()['total_chunks'],2)
        self.assertIn('virtualization',rag.search_study_material('cloud')[0]['text'])

    def test_upload_progress_returns_displayable_html(self):
        import ui_components
        self.assertIn('Ready',ui_components.render_stepper(5))

    def test_saved_pdf_selection_preview_and_reuse(self):
        pdf=self.root/'saved.pdf'
        make_pdf(pdf,'Cloud elasticity scales computing resources dynamically with demand.')
        rag.process_and_index_pdf(pdf,'saved.pdf')
        at=self.app()
        self.go(at,'📚 Study Materials')
        at.session_state.current_quiz=[{'id':99}]
        at.button(key='use_pdf_saved.pdf').click().run()
        self.clean(at)
        self.assertEqual(at.session_state.active_material,'saved.pdf')
        self.assertIsNone(at.session_state.current_quiz)
        at.button(key='preview_pdf_saved.pdf').click().run()
        self.clean(at)
        self.assertTrue(at.get('imgs'))
        self.assertTrue(any('Page 1 of 1' in c.value for c in at.caption))
        self.assertTrue(at.get('download_button'))
        self.button(at,'Close PDF preview')
        self.button(at,'Ask about selected PDF')
        with patch.object(study_chat,'reply',return_value={'answer':'Selected document reply','sources':[]}) as answer:
            at.chat_input[0].set_value('Explain elasticity').run()
            self.clean(at)
        answer.assert_called_once_with('Explain elasticity',history=[],file_name='saved.pdf',record_question=False)
        self.go(at,'📝 Quiz')
        self.assertEqual(at.selectbox[0].options,['saved'])
        self.go(at,'📚 Study Materials')
        self.button(at,'Use all saved PDFs')
        self.assertIsNone(at.session_state.active_material)

    def test_search_is_restricted_to_selected_pdf(self):
        for name,text in [('cloud.pdf','Cloud elasticity scales computing resources dynamically with demand.'),('fruit.pdf','Bananas and apples are fruit. Fruit is part of a balanced diet.')]:
            path=self.root/name
            make_pdf(path,text)
            rag.process_and_index_pdf(path,name)
        matches=rag.search_study_material('cloud elasticity',top_k=1,file_name='fruit.pdf')
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]['file_name'],'fruit.pdf')
        self.assertEqual(rag.search_study_material('cloud',file_name='missing.pdf'),[])

    def test_upload_limit_and_minimal_toolbar_config(self):
        from streamlit import config as streamlit_config
        self.assertEqual(streamlit_config.get_option('server.maxUploadSize'),20)
        self.assertEqual(streamlit_config.get_option('client.toolbarMode'),'minimal')

    def test_worked_example_context_excludes_nearby_exercises(self):
        chunks=[
            {'file_name':'math.pdf','page':4,'chunk_id':1,'text':'Circle conclusion.\nExample 2 Find the area enclosed by the ellipse\nSolution: use four quadrants.'},
            {'file_name':'math.pdf','page':4,'chunk_id':2,'text':'Integrate the vertical strips to obtain pi a b.'},
            {'file_name':'math.pdf','page':5,'chunk_id':3,'text':'Alternatively use horizontal strips.\nEXERCISE 8.1\nUse numbers 116 and 9.'},
        ]
        matches=[dict(chunks[2],score=0.9),dict(chunks[0],score=0.7)]
        with patch.object(rag,'_CHUNKS_METADATA',chunks),patch.object(rag,'search_study_material',return_value=matches):
            context=rag.retrieve_answer_context('Find the area enclosed by the ellipse',file_name='math.pdf')
        combined='\n'.join(c['text'] for c in context)
        self.assertTrue(combined.startswith('Example 2'))
        self.assertIn('Integrate the vertical strips',combined)
        self.assertIn('horizontal strips',combined)
        self.assertNotIn('EXERCISE',combined)
        self.assertNotIn('116',combined)
        self.assertNotIn('Circle',combined)

    def test_math_delimiters_preserve_tables_existing_math_and_code(self):
        import ui_components as ui
        raw=r'Inline \(x^2\). Display \[\frac{x^2}{a^2}=1\]. Code `\(keep\)` and $y^2$.'
        output=ui.normalize_answer_markdown(raw)
        self.assertIn('$x^2$',output)
        self.assertIn('$$\n'+r'\frac{x^2}{a^2}=1'+'\n$$',output)
        self.assertIn(r'`\(keep\)`',output)
        self.assertIn('$y^2$',output)
        code='```latex\n'+r'\[keep\]'+'\n```'
        self.assertEqual(ui.normalize_answer_markdown(code),code)

    def test_chat_renders_markdown_math_without_html_wrapping(self):
        at=self.app()
        self.go(at,'💬 Ask AI')
        at.session_state.chat_history=[{'role':'assistant','content':r'Area: \[A=\pi ab\]','sources':[]}]
        at.run()
        self.clean(at)
        self.assertTrue(at.get('chat_message'))
        rendered=[m.value for m in at.markdown if r'A=\pi ab' in m.value]
        self.assertEqual(len(rendered),1)
        self.assertIn('$$',rendered[0])
        self.assertNotIn('<div>',rendered[0])

class ConversationTests(unittest.TestCase):
    def test_normal_chat_requests_do_not_reach_pdf_or_web(self):
        for question in ['Hello! Can we chat normally?', 'Can you talk with me?', "Let's just chat", 'I want to chat with you']:
            with self.subTest(question=question), patch.object(config,'generate_text',return_value='Of course!') as generate, patch.object(rag,'answer_question') as pdf, patch.object(config,'generate_completion') as web:
                result=study_chat.reply(question)
                self.assertEqual(result['origin'],'conversation')
                generate.assert_called_once()
                pdf.assert_not_called()
                web.assert_not_called()

    def test_greeting_with_subject_question_still_uses_router(self):
        with patch.object(config,'generate_text',return_value=json.dumps({'intent':'question','query':'Hello, what is integration?'})) as generate:
            result=study_chat.plan_turn('Hello, what is integration?', [])
        generate.assert_called_once()
        self.assertEqual(result['intent'],'question')

    def test_greeting_uses_history_without_pdf_or_search(self):
        history=[{'role':'user','content':'My name is Chaitanya'}]
        with patch.object(config,'generate_text',return_value='Hi Chaitanya!') as generate,patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion') as web:
            result=study_chat.reply('hello',history=history)
        self.assertEqual(result['origin'],'conversation')
        self.assertEqual(generate.call_args.kwargs['history'],history)
        pdf.assert_not_called()
        web.assert_not_called()

    def test_followup_resolves_subject_and_preserves_pdf_scope(self):
        history=[{'role':'user','content':'What is integration?'},{'role':'assistant','content':'Integration accumulates quantities.'}]
        plan={'intent':'question','query':'Explain integration more simply'}
        with patch.object(config,'generate_text',return_value=json.dumps(plan)),patch.object(rag,'answer_question',return_value={'answer':'Simpler explanation','sources':[{'file_name':'math.pdf','page':1}]}) as pdf,patch.object(config,'generate_completion') as web:
            result=study_chat.reply('explain it more simply',history=history,file_name='math.pdf')
        self.assertEqual(result['origin'],'pdf')
        pdf.assert_called_once_with('Explain integration more simply',file_name='math.pdf',history=history)
        web.assert_not_called()

    def test_outside_pdf_searches_without_uploading_pdf_or_history(self):
        history=[{'role':'assistant','content':'Private PDF excerpt'}]
        with patch.object(study_chat,'plan_turn',return_value={'intent':'question','query':'What is photosynthesis?'}),patch.object(rag,'answer_question',return_value={'answer':"I couldn't find this information in the uploaded study material.",'sources':[]}),patch.object(config,'generate_completion',return_value={'answer':'Plants use light.','searched':True,'web_sources':[{'title':'Source','url':'https://example.org/photosynthesis'}]}) as web:
            result=study_chat.reply('What is photosynthesis?',history=history)
        self.assertEqual(result['origin'],'web')
        self.assertNotIn('history',web.call_args.kwargs)
        self.assertNotIn('Private PDF excerpt',str(web.call_args))
        self.assertTrue(web.call_args.kwargs['web_search'])

    def test_current_question_bypasses_pdf_and_search_failure_is_honest(self):
        with patch.object(study_chat,'plan_turn',return_value={'intent':'web','query':'Latest science news'}),patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion',return_value={'answer':'Unverified text','searched':False,'web_sources':[]}):
            result=study_chat.reply('Latest science news')
        pdf.assert_not_called()
        self.assertEqual(result['origin'],'error')
        self.assertNotIn('Unverified text',result['answer'])

    def test_standalone_question_is_not_rewritten(self):
        with patch.object(config,'generate_text',return_value=json.dumps({'intent':'question','query':'Changed question'})):
            result=study_chat.plan_turn('Find the area enclosed by the ellipse',[])
        self.assertEqual(result['query'],'Find the area enclosed by the ellipse')

class GroqConnectionTests(unittest.TestCase):
    def setUp(self):
        self.provider=patch.object(config,'AI_PROVIDER','groq')
        self.provider.start()
        self.addCleanup(self.provider.stop)
        self.env=patch.dict('os.environ',{'GROQ_API_KEY':'test-private-key'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self,status=200,payload=None):
        from unittest.mock import Mock
        r=Mock(status_code=status,ok=200<=status<300)
        r.json.return_value=payload if payload is not None else {'choices':[{'message':{'content':'Working'},'finish_reason':'stop'}]}
        return r

    def test_success_uses_groq_only_and_system_prompt(self):
        with patch('requests.post',return_value=self.response()) as post, patch.object(config,'generate_gemini_text',side_effect=AssertionError('Unexpected Google call')):
            self.assertEqual(config.generate_text('Hello','Be concise'),'Working')
            args=post.call_args
            self.assertEqual(args.args[0],'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(args.kwargs['json']['messages'][0],{'role':'system','content':'Be concise'})
            self.assertEqual(post.call_count,1)

    def test_missing_key_does_not_send_request(self):
        with patch.dict('os.environ',{'GROQ_API_KEY':'paste_your_groq_key_here'}),patch('requests.post') as post:
            self.assertFalse(config.is_ai_configured())
            with self.assertRaisesRegex(ValueError,'GROQ_API_KEY'): config.generate_text('Hello')
            post.assert_not_called()

    def test_auth_limits_and_service_errors(self):
        for status,message in [(401,'rejected'),(403,'rejected'),(429,'usage limit'),(503,'temporarily unavailable')]:
            with self.subTest(status=status),patch('requests.post',return_value=self.response(status)):
                with self.assertRaisesRegex(RuntimeError,message): config.generate_text('Hello')

    def test_timeout_truncation_and_empty_reply(self):
        import requests
        with patch('requests.post',side_effect=requests.Timeout):
            with self.assertRaisesRegex(RuntimeError,'too long'): config.generate_text('Hello')
        for content,finish,message in [('', 'stop','empty'),('Partial','length','cut short')]:
            r=self.response(payload={'choices':[{'message':{'content':content},'finish_reason':finish}]})
            with self.subTest(finish=finish),patch('requests.post',return_value=r):
                with self.assertRaisesRegex(RuntimeError,message): config.generate_text('Hello')

    def test_search_executes_and_returns_real_source_links(self):
        payload={'choices':[{'finish_reason':'stop','message':{'content':'Verified fact【1†L0-L2】','executed_tools':[{'name':'browser.search','type':'browser_search','index':1,'search_results':{'results':[{'title':'Official source','url':'https://example.org/fact'},{'title':'Bad','url':'javascript:alert(1)'}]}}]}}]}
        with patch('requests.post',return_value=self.response(payload=payload)) as post:
            result=config.generate_completion('Find fact',web_search=True)
        self.assertTrue(result['searched'])
        self.assertEqual(len(result['web_sources']),1)
        self.assertIn('[source](<https://example.org/fact>)',result['answer'])
        self.assertNotIn('【',result['answer'])
        self.assertEqual(post.call_args.kwargs['json']['tool_choice'],'auto')

    def test_search_without_tool_execution_is_not_claimed_as_verified(self):
        with patch('requests.post',return_value=self.response()) as post:
            result=config.generate_completion('Find fact',web_search=True)
        self.assertEqual(post.call_args.kwargs['json']['tool_choice'],'auto')
        self.assertFalse(result['searched'])
        self.assertEqual(result['web_sources'],[])

    def test_error_messages_do_not_expose_key(self):
        r=self.response(400,{'error':{'message':'Rejected test-private-key'}})
        with patch('requests.post',return_value=r):
            with self.assertRaises(RuntimeError) as caught: config.generate_text('Hello')
        self.assertNotIn('test-private-key',str(caught.exception))

if __name__=='__main__': unittest.main(verbosity=2)
