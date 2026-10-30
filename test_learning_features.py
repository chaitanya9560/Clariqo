"""Persistence, syllabus, progress and quiz source checks in isolated storage."""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from unittest.mock import patch
from test_working_flows import make_pdf, fake_ai, sample_questions
import test_working_flows as flow_support
import memory, rag, quiz, study_plan, study_chat, tools

class LearningFeatureTests(unittest.TestCase):
    def setUp(self):
        self.fx=flow_support.WorkingFlows();self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.root=self.fx.root

    def index(self,name,text):
        p=self.root/name;make_pdf(p,text);rag.process_and_index_pdf(p,name)

    def new_plan(self,at):
        self.fx.go(at,'📅 Study Plan')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):self.fx.button(at,'📅 Generate Study Plan')

    def test_chat_with_sources_survives_new_session_and_can_be_cleared(self):
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        result={'answer':'Saved answer','sources':[{'file_name':'notes.pdf','page':2,'score':0.8}], 'origin':'pdf'}
        with patch.object(study_chat,'reply',return_value=result):at.chat_input[0].set_value('Explain this').run()
        self.fx.clean(at)
        other=self.fx.app();self.fx.go(other,'💬 Ask AI')
        self.assertEqual(other.session_state.chat_history[-1]['content'],'Saved answer')
        self.assertEqual(other.session_state.chat_history[-1]['sources'][0]['page'],2)
        self.fx.button(other,'🧹 Clear Chat History')
        again=self.fx.app();self.assertEqual(again.session_state.chat_history,[])
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],1)

    def test_checkbox_completion_survives_new_session(self):
        at=self.fx.app();self.new_plan(at)
        at.checkbox(key='check_day_2').check().run();self.fx.clean(at)
        restored=self.fx.app();self.fx.go(restored,'📅 Study Plan')
        self.assertEqual(restored.session_state.completed_study_days,{2})
        self.assertTrue(restored.checkbox(key='check_day_2').value)
        self.assertFalse(restored.checkbox(key='check_day_1').value)
        restored.checkbox(key='check_day_2').uncheck().run()
        self.assertEqual(memory.load_memory()['completed_study_days'],[])

    def test_regeneration_saves_new_plan_and_resets_completed_days(self):
        at=self.fx.app();self.new_plan(at)
        first=at.session_state.generated_plan['plan_id']
        at.checkbox(key='check_day_1').check().run()
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):self.fx.button(at,'📅 Generate Study Plan')
        saved=memory.load_memory()
        self.assertNotEqual(saved['generated_plan']['plan_id'],first)
        self.assertEqual(saved['completed_study_days'],[])
        restored=self.fx.app();self.fx.go(restored,'📅 Study Plan')
        self.assertFalse(restored.checkbox(key='check_day_1').value)

    def test_old_tab_cannot_change_new_plan_completion(self):
        old=self.fx.app();self.new_plan(old)
        newer=self.fx.app();self.new_plan(newer)
        old.checkbox(key='check_day_1').check().run();self.fx.clean(old)
        self.assertTrue(old.warning)
        self.assertEqual(memory.load_memory()['completed_study_days'],[])

    def test_error_history_survives_refresh_without_becoming_model_context(self):
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        with patch.object(study_chat,'reply',side_effect=RuntimeError('Offline test')):at.chat_input[0].set_value('First attempt').run()
        restored=self.fx.app();self.fx.go(restored,'💬 Ask AI')
        self.assertTrue(any('Offline test' in e.value for e in restored.error))
        with patch.object(study_chat,'reply',return_value={'answer':'Recovered','sources':[]}) as reply:
            restored.chat_input[0].set_value('New attempt').run()
        self.assertEqual(reply.call_args.kwargs['history'],[])
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],2)

    def test_all_chat_modes_count_once(self):
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        with patch.object(study_chat,'reply',return_value={'answer':'Hi','sources':[]}):at.chat_input[0].set_value('Hello').run()
        next(r for r in at.radio if r.label=='Mode').set_value('PDF only').run()
        with patch.object(rag,'answer_question',return_value={'answer':'PDF answer','sources':[]}) as answer:
            at.chat_input[0].set_value('A PDF question').run()
        self.assertFalse(answer.call_args.kwargs['record_question'])
        next(r for r in at.radio if r.label=='Mode').set_value('Study tools').run()
        at.chat_input[0].set_value('Show my progress').run();self.fx.clean(at)
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],3)
        self.assertEqual(len(memory.load_memory()['recent_questions']),3)

    def test_real_rag_call_inside_ui_does_not_double_count(self):
        self.index('cloud.pdf','Cloud elasticity scales resources up and down based on workload demand.')
        at=self.fx.app();self.fx.go(at,'💬 Ask AI')
        next(r for r in at.radio if r.label=='Mode').set_value('PDF only').run()
        with patch.object(rag,'generate_text',return_value='Elasticity scales resources.'):
            at.chat_input[0].set_value('Cloud elasticity?').run()
        self.fx.clean(at)
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],1)

    def test_legacy_memory_migration_keeps_progress_and_adds_counter(self):
        legacy={'topics_studied':['Cloud'],'quiz_history':[],'weak_topics':[], 'recent_questions':[{'question':'One'},{'question':'Two'}]}
        memory.MEMORY_FILE.write_text(json.dumps(legacy))
        for n in range(35):memory.add_question(str(n))
        restored=memory.load_memory()
        self.assertEqual(restored['total_questions_asked'],37)
        self.assertEqual(len(restored['recent_questions']),30)
        self.assertEqual(restored['topics_studied'],['Cloud'])

    def test_atomic_write_failure_preserves_previous_data(self):
        memory.add_question('Keep me')
        before=memory.MEMORY_FILE.read_bytes()
        with patch('memory.os.replace',side_effect=OSError('Disk failure')):
            with self.assertRaises(OSError):memory.add_question('Not committed')
        self.assertEqual(memory.MEMORY_FILE.read_bytes(),before)
        self.assertFalse(list(self.root.glob('.memory-*.tmp')))

    def test_concurrent_question_updates_do_not_get_lost(self):
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(memory.add_question,[f'Question {i}' for i in range(20)]))
        self.assertEqual(memory.get_progress_summary()['total_questions_asked'],20)
        self.assertEqual(len(memory.load_memory()['recent_questions']),20)

    def test_reset_progress_preserves_saved_chat_and_plan(self):
        at=self.fx.app();self.new_plan(at)
        memory.save_chat_history([{'role':'user','content':'Keep this conversation'}])
        memory.add_question('Count this')
        memory.clear_memory()
        data=memory.load_memory()
        self.assertEqual(data['total_questions_asked'],0)
        self.assertEqual(data['chat_history'][0]['content'],'Keep this conversation')
        self.assertIsNotNone(data['generated_plan'])

    def test_accuracy_is_weighted_by_number_of_questions(self):
        memory.add_quiz_result('Cloud',5,5,100)
        memory.add_quiz_result('Math',5,10,50)
        self.assertEqual(memory.get_progress_summary()['average_quiz_score'],66.7)

    def test_plan_uses_only_selected_syllabus_and_records_its_sources(self):
        self.index('syllabus.pdf','Syllabus: resource pooling, cloud elasticity and virtual machines are the three units.')
        self.index('other.pdf','Different subject: integration and the area enclosed by an ellipse.')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai) as generate:
            p=study_plan.generate_study_plan('Cloud',str(date.today()+timedelta(days=3)),file_name='syllabus.pdf')
        prompt=generate.call_args.args[0]
        self.assertIn('resource pooling',prompt)
        self.assertNotIn('area enclosed',prompt)
        self.assertEqual({s['file_name'] for s in p['syllabus_sources']},{'syllabus.pdf'})
        self.assertFalse(p['syllabus_truncated'])

    def test_general_plan_does_not_include_saved_material(self):
        self.index('notes.pdf','Cloud private content: resource pooling and elasticity support workloads.')
        with patch.object(study_plan,'generate_text',side_effect=fake_ai) as generate:
            p=study_plan.generate_study_plan('Cloud',str(date.today()+timedelta(days=3)),use_materials=False)
        self.assertNotIn('private content',generate.call_args.args[0])
        self.assertEqual(p['syllabus_sources'],[])

    def test_long_material_is_marked_partial(self):
        self.index('syllabus.pdf','Cloud syllabus includes resource pooling, elasticity, virtualization and service models.')
        context=rag.get_syllabus_context('syllabus.pdf',max_chars=25)
        self.assertTrue(context['truncated'])
        self.assertEqual(context['sources'][0]['file_name'],'syllabus.pdf')

    def test_plan_page_passes_selected_pdf_and_restores_source_label(self):
        self.index('cloud.pdf','Cloud syllabus: resource pooling and cloud elasticity are key units.')
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        next(s for s in at.selectbox if s.label=='Syllabus / Study PDF').set_value('cloud.pdf').run()
        with patch.object(study_plan,'generate_text',side_effect=fake_ai) as generate:self.fx.button(at,'📅 Generate Study Plan')
        self.assertIn('resource pooling',generate.call_args.args[0])
        restored=self.fx.app();self.fx.go(restored,'📅 Study Plan')
        self.assertTrue(any('Plan sources: cloud.pdf' in c.value for c in restored.caption))

    def test_quiz_dropdown_retrieves_only_chosen_pdf(self):
        self.index('cloud.pdf','Cloud elasticity adjusts resources with demand.')
        self.index('math.pdf','Math integration gives an area under a curve.')
        at=self.fx.app();self.fx.go(at,'📝 Quiz')
        next(s for s in at.selectbox if s.label=='Select Topic / Material').set_value('cloud').run()
        with patch.object(quiz,'generate_text',side_effect=fake_ai) as generate:self.fx.button(at,'⚡ Generate Quiz')
        prompt=generate.call_args.args[0]
        self.assertIn('Cloud elasticity',prompt)
        self.assertNotIn('Math integration',prompt)

    def test_general_quiz_does_not_search_saved_pdfs(self):
        self.index('cloud.pdf','Cloud elasticity adjusts resources with demand.')
        at=self.fx.app();self.fx.go(at,'📝 Quiz')
        next(s for s in at.selectbox if s.label=='Select Topic / Material').set_value('General knowledge / custom topic').run()
        next(t for t in at.text_input if t.label.startswith('Or enter custom')).set_value('Photosynthesis').run()
        with patch.object(rag,'search_study_material') as search,patch.object(quiz,'generate_text',side_effect=fake_ai):self.fx.button(at,'⚡ Generate Quiz')
        search.assert_not_called()

    def test_quiz_rejects_duplicate_questions_and_normalized_options(self):
        qs=sample_questions();qs[1]['question']=qs[0]['question'].upper()
        with patch.object(quiz,'generate_text',return_value=json.dumps(qs)):
            with self.assertRaises(RuntimeError):quiz.generate_quiz_questions('Cloud')
        qs=sample_questions();qs[0]['options']['A']=' Computing   Resources '
        with patch.object(quiz,'generate_text',return_value=json.dumps(qs)):
            with self.assertRaises(RuntimeError):quiz.generate_quiz_questions('Cloud')

    def test_quiz_rejects_extra_list_options_instead_of_dropping_one(self):
        qs=sample_questions();qs[0]['options']=['one','two','three','four','five']
        with patch.object(quiz,'generate_text',return_value=json.dumps(qs)):
            with self.assertRaises(RuntimeError):quiz.generate_quiz_questions('Cloud')

    def test_study_tool_quiz_honors_count_difficulty_and_topic(self):
        with patch.object(tools,'generate_quiz',return_value=[]) as generate:
            tools.route_and_execute('Give me a quiz on Cloud with 10 hard questions')
        self.assertEqual(generate.call_args.kwargs['topic'],'Cloud')
        self.assertEqual(generate.call_args.kwargs['num_questions'],10)
        self.assertEqual(generate.call_args.kwargs['difficulty'],'Hard')

    def test_focus_scores_use_actual_subtopic_answers(self):
        qs=sample_questions()
        for n,q in enumerate(qs,1):q['id']=n
        qs[0]['subtopic']='Service Models'
        quiz.calculate_quiz_score(qs,{1:'A',2:'B',3:'B',4:'B',5:'B'},'Cloud')
        scores=memory.get_progress_summary()['focus_scores']
        self.assertEqual(scores['Service Models'],0)
        self.assertNotIn('Elasticity',scores)

    def test_legacy_weak_area_does_not_get_a_fake_percentage(self):
        memory.add_quiz_result('Cloud',4,5,80,weak_areas=['Service Models'])
        self.assertIsNone(memory.get_progress_summary()['focus_scores']['Service Models'])
        at=self.fx.app();self.fx.go(at,'📊 My Progress')
        self.assertTrue(any('Not assessed' in m.value for m in at.markdown))

    def test_plan_form_restores_saved_settings(self):
        self.index('cloud.pdf','Cloud syllabus includes elasticity, resource pooling and virtualization.')
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        next(s for s in at.selectbox if s.label=='Syllabus / Study PDF').set_value('cloud.pdf').run()
        next(t for t in at.text_input if t.label=='Subject / Course Name').set_value('Cloud Science').run()
        at.date_input[0].set_value(date.today()+timedelta(days=3)).run()
        at.slider[0].set_value(3.0).run()
        next(s for s in at.selectbox if s.label=='Current Knowledge Level').set_value('Advanced').run()
        at.multiselect[0].set_value(['Core Theory']).run()
        with patch.object(study_plan,'generate_text',side_effect=fake_ai):self.fx.button(at,'📅 Generate Study Plan')
        restored=self.fx.app();self.fx.go(restored,'📅 Study Plan')
        self.assertEqual(next(t for t in restored.text_input if t.label=='Subject / Course Name').value,'Cloud Science')
        self.assertEqual(restored.date_input[0].value,date.today()+timedelta(days=3))
        self.assertEqual(restored.slider[0].value,3.0)
        self.assertEqual(next(s for s in restored.selectbox if s.label=='Current Knowledge Level').value,'Advanced')
        self.assertEqual(next(s for s in restored.selectbox if s.label=='Syllabus / Study PDF').value,'cloud.pdf')
        self.assertEqual(restored.multiselect[0].value,['Core Theory'])

if __name__=='__main__':unittest.main(verbosity=2)
