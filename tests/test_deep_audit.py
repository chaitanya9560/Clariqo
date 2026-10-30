"""Deep audit expectations. Failures document current product defects.
All writes and resets use temporary storage; AI replies are mocked here.
Run alongside test_working_flows; live checks are recorded separately.
"""
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pypdf import PdfReader, PdfWriter
from test_working_flows import WorkingFlows, make_pdf, sample_questions, fake_ai
import config, memory, quiz, rag, study_plan, study_chat, tools

class DeepAudit(unittest.TestCase):
    def setUp(self):
        self.fx=WorkingFlows()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.root=self.fx.root

    def test_counter_survives_thirty_recent_questions(self):
        for n in range(35): memory.add_question(f'Question {n}')
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],35)
        self.assertEqual(len(memory.load_memory()['recent_questions']),30)

    def test_valid_json_with_wrong_shape_does_not_crash(self):
        for payload in [[],None,42,{'quiz_history':None},{'recent_questions':{}}]:
            with self.subTest(payload=payload):
                memory.MEMORY_FILE.write_text(json.dumps(payload))
                summary=memory.get_progress_summary()
                self.assertIsInstance(summary['recent_questions'],list)

    def test_page_count_includes_blank_pages(self):
        src=self.root/'first.pdf'
        make_pdf(src,'Cloud elasticity dynamically scales resources to workload demand.')
        out=self.root/'blank_last.pdf'
        w=PdfWriter(); w.add_page(PdfReader(src).pages[0]); w.add_blank_page(width=612,height=792)
        with out.open('wb') as f: w.write(f)
        result=rag.process_and_index_pdf(out,'blank_last.pdf')
        self.assertEqual(result['total_pages'],2)

    def test_encrypted_pdf_rejected_without_partial_index(self):
        src=self.root/'source.pdf'; make_pdf(src,'Cloud service models include IaaS and PaaS for workloads.')
        w=PdfWriter(); w.add_page(PdfReader(src).pages[0]); w.encrypt('audit-password')
        out=self.root/'locked.pdf'
        with out.open('wb') as f:w.write(f)
        with self.assertRaises(Exception):rag.process_and_index_pdf(out,'locked.pdf')
        self.assertFalse(rag.get_vector_store_status()['is_ready'])

    def test_failed_reindex_keeps_previous_index(self):
        p=self.root/'notes.pdf'; make_pdf(p,'Cloud elasticity dynamically scales resources to workload demand.')
        rag.process_and_index_pdf(p,'notes.pdf')
        before=rag.get_vector_store_status()['total_chunks']
        p.write_bytes(b'broken')
        with self.assertRaises(ValueError):rag.process_and_index_pdf(p,'notes.pdf')
        self.assertEqual(rag.get_vector_store_status()['total_chunks'],before)

    def test_quiz_rejects_identical_options(self):
        qs=sample_questions(); qs[0]['options']={k:'Same answer' for k in 'ABCD'}
        with patch.object(quiz,'generate_text',return_value=json.dumps(qs)):
            with self.assertRaises(RuntimeError):quiz.generate_quiz_questions('Cloud')

    def test_quiz_rejects_null_subtopic_and_explanation(self):
        for field in ['subtopic','explanation']:
            qs=sample_questions(); qs[0][field]=None
            with self.subTest(field=field),patch.object(quiz,'generate_text',return_value=json.dumps(qs)):
                with self.assertRaises(RuntimeError):quiz.generate_quiz_questions('Cloud')

    def test_empty_answers_are_graded_zero_without_crash(self):
        qs=sample_questions()
        for i,q in enumerate(qs,1):q['id']=i
        result=quiz.calculate_quiz_score(qs,{},'Cloud')
        self.assertEqual(result['percentage'],0)
        self.assertEqual(len(result['details']),5)
        self.assertEqual(memory.get_progress_summary()['total_quizzes_taken'],1)

    def test_plan_rejects_past_date(self):
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):
            with self.assertRaises(ValueError):
                study_plan.generate_study_plan('Cloud',str(date.today()-timedelta(days=1)))

    def test_plan_rejects_empty_subject(self):
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):
            with self.assertRaises(ValueError):
                study_plan.generate_study_plan('  ',str(date.today()+timedelta(days=3)))

    def test_plan_rejects_unstructured_or_empty_reply(self):
        for reply in ['', 'Sorry, I cannot create that plan.']:
            with self.subTest(reply=reply),patch.object(study_plan,'generate_text',return_value=reply):
                with self.assertRaises(RuntimeError):
                    study_plan.generate_study_plan('Cloud',str(date.today()+timedelta(days=3)))

    def test_regenerating_plan_resets_checked_days(self):
        at=self.fx.app(); self.fx.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):
            self.fx.button(at,'📅 Generate Study Plan')
            at.checkbox(key='check_day_1').check().run()
            self.assertIn(1,at.session_state.completed_study_days)
            self.fx.button(at,'📅 Generate Study Plan')
        self.assertEqual(at.session_state.completed_study_days,set())
        self.assertFalse(at.checkbox(key='check_day_1').value)

    def test_plan_persists_in_new_session(self):
        at=self.fx.app(); self.fx.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):self.fx.button(at,'📅 Generate Study Plan')
        other=self.fx.app(); self.fx.go(other,'📅 Study Plan')
        self.assertIsNotNone(other.session_state.generated_plan)

    def test_new_chat_session_preserves_conversation(self):
        at=self.fx.app(); self.fx.go(at,'💬 Ask AI')
        with patch.object(study_chat,'reply',return_value={'answer':'Hello','sources':[]}):
            at.chat_input[0].set_value('Hi').run()
        other=self.fx.app(); self.fx.go(other,'💬 Ask AI')
        self.assertEqual(len(other.session_state.chat_history),2)

    def test_quiz_topic_dropdown_scopes_source_document(self):
        for name,text in [('cloud.pdf','Cloud elasticity dynamically scales resources to match workload demand.'),('math.pdf','Integration computes the area enclosed by a mathematical curve.')]:
            p=self.root/name;make_pdf(p,text);rag.process_and_index_pdf(p,name)
        at=self.fx.app();self.fx.go(at,'📝 Quiz')
        next(s for s in at.selectbox if s.label=='Select Topic / Material').set_value('cloud').run()
        with patch.object(rag,'search_study_material',return_value=[]) as search,patch.object(quiz,'generate_text',side_effect=fake_ai):
            self.fx.button(at,'⚡ Generate Quiz')
        self.assertEqual(search.call_args.kwargs.get('file_name'),'cloud.pdf')

    def test_clear_index_clears_quiz_from_deleted_material(self):
        p=self.root/'cloud.pdf';make_pdf(p,'Cloud elasticity dynamically scales computing resources based on workload demand.');rag.process_and_index_pdf(p,'cloud.pdf')
        at=self.fx.app();at.session_state.current_quiz=sample_questions()
        self.fx.go(at,'📚 Study Materials');self.fx.button(at,'🗑️ Clear Vector Index')
        self.assertIsNone(at.session_state.current_quiz)

    def test_no_quizzes_does_not_claim_mastery(self):
        memory.add_question('What is cloud?')
        at=self.fx.app();self.fx.go(at,'📊 My Progress')
        self.assertFalse(any('All Topics Mastered!' in m.value for m in at.markdown))

    def test_chat_error_remains_visible_after_rerun(self):
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        with patch.object(study_chat,'reply',side_effect=RuntimeError('Connection interrupted')):
            at.chat_input[0].set_value('Hi').run()
        self.assertTrue(at.error)
        at.run()
        visible=' '.join(m.value for m in at.markdown)+' '.join(e.value for e in at.error)
        self.assertIn('Connection interrupted',visible)

    def test_chat_study_tools_plan_appears_on_plan_page(self):
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        next(r for r in at.radio if r.label=='Mode').set_value('Study tools').run()
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):
            at.chat_input[0].set_value('Create a study plan for Cloud').run()
        self.fx.clean(at);self.fx.go(at,'📅 Study Plan')
        self.assertIsNotNone(at.session_state.generated_plan)

    def test_tool_router_respects_question_count_and_difficulty(self):
        with patch.object(tools,'generate_quiz',return_value=[]) as generate:
            tools.route_and_execute('Give me a quiz on Cloud with 10 hard questions')
        self.assertEqual(generate.call_args.kwargs['num_questions'],10)
        self.assertEqual(generate.call_args.kwargs['difficulty'],'Hard')

    def test_duplicate_plan_days_do_not_crash_ui(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',return_value='### Day 1: First\n- Read\n### Day 1: Second\n- Practice'):
            next(b for b in at.button if b.label=='📅 Generate Study Plan').click().run()
        self.fx.clean(at)

    def test_capitalized_json_fence_still_routes_conversation(self):
        with patch.object(config,'generate_text',return_value='```JSON\n{"intent":"conversation","query":"Can we talk?"}\n```'):
            result=study_chat.plan_turn('I feel like talking today',[])
        self.assertEqual(result['intent'],'conversation')

    def test_changed_refusal_wording_falls_back_to_internet(self):
        with patch.object(study_chat,'plan_turn',return_value={'intent':'question','query':'Photosynthesis'}),patch.object(rag,'answer_question',return_value={'answer':'The provided pages do not discuss photosynthesis.','sources':[{'file_name':'math.pdf','page':1}]}),patch.object(config,'generate_completion',return_value={'answer':'Verified answer','searched':True,'web_sources':[{'title':'Source','url':'https://example.org'}]}) as web:
            result=study_chat.reply('Photosynthesis')
        self.assertEqual(result['origin'],'web')
        web.assert_called_once()

class UploadAndRenderingAudit(DeepAudit):
    # Only run the additional methods in this class via an explicit suite.
    def test_invalid_replacement_keeps_original_pdf_bytes(self):
        import io
        p=self.root/'cloud.pdf';make_pdf(p,'Cloud elasticity dynamically scales computing resources based on workload demand.')
        original=p.read_bytes();rag.process_and_index_pdf(p,'cloud.pdf')
        upload=io.BytesIO(b'not a PDF');upload.name='cloud.pdf';upload.size=len(upload.getvalue())
        at=self.fx.app()
        with patch('streamlit.file_uploader',return_value=[upload]),patch('time.sleep'):
            self.fx.go(at,'📚 Study Materials');self.fx.button(at,'🚀 Process & Index Materials')
        self.assertEqual(p.read_bytes(),original)

    def test_backend_rejects_oversized_upload_before_writing(self):
        import io
        upload=io.BytesIO(b'%PDF');upload.name='too-large.pdf';upload.size=21*1024*1024
        at=self.fx.app()
        with patch('streamlit.file_uploader',return_value=[upload]):
            self.fx.go(at,'📚 Study Materials');self.fx.button(at,'🚀 Process & Index Materials')
        self.assertFalse((self.root/upload.name).exists())
        self.assertTrue(any('20 MB' in e.value for e in at.error))

    def test_uploaded_filename_cannot_escape_upload_directory(self):
        import io
        uploads=self.root/'uploads';uploads.mkdir()
        upload=io.BytesIO(b'not a PDF');upload.name='../escaped.pdf';upload.size=len(upload.getvalue())
        at=self.fx.app()
        with patch.object(config,'UPLOADS_DIR',uploads),patch('streamlit.file_uploader',return_value=[upload]),patch('time.sleep'):
            self.fx.go(at,'📚 Study Materials');self.fx.button(at,'🚀 Process & Index Materials')
        self.assertFalse((self.root/'escaped.pdf').exists())

    def test_question_text_cannot_inject_html_into_dashboard(self):
        marker='<b data-audit-marker="literal">Hello</b>'
        memory.add_question(marker)
        at=self.fx.app()
        unsafe=[m.value for m in at.markdown if marker in m.value and m.proto.allow_html]
        self.assertEqual(unsafe,[])

    def test_plan_exam_tips_remain_visible(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        at.date_input[0].set_value(date.today()+timedelta(days=1)).run()
        with patch.object(study_plan,'generate_text',return_value='### Day 1: Review\n- Read notes\n### Exam Tips\n1. AUDIT_EXAM_TIP_VISIBLE'):
            self.fx.button(at,'📅 Generate Study Plan')
        self.assertTrue(any('AUDIT_EXAM_TIP_VISIBLE' in m.value for m in at.markdown))

    def test_plan_uses_uploaded_syllabus_context(self):
        p=self.root/'syllabus.pdf';make_pdf(p,'Syllabus unit one: Cloud elasticity. Unit two: resource pooling. Unit three: virtual machines.')
        rag.process_and_index_pdf(p,'syllabus.pdf')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai) as generate:
            study_plan.generate_study_plan('Cloud',str(date.today()+timedelta(days=3)))
        self.assertIn('resource pooling',generate.call_args.args[0].lower())

def load_tests(loader, tests, pattern):
    suite=unittest.TestSuite(loader.loadTestsFromTestCase(DeepAudit))
    suite.addTests(UploadAndRenderingAudit(n) for n in UploadAndRenderingAudit.__dict__ if n.startswith('test_'))
    return suite

if __name__=='__main__':unittest.main(verbosity=2)
