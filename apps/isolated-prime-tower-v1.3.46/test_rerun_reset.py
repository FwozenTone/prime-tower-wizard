import pathlib,shutil,subprocess,unittest
from unittest.mock import patch
import tower_wizard as wizard

class RerunResetTests(unittest.TestCase):
 def test_generation_resets_log_before_worker_starts(self):
  for name in ('automatic','manual_generate'):
   w=wizard.Workflow();w.state.update(events=['previous failure'],result={'plates':[{'error':'old'}]},project='old.3mf',folder='old',stage='batch_failed')
   with patch.object(wizard.threading,'Thread') as thread:
    w.launch(getattr(w,name),{'source':'same.3mf'})
    self.assertEqual([],w.state['events']);self.assertIsNone(w.state['result'])
    self.assertEqual('starting',w.state['stage']);self.assertEqual('',w.state['project'])
    self.assertTrue(w.state['busy']);thread.return_value.start.assert_called_once()
 @unittest.skipUnless(shutil.which('node'),'Node required for UI test')
 def test_click_clears_immediately_and_discards_old_poll(self):
  html=pathlib.Path(__file__).with_name('wizard.html').read_text()
  script=html[html.index('let runRevision='):html.index('let slicerLocations=')]
  harness=r"""
const assert=require('node:assert/strict');
const nodes={};const el=id=>nodes[id]||(nodes[id]={textContent:'old log',hidden:false,value:'same.3mf',classList:{remove(){},toggle(){}},focus(){},scrollIntoView(){}});
const plateSettings={1:{frame_slot:1}};
const selectedPlates=()=>[1],inputs=()=>({source:'same.3mf'}),token='test';
let manualNeeded=false,lastStage='',postDone,oldDone;
const restoreInputs=async()=>{},showSelectedProject=()=>{};
const document={querySelectorAll:()=>[]};
const call=()=>new Promise(resolve=>{postDone=resolve});
let fetched=0;
const fetch=async()=>({json:()=>++fetched===1?new Promise(resolve=>{oldDone=resolve}):Promise.resolve({stage:'starting',events:[],inputs:{},message:'Starting',busy:true})});
(async()=>{
 const old=poll();await Promise.resolve();
 const run=start('/auto');
 assert.equal(el('details').textContent,'');assert.equal(el('plateErrors').textContent,'');assert.equal(el('plateErrors').hidden,true);
 oldDone({stage:'batch_failed',events:['stale error'],inputs:{},message:'Old failure'});await old;
 assert.equal(el('details').textContent,'');assert.equal(el('messageText').textContent,'Starting tower generation…');
 postDone({});await run;assert.equal(el('details').textContent,'');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
  subprocess.run(['node','-e',script+'\n'+harness],check=True,capture_output=True,text=True)
