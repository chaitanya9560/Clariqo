"""Run isolated regression and audit expectations; preserve failures as evidence."""
import ast,hashlib,json,sys,threading,time,unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_working_flows as regression
import test_deep_audit as edge
from test_learning_features import LearningFeatureTests
from test_chat_routing import ChatRoutingTests
from test_safe_uploads import SafeUploadTests
from test_study_plan_format import PlanFormatTests
from test_release_audit import ReleaseAuditTests
from test_cloud_sessions import CloudSessionTests
ROOT=Path(__file__).resolve().parents[1]
MODULES=['app.py','config.py','rag.py','quiz.py','memory.py','study_plan.py','study_chat.py','tools.py','ui_components.py','study_uploads.py','workspace.py','cloud_app.py']
called=set()
SOURCE_FILES={str(ROOT/m) for m in MODULES}
def profile(frame,event,arg):
    if event=='call' and frame.f_code.co_filename in SOURCE_FILES:
        called.add((Path(frame.f_code.co_filename).name,frame.f_code.co_name))

def digest_files():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for d in ['uploads','data/vector_store'] for p in (ROOT/d).glob('*') if p.is_file()}

class AuditResult(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.outcomes={}
    def addSuccess(self,test):self.outcomes[test.id()]='PASS';super().addSuccess(test)
    def addFailure(self,test,err):self.outcomes[test.id()]='FAIL';super().addFailure(test,err)
    def addError(self,test,err):self.outcomes[test.id()]='FAIL';super().addError(test,err)
    def addSubTest(self,test,subtest,err):
        if err:self.outcomes[test.id()]='FAIL'
        super().addSubTest(test,subtest,err)

suite=unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(regression))
for cls in (LearningFeatureTests, ChatRoutingTests, SafeUploadTests, PlanFormatTests, ReleaseAuditTests, CloudSessionTests, edge.DeepAudit):
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
suite.addTests(edge.UploadAndRenderingAudit(n) for n in edge.UploadAndRenderingAudit.__dict__ if n.startswith('test_'))
(ROOT/'test_results').mkdir(exist_ok=True)
before=digest_files();start=time.monotonic()
sys.setprofile(profile);threading.setprofile(profile)
with (ROOT/'test_results/deep-combined.log').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=AuditResult).run(suite)
sys.setprofile(None);threading.setprofile(None)
coverage={}
for m in MODULES:
    defs=[n.name for n in ast.parse((ROOT/m).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    coverage[m]={'called':[n for n in defs if (m,n) in called],'not_called':[n for n in defs if (m,n) not in called]}
report={'tests_run':result.testsRun,'passed_methods':sum(s=='PASS' for s in result.outcomes.values()),'failed_methods':sum(s=='FAIL' for s in result.outcomes.values()),'failure_events':len(result.failures),'error_events':len(result.errors),'seconds':round(time.monotonic()-start,2),'results':result.outcomes,'function_call_coverage':coverage,'saved_pdfs_and_index_unchanged':before==digest_files()}
(ROOT/'test_results/deep-summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['results','function_call_coverage']}))

raise SystemExit(0 if result.wasSuccessful() else 1)
