"""UI-only artifact reuse: complete jobs stop polling; ZIP is built once."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from streamlit.testing.v1 import AppTest
class NativeOutputUI(unittest.TestCase):
 def test_complete_download_package_is_not_rebuilt_on_rerun(self):
  with TemporaryDirectory() as d:
   pdf=Path(d)/'a.pdf';pdf.write_bytes(b'%PDF fake UI test')
   script='''
import streamlit as st
from io import BytesIO
import zipfile
from web.native_output_ui import render_native_output
class M:
 def __init__(self):self.preview_engine='word';self.result=True;self.calls=0
 def preview_targets(self):return {'round-1':{'sha256':'a'*64}}
 def preview_job_status(self,identity):return {'state':'succeeded'}
 def set_preview_engine(self,e):self.preview_engine=e
 def get_preview(self,*a,**kw):return {'pdf':PDF,'document_sha256':'a'*64,'page_count':1,'word_export':{'pdf_sha256':'b'*64}}
 def _history_binding(self):return 'stable'
 def result_package(self):
  self.calls+=1;b=BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('fixed.docx',b'synthetic')
  return b.getvalue()
if 'm' not in st.session_state:st.session_state.m=M();st.session_state.s={'native_output':{'sha256':'a'*64,'state':'cached','target':'round-1'}}
render_native_output(st.session_state.m,st.session_state.s)
'''.replace('PDF',repr(str(pdf)))
   app=AppTest.from_string(script).run();self.assertFalse(app.exception)
   app.checkbox[0].check().run();self.assertFalse(app.exception);self.assertEqual(app.session_state.m.calls,1)
   app.run();self.assertFalse(app.exception);self.assertEqual(app.session_state.m.calls,1)
 def test_finished_batch_with_existing_pages_notifies_once(self):
  script='''
import streamlit as st
from web.preview_ui import render_target_state
class M:
 def __init__(self):
  self.preview_epoch=0;self.preview_engine='word';self.preview_jobs={'batch':{'key':'out','epoch':0,'engine':'word','accepted':False}}
 def active_preview_job(self,key):self.preview_jobs['batch']['accepted']=True;return None
if 'm' not in st.session_state:st.session_state.m=M()
render_target_state(st.session_state.m,'out',{'engine':'word','page_count':12,'page_map':{'11':'mock.png'}},'seed','single')
st.write('batch ready')
'''
  app=AppTest.from_string(script).run();self.assertFalse(app.exception)
  self.assertTrue(app.session_state.m.preview_jobs['batch']['view_notified'])
  app.run();self.assertFalse(app.exception)
 def test_effect_number_controls_render_values_and_missing_without_defaults(self):
  script='''
import streamlit as st
from web.rule_fields_ui import value_control
for prop,seed in [('scale',100),('character_spacing',0),('baseline',None)]:
 value=value_control('main','body__'+prop,seed,'test-'+prop,lambda:None)
 st.write('value',value)
'''
  app=AppTest.from_string(script).run();self.assertFalse(app.exception)
  self.assertEqual([x.value for x in app.number_input],[100.,0.,None])
