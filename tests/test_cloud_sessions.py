"""Visitor isolation across overlapping requests, reruns and storage failures."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import config, memory, rag, study_uploads
from workspace import Workspace, current_workspace, use_workspace
from test_working_flows import make_pdf, FixtureEmbedder


class CloudSessionTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = Workspace(), Workspace()
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)
        p=patch.object(rag, 'get_embedding_model', return_value=FixtureEmbedder())
        p.start();self.addCleanup(p.stop)

    def upload(self, text, name='notes.pdf'):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/name;make_pdf(path,text)
            upload=BytesIO(path.read_bytes());upload.name=name;upload.size=len(upload.getbuffer())
            return study_uploads.save_and_index_pdf(upload)

    def test_concurrent_visitors_have_separate_files_vectors_and_learning(self):
        barrier=threading.Barrier(2)
        def visitor(ws, label):
            with use_workspace(ws):
                self.upload(f'Cloud elasticity and computing resources. {label} private study notes.')
                memory.save_chat_history([{'role':'user','content':label}])
                memory.add_question(label)
                barrier.wait(timeout=15)
                return (config.get_uploads_dir(),memory.load_memory()['chat_history'],
                        rag.search_study_material('cloud')[0]['text'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(visitor,self.a,'ALPHA');b=pool.submit(visitor,self.b,'BETA')
            one,two=a.result(timeout=30),b.result(timeout=30)
        self.assertNotEqual(one[0],two[0])
        self.assertEqual(one[1][0]['content'],'ALPHA');self.assertEqual(two[1][0]['content'],'BETA')
        self.assertNotIn('BETA',one[2]);self.assertNotIn('ALPHA',two[2])
        self.assertIsNot(self.a.vectors.index,self.b.vectors.index)

    def test_clear_and_failed_replace_never_touch_another_visitor(self):
        for ws,label in [(self.a,'ALPHA'),(self.b,'BETA')]:
            with use_workspace(ws):self.upload('Cloud computing elasticity and resource management. '+label)
        before=(self.b.uploads/'notes.pdf').read_bytes()
        with use_workspace(self.a):
            with patch.object(rag,'get_embedding_model',side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):self.upload('Cloud replacement text with sufficient characters for indexing.')
            self.assertIn('ALPHA',rag.get_vector_state().metadata[0]['text'])
            rag.clear_vector_store();memory.clear_memory()
        with use_workspace(self.b):
            self.assertEqual(rag.get_vector_store_status()['indexed_files'],['notes.pdf'])
            self.assertEqual((self.b.uploads/'notes.pdf').read_bytes(),before)
            self.assertIn('BETA',rag.search_study_material('cloud')[0]['text'])

    def test_context_reset_on_error_and_nested_context(self):
        self.assertIsNone(current_workspace())
        with use_workspace(self.a):
            try:
                with use_workspace(self.b):raise RuntimeError('test')
            except RuntimeError:pass
            self.assertIs(current_workspace(),self.a)
        self.assertIsNone(current_workspace())

    def test_disk_reload_is_scoped_to_current_session(self):
        with use_workspace(self.a):
            self.upload('Cloud computing elasticity and flexible resources for computing workloads.')
            self.a.vectors.index=None;self.a.vectors.metadata=[]
            self.assertEqual(rag.get_vector_store_status()['indexed_files'],['notes.pdf'])
        with use_workspace(self.b):
            self.assertFalse(rag.get_vector_store_status()['is_ready'])
            self.assertEqual(memory.load_memory()['recent_questions'],[])

    def test_cloud_entrypoint_rerun_preserves_session_and_new_browser_starts_empty(self):
        one=AppTest.from_file('cloud/app.py',default_timeout=30).run()
        self.assertFalse(one.exception,[x.message for x in one.exception])
        ws=one.session_state['_private_workspace']
        self.addCleanup(ws.close)
        with use_workspace(ws):memory.add_question('Only visitor A')
        one.run();self.assertFalse(one.exception)
        self.assertEqual(one.session_state['_private_workspace'].root,ws.root)
        two=AppTest.from_file('cloud/app.py',default_timeout=30).run()
        self.assertFalse(two.exception,[x.message for x in two.exception])
        other=two.session_state['_private_workspace'];self.addCleanup(other.close)
        self.assertNotEqual(ws.root,other.root)
        with use_workspace(other):self.assertEqual(memory.load_memory()['recent_questions'],[])
        self.assertTrue(any('Public demo:' in x.value for x in two.info))

    def test_public_pdf_count_limit_and_existing_replacement(self):
        with use_workspace(self.a):
            for i in range(5):self.upload('Cloud computing elasticity and resource management concepts.',f'notes{i}.pdf')
            with self.assertRaisesRegex(ValueError,'5 PDFs'):
                self.upload('Cloud computing text sufficient for semantic indexing.','sixth.pdf')
            self.upload('Cloud replacement with enough text to build a search index.','notes0.pdf')
            self.assertEqual(len(rag.get_indexed_files_details()),5)

    def test_closed_workspace_removes_temporary_files(self):
        root=self.a.root
        with use_workspace(self.a):memory.add_question('Private data')
        self.a.close()
        self.assertFalse(root.exists())

    def test_session_ai_quota_expires_without_affecting_other_visitors(self):
        from workspace import reserve_ai_request
        with patch('workspace.time.monotonic',return_value=1000):
            with use_workspace(self.a):
                for _ in range(60):reserve_ai_request()
                with self.assertRaisesRegex(RuntimeError,'60 AI requests'):reserve_ai_request()
            with use_workspace(self.b):reserve_ai_request()
        with patch('workspace.time.monotonic',return_value=4600):
            with use_workspace(self.a):reserve_ai_request()
            self.assertEqual(len(self.a.api_calls),1)

    def test_public_pdf_page_and_total_size_limits_reject_before_indexing(self):
        from pypdf import PdfWriter
        with use_workspace(self.a):
            p=self.a.uploads/'huge.pdf';writer=PdfWriter()
            for _ in range(201):writer.add_blank_page(width=100,height=100)
            with p.open('wb') as f:writer.write(f)
            with self.assertRaisesRegex(ValueError,'200 pages'):rag.extract_text_from_pdf(p)
            p.unlink()
            # A sparse file checks the quota without allocating 50 MB in memory.
            with (self.a.uploads/'existing.pdf').open('wb') as f:f.truncate(50*1024*1024)
            with self.assertRaisesRegex(ValueError,'50 MB'):
                self.upload('Cloud computing elasticity and flexible resources for workloads.')
