"""Additional damaged-data and clean-checkout checks before Git publication."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from test_working_flows import make_pdf
import test_working_flows as flow_support
import memory, rag

class ReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.fx=flow_support.WorkingFlows();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.root=self.fx.root

    def index(self):
        p=self.root/'cloud.pdf';make_pdf(p,'Cloud elasticity scales computing resources up and down with workload demand.')
        rag.process_and_index_pdf(p,'cloud.pdf')

    def test_damaged_saved_web_sources_do_not_crash_chat(self):
        for sources in [None,[{}],[{'title':None,'url':'javascript:bad'}]]:
            with self.subTest(sources=sources):
                data=memory._fresh_default_memory();data['chat_history']=[{'role':'assistant','content':'Keep this answer','web_sources':sources}]
                memory.MEMORY_FILE.write_text(json.dumps(data))
                at=self.fx.app();self.fx.go(at,'💬 Ask AI')
                self.assertTrue(any('Keep this answer' in m.value for m in at.markdown))

    def test_damaged_saved_plan_fields_do_not_crash_plan_page(self):
        plan={'subject':'Cloud','exam_date':'2026-11-02','days_remaining':3,'daily_hours':2.0,'knowledge_level':'Intermediate','plan_markdown':'### Day 1: Study\n- Read notes'}
        for key,value in [('daily_hours','bad'),('weak_topics',None),('syllabus_sources',None),('subject',42)]:
            with self.subTest(key=key):
                damaged=dict(plan);damaged[key]=value
                data=memory._fresh_default_memory();data['generated_plan']=damaged
                memory.MEMORY_FILE.write_text(json.dumps(data))
                at=self.fx.app();self.fx.go(at,'📅 Study Plan')

    def test_nonfinite_saved_plan_recovers_without_losing_questions(self):
        data=memory._fresh_default_memory();data['recent_questions']=[{'question':'Keep this question'}]
        data['generated_plan']={'subject':'Cloud','exam_date':'2026-11-02','days_remaining':3,'daily_hours':float('nan'),'knowledge_level':'Intermediate','plan_markdown':'### Day 1: Study\n- Read'}
        memory.MEMORY_FILE.write_text(json.dumps(data))
        restored=memory.load_memory()
        self.assertEqual(restored['recent_questions'][0]['question'],'Keep this question')
        self.assertIsNone(restored['generated_plan'])

    def test_invalid_vector_metadata_is_not_reported_ready(self):
        self.index()
        original=rag.METADATA_FILE.read_text()
        for content in ['null','[]',json.dumps([{'text':'missing fields'}]),original[:-1]+','+original[1:]]:
            with self.subTest(content=content[:30]):
                rag.METADATA_FILE.write_text(content);rag._FAISS_INDEX=None;rag._CHUNKS_METADATA=[]
                self.assertFalse(rag.get_vector_store_status()['is_ready'])
                self.assertEqual(rag.search_study_material('Cloud'),[])

    def test_changed_embedding_dimension_has_actionable_error(self):
        self.index()
        wrong=type('WrongDimension',(),{'encode':lambda self,*a,**k:np.array([[1.,0.,0.]],dtype=np.float32)})()
        with patch.object(rag,'get_embedding_model',return_value=wrong):
            with self.assertRaisesRegex(ValueError,'[Rr]e.*index|[Ii]ndex.*again'):
                rag.search_study_material('Cloud')

    def test_zero_requested_results_is_empty_even_with_pdf_scope(self):
        self.index()
        self.assertEqual(rag.search_study_material('Cloud',top_k=0,file_name='cloud.pdf'),[])

    def test_git_excludes_private_runtime_and_generated_data(self):
        project=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git','init','-q',tmp],check=True,capture_output=True)
            paths=['.env','data/memory.json','data/memory.before-saved-chat-and-plans.json','data/memory.json.invalid-abcd','uploads/book.pdf','test_results/deep-live.json','.runtime/python/bin/python','.model-cache/model.bin']
            cmd=['git',f'--git-dir={tmp}/.git',f'--work-tree={project}','check-ignore','--no-index','--stdin']
            result=subprocess.run(cmd,input='\n'.join(paths)+'\n',text=True,capture_output=True)
            self.assertEqual(set(result.stdout.splitlines()),set(paths))
            self.assertTrue((project/'tests/fixtures/three_day_plan.md').is_file())

    def test_invalid_chunk_settings_are_rejected_and_high_overlap_makes_progress(self):
        pages=[{'page':1,'text':('Cloud elasticity and service models. '*20)+'ENDTOKEN'}]
        for size,overlap in [(0,0),(100,100),(100,-1),(100,101)]:
            with self.subTest(size=size,overlap=overlap):
                with self.assertRaises(ValueError):rag.chunk_text(pages,'notes.pdf',size,overlap)
        chunks=rag.chunk_text(pages,'notes.pdf',100,90)
        self.assertLess(len(chunks),100)
        self.assertIn('ENDTOKEN',chunks[-1]['text'])

if __name__=='__main__':unittest.main(verbosity=2)
