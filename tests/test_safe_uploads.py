"""Upload transaction tests using temporary files and deterministic embeddings."""
import io
import unittest
from pathlib import Path
from unittest.mock import patch
from test_working_flows import make_pdf
import test_working_flows as flow_support
import rag, memory, study_uploads

class SafeUploadTests(unittest.TestCase):
    def setUp(self):
        self.fixture=flow_support.WorkingFlows();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        self.saved=self.root/'notes.pdf'
        make_pdf(self.saved,'Cloud original material: elasticity scales computing resources with demand.')
        rag.process_and_index_pdf(self.saved,'notes.pdf')
        self.original=self.saved.read_bytes()
        self.before={p:p.read_bytes() for p in (rag.FAISS_INDEX_FILE,rag.METADATA_FILE)}
        self.original_memory=memory.load_memory()

    def upload(self,name='notes.pdf',text='Cloud replacement material: virtualization shares hardware among virtual machines.'):
        p=self.root/'incoming.pdf';make_pdf(p,text)
        f=io.BytesIO(p.read_bytes());f.name=name;f.size=len(f.getbuffer())
        return f

    def preserved(self):
        self.assertEqual(self.saved.read_bytes(),self.original)
        for p,data in self.before.items():self.assertEqual(p.read_bytes(),data)
        self.assertEqual(memory.load_memory(),self.original_memory)
        self.assertFalse(list(self.root.glob('.upload-*')))
        rag.get_vector_state().index=None;rag.get_vector_state().metadata=[]
        self.assertIn('original material',rag.search_study_material('cloud')[0]['text'])

    def test_corrupt_replacement_preserves_original_and_index(self):
        f=io.BytesIO(b'not a PDF');f.name='notes.pdf';f.size=len(f.getbuffer())
        with self.assertRaises(ValueError):study_uploads.save_and_index_pdf(f)
        self.preserved()

    def test_embedding_failure_preserves_original_and_index(self):
        with patch.object(rag,'get_embedding_model',side_effect=RuntimeError('Embedding failed')):
            with self.assertRaisesRegex(RuntimeError,'Embedding failed'):
                study_uploads.save_and_index_pdf(self.upload())
        self.preserved()

    def test_partial_index_write_is_rolled_back(self):
        def fail_save():
            rag.METADATA_FILE.write_bytes(b'partial write')
            raise OSError('Disk write failed')
        with patch.object(rag,'save_vector_store',side_effect=fail_save):
            with self.assertRaisesRegex(OSError,'Disk write failed'):
                study_uploads.save_and_index_pdf(self.upload())
        self.preserved()

    def test_final_pdf_replace_failure_restores_index(self):
        with patch.object(Path,'replace',side_effect=PermissionError('Replace denied')):
            with self.assertRaisesRegex(PermissionError,'Replace denied'):
                study_uploads.save_and_index_pdf(self.upload())
        self.preserved()

    def test_valid_replacement_updates_pdf_and_search_and_keeps_other_documents(self):
        other=self.root/'other.pdf';make_pdf(other,'Cloud another document describes public and private deployment models.')
        rag.process_and_index_pdf(other,'other.pdf')
        upload=self.upload();expected=upload.getvalue()
        result=study_uploads.save_and_index_pdf(upload)
        self.assertEqual(self.saved.read_bytes(),expected)
        self.assertEqual(result['file_name'],'notes.pdf')
        rag.get_vector_state().index=None;rag.get_vector_state().metadata=[]
        texts=' '.join(x['text'] for x in rag.search_study_material('cloud',file_name='notes.pdf'))
        self.assertIn('replacement material',texts)
        self.assertNotIn('original material',texts)
        self.assertTrue(rag.search_study_material('cloud',file_name='other.pdf'))
        self.assertFalse(list(self.root.glob('.upload-*')))

    def test_failed_first_upload_leaves_no_saved_pdf_or_index_change(self):
        f=io.BytesIO(b'not a PDF');f.name='new.pdf';f.size=len(f.getbuffer())
        with self.assertRaises(ValueError):study_uploads.save_and_index_pdf(f)
        self.assertFalse((self.root/'new.pdf').exists())
        self.preserved()

    def test_unsafe_names_rejected_before_writing(self):
        for name in ['../escaped.pdf','/tmp/escaped.pdf','folder/file.pdf','folder\\file.pdf','notes.txt']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):study_uploads.save_and_index_pdf(self.upload(name))
                self.preserved()

    def test_symlink_destination_is_not_followed(self):
        link=self.root/'link.pdf';link.symlink_to(self.saved)
        with self.assertRaises(ValueError):study_uploads.save_and_index_pdf(self.upload('link.pdf'))
        self.preserved()

if __name__=='__main__':unittest.main(verbosity=2)
