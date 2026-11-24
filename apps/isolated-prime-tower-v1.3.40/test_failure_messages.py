import pathlib,shutil,subprocess,unittest

class FailureMessageTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Node is needed for the UI behavior test')
 def test_single_batch_and_reset_errors(self):
  html=pathlib.Path(__file__).with_name('wizard.html').read_text()
  script=html[html.index('function resultSummary('):html.index('async function poll()')]
  checks=r"""
const assert=require('node:assert/strict');
const panel={};const el=()=>panel;
const reason='Reference layer at Z=0.35 is 0.15 mm; slot 2 permits 0.2–0.3 mm. Align the reference layer grids and regenerate.';
let state={stage:'batch_complete',result:{plates:[{plate:1,generated:true},{plate:2,generated:false,error:reason}]}};
showFailures(state);
assert.equal(panel.hidden,false);assert.equal(panel.textContent,'Plate 2: '+reason);
assert.ok(resultSummary(state.result).includes(reason));
showFailures({stage:'needs_attention',message:reason,result:state.result});assert.equal(panel.textContent,reason);
showFailures({stage:'generate',result:{plates:[{plate:1,generated:false}]}});assert.equal(panel.hidden,true);
showFailures({stage:'ready'});assert.equal(panel.textContent,'');assert.equal(panel.hidden,true);
showFailures({stage:'batch_failed',result:{plates:[{plate:3,error:'<xml> & text'}]}});
assert.equal(panel.textContent,'Plate 3: <xml> & text');assert.equal(panel.innerHTML,undefined);
"""
  subprocess.run(['node','-e',script+'\n'+checks],check=True,capture_output=True,text=True)
  self.assertIn('#plateErrors{border:2px solid #b42318',html)
  self.assertIn('id="plateErrors" role="alert" hidden',html)
