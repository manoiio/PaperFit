"""由bundled Python执行；调用技能原渲染器转换，再只栅格化前N页。"""
import json,sys,importlib.util
from pathlib import Path
from pdf2image import pdfinfo_from_path,convert_from_path

job=Path(sys.argv[1]);request=json.loads((job/'request.json').read_text())
spec=importlib.util.spec_from_file_location('bundled_render_docx',request['renderer_script'])
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
pdf,debug=renderer.convert_to_pdf(str(job/'source.docx'),str(job/'profile'),str(job),'source',False)
(job/'renderer.log').write_text(debug,encoding='utf-8')
if not pdf:raise RuntimeError('bundled DOCX conversion failed')
count=int(pdfinfo_from_path(pdf)['Pages'])
if count<1:raise RuntimeError('empty PDF')
end=min(count,request['max_pages'])
images=convert_from_path(pdf,dpi=request['dpi'],first_page=1,last_page=end,fmt='png',thread_count=1)
for n,img in enumerate(images,1):img.save(job/f'page-{n}.png')
(job/'worker-result.json').write_text(json.dumps({'page_count':count,'preview_pages':end,'pdf':pdf,
                                              'fallback_odt':'DOCX->ODT' in debug}),encoding='utf-8')
