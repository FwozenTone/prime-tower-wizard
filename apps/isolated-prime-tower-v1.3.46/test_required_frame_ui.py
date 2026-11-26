import pathlib,re,shutil,subprocess,unittest

class RequiredFrameUITests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Node required')
 def test_colors_and_required_selection_before_requests(self):
  html=pathlib.Path(__file__).with_name('wizard.html').read_text()
  render=html[html.index('function defaultPlateOptions()'):html.index('async function loadPlates(')]
  start=html[html.index('function validateFrameSelections()'):html.index('function resultSummary(')]
  script=r'''
const assert=require('node:assert/strict');
const nodes={};let selected=[1,2],plateSettings={},projectMaterials=[{slot:1,material:'PLA',rigid:true}];
function node(){return {style:{},options:[],append(...items){this.options.push(...items)},replaceChildren(){},focus(){this.focused=true}}}
const document={createElement:()=>node()};const el=id=>nodes[id]||(nodes[id]=node());
const selectedPlates=()=>selected;const plateLabel=n=>`Plate ${n}`;
function Option(text,value){this.text=text;this.value=value;this.style={}}
let requests=0;const call=async()=>{requests++};
'''+render+'\n'+start+r'''
(async()=>{
 renderPlateOptions();assert.equal(plateSettings[1].frame_slot,'');
 assert.equal(validateFrameSelections(),false);assert.equal(el('plate_1_frame_slot').focused,true);
 await start('/auto');assert.equal(requests,0);
 plateSettings[1].frame_slot='1';assert.equal(validateFrameSelections(),false);
 assert.match(el('error').textContent,/Plate 2/);
 plateSettings[2].frame_slot='1';assert.equal(validateFrameSelections(),true);
 selected=[1];plateSettings[2].frame_slot='';assert.equal(validateFrameSelections(),true);
 const created=[];document.createElement=()=>{const n=node();created.push(n);return n};
 plateSettings[1].frame_slot='';renderPlateOptions();
 const select=created.find(n=>n.id==='plate_1_frame_slot');
 assert.equal(select.required,true);assert.equal(select.style.color,'#b42318');
 assert.equal(select.options[0].style.color,'#b42318');assert.equal(select.options[1].style.color,'#000000');
 select.value='1';select.onchange();assert.equal(select.style.color,'#000000');assert.equal(plateSettings[1].frame_slot,'1');
 select.value='';select.onchange();assert.equal(select.style.color,'#b42318');
})().catch(e=>{console.error(e);process.exit(1)});
'''
  subprocess.run(['node','-e',script],check=True,capture_output=True,text=True)
