from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json,subprocess
from core.package import sha256,DemoError
from core.word_preview import batch,render_preview
from core.preview import valid_artifacts
from core.word_native import re_unsafe_field,simple_page_code
from web.session import WebSession
from tests.preview_fixture import configuration as fake_configuration
S=Path(__file__).resolve().parents[1]/'samples/phase53'
class NativePDF(TestCase):
 def test_batch_11_reuses_pdf_and_artifact_tampering_refuses(self):
  with TemporaryDirectory() as d:
   d=Path(d);pdf=d/'out.pdf';pdf.write_bytes(b'%PDF-synthetic');img=d/'page1.png';img.write_bytes(b'first');meta={'page_count':21,'engine':'word','pdf':str(pdf),'pages':[str(img)],'page_map':{'1':str(img)},'artifact_sha256':{str(pdf):sha256(pdf.read_bytes()),str(img):sha256(img.read_bytes())}}
   def convert(args,**kw):
    prefix=Path(args[-1]);a=int(args[args.index('-f')+1]);b=int(args[args.index('-l')+1])
    for i in range(a,b+1):prefix.with_name(prefix.name+'-'+str(i)+'.png').write_bytes(b'page'+str(i).encode())
    return subprocess.CompletedProcess(args,0)
   with patch('core.word_preview.subprocess.run',side_effect=convert) as run:
    result=batch(meta,12);self.assertEqual(run.call_count,1);self.assertIn('20',result['page_map']);self.assertNotIn('21',result['page_map']);self.assertEqual(batch(result,11),result);self.assertEqual(run.call_count,1)
   pdf.write_bytes(b'changed')
   with self.assertRaises(DemoError):batch(result,21)
 def test_export_is_mocked_no_docx_write_and_config_binding(self):
  with TemporaryDirectory() as d:
   d=Path(d);raw=(S/'source.docx').read_bytes();source=d/'source.docx';source.write_bytes(raw)
   def export(data,path):
    self.assertEqual(data,raw);path.write_bytes(b'%PDF-fake');return {'source_sha256':sha256(data),'pdf_sha256':sha256(path.read_bytes()),'limitation':'mock PDF; no visual proof'}
   def convert(args,**kw):
    if args[0].endswith('pdfinfo'):return subprocess.CompletedProcess(args,0,stdout='Pages: 12\n')
    prefix=Path(args[-1]);a=int(args[args.index('-f')+1]);b=int(args[args.index('-l')+1])
    for i in range(a,b+1):prefix.with_name(prefix.name+'-'+str(i)+'.png').write_bytes(b'png'+str(i).encode())
    return subprocess.CompletedProcess(args,0)
   with patch('core.word_preview.configuration',return_value=({'renderer':'mock Word','renderer_version':'mock'},'a'*64)),patch('core.word_preview.subprocess.run',side_effect=convert):
    meta=render_preview(source,d/'jobs',exporter=export);self.assertEqual(meta['page_count'],12);self.assertTrue(valid_artifacts(meta));self.assertEqual(source.read_bytes(),raw)
 def test_engine_switch_is_navigation_only_and_environment_separate(self):
  with TemporaryDirectory() as d:
   m=WebSession(Path(d));self.assertEqual(m.preview_engine,'libreoffice')
   with patch('core.word_native.export_pdf',side_effect=AssertionError('Must not export')),patch('core.word_preview.configuration',side_effect=AssertionError('Must not probe')):
    m.set_preview_engine('word');self.assertIsNone(m.preview_environment);m.set_preview_engine('libreoffice');self.assertIsNone(m.preview_environment)
   with self.assertRaises(DemoError):m.set_preview_engine('fake')
 def test_external_and_split_instructions_remain_unsafe(self):
  for x in (' DDEAUTO x','INCLUDETEXT secret',' LINK x'):self.assertTrue(re_unsafe_field(x))
  for c in (' PAGE ','PAGE \\* MERGEFORMAT','PAGE \\* roman'):self.assertTrue(simple_page_code(c))
  self.assertFalse(simple_page_code('PAGE \\* UNKNOWN'))
  self.assertFalse(re_unsafe_field(' REF "bookmark" \\h '))
 def test_old_page_files_stay_valid_until_new_map_is_published(self):
  from core.word_preview import retire_pages
  with TemporaryDirectory() as d:
   folder=Path(d);pdf=folder/'doc.pdf';pdf.write_bytes(b'%PDF bounded synthetic');stub=folder/'stub.png';stub.write_bytes(b'stub');meta={'page_count':61,'engine':'word','pdf':str(pdf),'pages':[str(stub)],'page_map':{},'artifact_sha256':{str(pdf):sha256(pdf.read_bytes()),str(stub):sha256(stub.read_bytes())}}
   def convert(args,**kw):
    prefix=Path(args[-1]);a=int(args[args.index('-f')+1]);b=int(args[args.index('-l')+1])
    for i in range(a,b+1):prefix.with_name(prefix.name+'-'+str(i)+'.png').write_bytes(b'page'+str(i).encode())
    return subprocess.CompletedProcess(args,0)
   with patch('core.word_preview.subprocess.run',side_effect=convert):
    meta=batch(meta,1);meta['artifact_sha256'].pop(str(stub));stub.unlink()
    for page in (11,21,31,41):meta=retire_pages(batch(meta,page))
    old=meta;new=batch(meta,51)
    self.assertTrue(valid_artifacts(old));self.assertEqual(len(new['page_map']),50);self.assertNotIn('1',new['page_map']);self.assertIn('60',new['page_map'])
    new=retire_pages(new);self.assertTrue(valid_artifacts(new));self.assertEqual(new['page_cleanup']['retired_files'],10);self.assertEqual(pdf.read_bytes(),b'%PDF bounded synthetic')

 def test_cancelled_batch_removes_only_new_images(self):
  from core.word_preview import discard_batch
  with TemporaryDirectory() as d:
   root=Path(d);pdf=root/'document.pdf';pdf.write_bytes(b'%PDF');old=root/'batch-old';old.mkdir();keep=old/'page-1.png';keep.write_bytes(b'keep');new=root/'batch-new';new.mkdir();added=new/'page-11.png';added.write_bytes(b'new')
   snapshot={'pdf':str(pdf),'artifact_sha256':{str(pdf):sha256(pdf.read_bytes()),str(keep):sha256(keep.read_bytes())}}
   result={'artifact_sha256':{**snapshot['artifact_sha256'],str(added):sha256(added.read_bytes())}}
   discard_batch(snapshot,result);self.assertTrue(pdf.exists());self.assertEqual(keep.read_bytes(),b'keep');self.assertFalse(new.exists())

 def test_accepted_batch_releases_its_snapshot_but_keeps_pdf_pages(self):
  from core.preview_jobs import PreviewJobs
  import time
  with TemporaryDirectory() as td:
   m=WebSession(Path(td));m.set_mode('academic');m.load((S/'source.docx').read_bytes(),'public.docx');m.set_types(json.loads((S/'roles.json').read_text()));self.assertTrue(m.confirm_and_check(),m.error);m.set_preview_engine('word');queue=PreviewJobs()
   config=({'renderer':'mock Word','renderer_version':'mock'},'b'*64)
   def initial(path,root,context=None):
    root.mkdir(parents=True);pdf=root/'document.pdf';pdf.write_bytes(b'%PDF mock');png=root/'page-1.png';png.write_bytes(b'1')
    return {'engine':'word','document_sha256':sha256(path.read_bytes()),'render_config_sha256':'b'*64,'page_count':12,'pages':[str(png)],'page_map':{'1':str(png)},'pdf':str(pdf),'artifact_sha256':{str(pdf):sha256(pdf.read_bytes()),str(png):sha256(png.read_bytes())}}
   def convert(args,**kw):
    prefix=Path(args[-1])
    for n in (11,12):prefix.with_name(prefix.name+'-'+str(n)+'.png').write_bytes(str(n).encode())
    return subprocess.CompletedProcess(args,0)
   def await_result(identity):
    until=time.monotonic()+5
    while time.monotonic()<until:
     status=m.preview_job_status(identity)
     if status['state'] not in ('running','queued'):return status
     time.sleep(.005)
    self.fail('mock batch did not complete')
   with patch('core.word_preview.configuration',return_value=config):
    request=m.submit_preview('input',scheduler=queue,renderer=initial);self.assertEqual(await_result(request['id'])['state'],'succeeded')
    root=m.work_root/'_preview-jobs';old=set(root.iterdir())
    with patch('core.word_preview.subprocess.run',side_effect=convert):
     request=m.submit_preview_pages('input',11,scheduler=queue);self.assertEqual(await_result(request['id'])['state'],'succeeded')
    self.assertEqual(set(root.iterdir()),old,'accepted batch leaked an input snapshot directory')
    meta=m.get_preview('input',verify_environment=False);self.assertTrue(valid_artifacts(meta));self.assertIn('11',meta['page_map']);self.assertTrue(Path(meta['pdf']).exists())
