"""Local five-step shortcuts remain useful without credentials/network."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from web.session import WebSession
from core.package import DemoError
ROOT=Path(__file__).resolve().parents[1]
class LocalWorkbenchAcceptance(TestCase):
 def test_local_complete_no_api_and_shared_input_selection_switching(self):
  with TemporaryDirectory() as d,patch('ai.structure.http_post',side_effect=AssertionError('Network prohibited')) as structure_post,patch('ai.short_spec.http_post',side_effect=AssertionError('Network prohibited')) as spec_post,patch('ai.short_spec.settings',side_effect=DemoError('无密钥')):
   s=WebSession(d);s.set_mode('academic');s.load((ROOT/'samples/phase43/errors.docx').read_bytes(),'合成.docx')
   s.set_table_enabled(True);s.set_table_types({'1':'cover','2':'content','3':'pending'});s.enable_notes(True)
   note=s.note_draft.copy();note['objects']=[r['key'] for r in s.note_inventory()['objects'] if r['safe_relationship']];s.edit_notes(note)
   at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);at.session_state.workflow=s;at.run();at.button(key='local-entry').click().run();at.button(key='workspace-nav-2').click().run()
   at.button(key='smart-prepare').click().run();at.button(key='smart-confirm-scope').click().run();self.assertFalse(at.exception);self.assertTrue(s.report)
   at.button(key='smart-execute').click().run();self.assertFalse(at.exception);self.assertTrue(s.result);self.assertEqual(s.current_round,0);self.assertEqual(s.generation_count,1)
   raw=s.downloads()['fixed.docx'];selection=s.selected.copy();at.button(key='smart-entry').click().run();self.assertFalse(at.exception);self.assertEqual(selection,s.selected);self.assertEqual(raw,s.downloads()['fixed.docx'])
   at.button(key='local-entry').click().run();self.assertFalse(at.exception);self.assertEqual(s.generation_count,1);self.assertEqual(structure_post.call_count,0);self.assertEqual(spec_post.call_count,0)
 def test_old_page_marker_migrates_without_action(self):
  with TemporaryDirectory() as d:
   s=WebSession(d);s.load((ROOT/'samples/errors.docx').read_bytes(),'合成.docx')
   at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);at.session_state.workflow=s;at.session_state['workspace-smart']=True;at.session_state['smart-legacy']=True;at.run()
   self.assertFalse(at.exception);self.assertFalse(at.session_state['workspace-smart']);self.assertTrue(at.button(key='workspace-nav-2'));self.assertIsNone(s.report);self.assertFalse(any(b.key=='onepass-legacy' for b in at.button))
