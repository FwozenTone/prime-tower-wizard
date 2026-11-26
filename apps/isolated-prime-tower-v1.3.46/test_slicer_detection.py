import pathlib,tempfile,zipfile,unittest,shutil,subprocess
import xml.etree.ElementTree as ET
import tower_wizard as wizard
import isolated_prime_tower as tower

class SlicerDetectionTests(unittest.TestCase):
 def test_saved_application_and_legacy_metadata(self):
  cases=[({'Application':'Snapmaker_Orca-2.4.1','OrcaSlicer':'2.5.1'},'snapmaker'),({'Application':'OrcaSlicer-2.5.1','Snapmaker_Orca:3mfVersion':'1'},'mainline'),({'Application':'BambuStudio-02.08.01.55','OrcaSlicer':'2.5.1'},'mainline'),({'Application':'Snapmaker Orca 2.4.1'},'snapmaker'),({'Snapmaker_Orca:3mfVersion':'1'},'snapmaker'),({'OrcaSlicer':'2.5.1','Snapmaker_Orca:3mfVersion':'1'},None),({'Application':'BambuStudio-2.0'},None),({},None)]
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/'project.3mf'
   for metadata,expected in cases:
    model=ET.Element(tower.Q('model'))
    for key,value in metadata.items():ET.SubElement(model,tower.Q('metadata'),name=key).text=value
    with zipfile.ZipFile(path,'w') as archive:archive.writestr(tower.MODEL,ET.tostring(model))
    self.assertEqual(wizard.detect_project_slicer(path)['branch'],expected)
 @unittest.skipUnless(shutil.which('node'),'Node required for UI check')
 def test_selection_locations_and_manual_override(self):
  html=pathlib.Path(__file__).with_name('wizard.html').read_text()
  script=html[html.index('let slicerLocations='):html.index('async function saveOrca()')]
  harness=r"""
const assert=require('node:assert/strict');
const nodes={};const el=id=>nodes[id]||(nodes[id]={style:{},value:'',textContent:''});
slicerLocations={mainline:{path:'/apps/Orca'},snapmaker:{path:'/apps/Snapmaker'}};
selectProjectSlicer({branch:'snapmaker'},'one.3mf');assert.equal(el('slicer_branch').value,'snapmaker');assert.equal(el('orca').value,'/apps/Snapmaker');
selectProjectSlicer({branch:'mainline'},'two.3mf');assert.equal(el('slicer_branch').value,'mainline');assert.equal(el('orca').value,'/apps/Orca');
selectProjectSlicer({branch:null},'unknown.3mf');assert.equal(el('slicer_branch').value,'mainline');assert.equal(el('slicerMatch').style.color,'#b42318');
el('slicer_branch').value='snapmaker';changeSlicer(true);assert.equal(el('orca').value,'/apps/Snapmaker');assert.equal(el('slicerMatch').textContent,'Using your slicer selection.');
"""
  subprocess.run(['node','-e',script+'\n'+harness],check=True,capture_output=True,text=True)
  self.assertIn('Select slicer version that matches the 3mf',html)

class PlateFrameSelectionTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Node required for UI check')
 def test_explicit_selection_retained_then_reset_for_new_project(self):
  html=pathlib.Path(__file__).with_name('wizard.html').read_text()
  script=html[html.index('let plateSettings='):html.index('function selectedPlates()')]
  harness=r"""
const assert=require('node:assert/strict');
const nodes={};const el=id=>nodes[id]||(nodes[id]={value:'',replaceChildren(){}});
const showSelectedProject=()=>{},selectProjectSlicer=()=>{},selectedPlates=()=>[];
let outputCustomized=false;
const call=async()=>({folder:'/projects',materials:[],plates:[]});
renderPlateOptions=()=>{};
(async()=>{
assert.equal(defaultPlateOptions().frame_slot,'');
settingsSource='one.3mf';el('source').value='one.3mf';plateSettings={'1':{frame_slot:3,width:40}};
await loadPlates();assert.equal(plateSettings['1'].frame_slot,3);
el('source').value='two.3mf';await loadPlates();assert.deepEqual(plateSettings,{});
assert.equal(defaultPlateOptions().frame_slot,'');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
  subprocess.run(['node','-e',script+'\n'+harness],check=True,capture_output=True,text=True)
  self.assertIn('Select outer wall and ribs filament (required)',html)
  self.assertNotIn('Automatic — choose a rigid material',html)
