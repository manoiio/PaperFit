"""只替换 document.xml，其余 ZIP 成员的未压缩字节原样保留。"""
from pathlib import Path
from io import BytesIO
import hashlib
import zipfile
from lxml import etree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
def q(name):
    return f'{{{W}}}{name}'

def sha256(data):
    return hashlib.sha256(data).hexdigest()

class DemoError(ValueError):
    pass

def parse(data):
    parser = ET.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)
    root = ET.fromstring(data, parser)
    if root.getroottree().docinfo.doctype:
        raise DemoError('不支持含DOCTYPE的XML')
    return root

class Package:
    def __init__(self, path):
        self.path = Path(path).resolve()
        if self.path.suffix.lower() != '.docx':
            raise DemoError('输入必须是.docx')
        if self.path.stat().st_size > 10 * 1024 * 1024:
            raise DemoError('演示输入上限10MB')
        self.raw = self.path.read_bytes()
        self.hash = sha256(self.raw)
        try:
            with zipfile.ZipFile(BytesIO(self.raw)) as z:
                self.infos = z.infolist()
                self.comment = z.comment
                names = [i.filename for i in self.infos]
                if len(names) != len(set(names)) or sum(i.file_size for i in self.infos) > 100 * 1024 * 1024:
                    raise DemoError('重复ZIP成员或解压体积超限')
                self.parts = {i.filename: z.read(i) for i in self.infos}
            self.root = parse(self.parts['word/document.xml'])
            self.story_roots = {}  # only validated, explicitly selected existing story parts
            self.styles = parse(self.parts['word/styles.xml']) if 'word/styles.xml' in self.parts else None
            if self.root.tag != q('document') or self.root.find(q('body')) is None:
                raise DemoError('只支持常见Transitional WordprocessingML主文档')
            # Validate OPC document content type; macro-enabled documents renamed .docx are rejected.
            ct = parse(self.parts['[Content_Types].xml'])
            types = [e.get('ContentType', '') for e in ct if e.get('PartName') == '/word/document.xml']
            if types != ['application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml']:
                raise DemoError('不支持宏文档或非标准主文档类型')
        except (zipfile.BadZipFile, KeyError, ET.XMLSyntaxError, RuntimeError) as e:
            raise DemoError(f'DOCX损坏或结构不支持：{type(e).__name__}') from e
        body = self.root.find(q('body'))
        self.paragraphs = body.findall(q('p'))
        self.sections = body.findall('w:p/w:pPr/w:sectPr', NS) + body.findall('w:sectPr', NS)
        self.ambiguous_sections = len(list(self.root.iter(q('sectPr')))) != len(self.sections)
        self.signed = any(n.startswith('_xmlsignatures/') for n in self.parts)

    def bytes(self, changed):
        if not changed:
            return self.raw
        main_changed=ET.tostring(self.root,method='c14n')!=ET.tostring(parse(self.parts['word/document.xml']),method='c14n')
        new_xml = ET.tostring(self.root, xml_declaration=True, encoding='UTF-8', standalone=True) if main_changed else self.parts['word/document.xml']
        out = BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            z.comment = self.comment
            for info in self.infos:
                replacement = ET.tostring(self.story_roots[info.filename], xml_declaration=True, encoding='UTF-8', standalone=True) if info.filename in self.story_roots else self.parts[info.filename]
                z.writestr(info, new_xml if info.filename == 'word/document.xml' else replacement)
        return out.getvalue()

def new_path(path, input_path=None):
    p = Path(path).absolute()
    if input_path is not None and p.resolve() == Path(input_path).resolve():
        raise DemoError('禁止覆盖原稿或使用指向原稿的路径')
    if p.exists() or p.is_symlink():
        raise DemoError(f'输出已存在，禁止覆盖：{p}')
    return p

def write_new(path, data, input_path=None):
    p = new_path(path, input_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive open prevents a concurrent process from making us overwrite an existing file.
    try:
        with p.open('xb') as f:
            f.write(data)
    except FileExistsError as e:
        raise DemoError(f'输出已存在，禁止覆盖：{p}') from e
    return p
