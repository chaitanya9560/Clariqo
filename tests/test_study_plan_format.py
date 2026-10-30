"""Study plan parsing and timeline checks using recorded and synthetic AI replies."""
import json
import unittest
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch
import study_plan

import test_working_flows as flow_support

class PlanFormatTests(unittest.TestCase):
    def setUp(self):
        self.fx=flow_support.WorkingFlows();self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)

    def recorded(self):
        return (Path(__file__).resolve().parent / 'fixtures/three_day_plan.md').read_text()

    def test_actual_failed_reply_parses_into_three_days(self):
        days=study_plan.parse_study_plan_to_days(self.recorded(),['Elasticity'])
        self.assertEqual([d['day_number'] for d in days],[1,2,3])
        self.assertTrue(days[0]['is_weak_topic'])
        self.assertIn('High',days[-1]['content'])

    def test_supported_heading_formats_preserve_tasks(self):
        for header in ['### Day 1: Foundations','## ### Day\u202f1 –\u202fFoundations','### 📚 Day 1 — Foundations','**Day 1: Foundations**','Day 1 - Foundations','# Day 1','### Day 1: **Foundations**']:
            with self.subTest(header=header):
                days=study_plan.parse_study_plan_to_days(header+'\n- Read\n### Day 2: Practice\n- Solve')
                self.assertEqual([d['day_number'] for d in days],[1,2])
                self.assertEqual(days[0]['content'],'- Read')
                self.assertEqual(days[1]['content'],'- Solve')

    def test_code_examples_do_not_create_checkboxes(self):
        plan='### Day 1: Read\n- Study\n```markdown\n### Day 99: Example only\n```\n### Day 2: Practice\n- Solve'
        self.assertEqual(len(study_plan.parse_study_plan_to_days(plan)),2)
        self.assertIn('Day 99',study_plan.parse_study_plan_to_days(plan)[0]['content'])
        self.assertEqual(len(study_plan.parse_study_plan_to_days('```markdown\n'+plan+'\n```')),2)

    def test_repeated_skipped_and_out_of_order_days_rejected(self):
        for numbers in [(1,1),(1,3),(2,1),(0,1)]:
            with self.subTest(numbers=numbers):
                text='\n'.join(f'### Day {n}: Tasks\n- Study' for n in numbers)
                with self.assertRaises(ValueError):study_plan.parse_study_plan_to_days(text)

    def test_generation_rejects_wrong_count_or_missing_tasks(self):
        for reply in ['### Day 1: Review\n- Read', '### Day 1: Read\n### Day 2: Practice\n- Solve\n### Day 3: Exam\n- Test','Sorry, no plan is available.','']:
            with self.subTest(reply=reply),patch.object(study_plan,'generate_text',return_value=reply):
                with self.assertRaises(RuntimeError):
                    study_plan.generate_study_plan('Cloud',str(date.today()+timedelta(days=3)))

    def test_recorded_reply_creates_three_independent_checkboxes(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        at.date_input[0].set_value(date.today()+timedelta(days=3)).run()
        with patch.object(study_plan,'generate_text',return_value=self.recorded()):
            self.fx.button(at,'📅 Generate Study Plan')
        self.assertEqual(len(at.checkbox),3)
        at.checkbox(key='check_day_2').check().run();self.fx.clean(at)
        self.assertEqual(at.session_state.completed_study_days,{2})
        self.assertFalse(at.checkbox(key='check_day_1').value)
        self.assertFalse(at.checkbox(key='check_day_3').value)
        at.checkbox(key='check_day_2').uncheck().run();self.fx.clean(at)
        self.assertEqual(at.session_state.completed_study_days,set())

    def test_invalid_reply_keeps_existing_valid_plan(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        at.date_input[0].set_value(date.today()+timedelta(days=3)).run()
        with patch.object(study_plan,'generate_text',return_value=self.recorded()):self.fx.button(at,'📅 Generate Study Plan')
        previous=at.session_state.generated_plan
        with patch.object(study_plan,'generate_text',return_value='### Day 1: A\n- Read\n### Day 1: B\n- Practise'):
            self.fx.button(at,'📅 Generate Study Plan')
        self.assertTrue(at.error)
        self.assertEqual(at.session_state.generated_plan,previous)
        self.assertEqual(len(at.checkbox),3)

    def test_old_invalid_session_plan_shows_error_without_crash(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        at.session_state.generated_plan={'plan_markdown':'### Day 1: A\n- Read\n### Day 1: B\n- Practise'}
        at.run();self.fx.clean(at)
        self.assertTrue(at.error)
        self.assertEqual(len(at.checkbox),0)

    def test_day_tables_and_exam_tips_are_visible(self):
        at=self.fx.app();self.fx.go(at,'📅 Study Plan')
        at.date_input[0].set_value(date.today()+timedelta(days=1)).run()
        text='### Day 1: Review\n- Read notes\n\n| Task | Minutes |\n| --- | --- |\n| Practice | 30 |\n\n### Exam Tips\n1. AUDIT_EXAM_TIP_VISIBLE'
        with patch.object(study_plan,'generate_text',return_value=text):self.fx.button(at,'📅 Generate Study Plan')
        self.assertTrue(any('AUDIT_EXAM_TIP_VISIBLE' in m.value for m in at.markdown))
        self.assertTrue(any('| Practice | 30 |' in m.value for m in at.markdown))

if __name__=='__main__':unittest.main(verbosity=2)
