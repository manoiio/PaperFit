"""本机规范提取；只读取主文档普通段落/表格，不执行字段或嵌入对象。"""
from .package import Package, DemoError, sha256, q, NS

MAX_TEXT = 12000
MAX_FILE = 2 * 1024 * 1024


def extract_norm(data, kind, *, encoding='auto', path=None):
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE:
        raise DemoError('格式要求文件须为非空TXT/DOCX，最大2MB')
    if kind == 'txt':
        if encoding not in ('auto', 'utf-8-sig', 'utf-16', 'gb18030'):
            raise DemoError('未支持的TXT编码')
        codec = encoding
        if codec == 'auto':
            codec = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        try:
            text = data.decode(codec, errors='strict')
        except UnicodeError:
            raise DemoError('TXT无法可靠解码；请明确选择GB18030或转换为UTF-8，不会忽略错误字节') from None
        if '\ufffd' in text or any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            raise DemoError('TXT含替换字符或异常控制字符，请核对编码')
        segments = [{'location': f'TXT:L{i}', 'text': line} for i, line in enumerate(text.splitlines(), 1) if line.strip()]
        notes = [f'严格按{codec}解码；自动模式只识别UTF-8和带BOM的UTF-16，其他编码须明确选择。']
    elif kind == 'docx':
        if path is None: raise DemoError('DOCX规范须先保存到会话内部路径')
        pkg = Package(path)
        if pkg.hash != sha256(data): raise DemoError('规范文件哈希不匹配')
        segments, notes = [], ['只提取主文档普通段落和表格单元格文字；不含页眉页脚、文本框、图片文字和嵌入对象。']
        counts = {'P': 0, 'T': 0}
        def paragraph(p, location):
            if p.xpath('.//w:del | .//w:ins | .//w:fldChar | .//w:instrText | .//w:drawing | .//w:object | .//w:sdt | .//w:txbxContent', namespaces=NS):
                notes.append(f'{location}含修订、字段或图形，未提取；请手动核对。')
                return
            pieces=[]
            for r in p.xpath('./w:r | ./w:hyperlink/w:r',namespaces=NS):
                for e in r:
                    if e.tag==q('t'):pieces.append(e.text or '')
                    elif e.tag==q('tab'):pieces.append('\t')
                    elif e.tag in (q('br'),q('cr')):pieces.append('\n')
            text=''.join(pieces)
            if text.strip(): segments.append({'location': location, 'text': text})
        for node in pkg.root.find(q('body')):
            if node.tag == q('p'):
                counts['P'] += 1
                paragraph(node, f'DOCX:P{counts["P"]}')
            elif node.tag == q('tbl'):
                counts['T'] += 1
                for r, row in enumerate(node.findall(q('tr')), 1):
                    for c, cell in enumerate(row.findall(q('tc')), 1):
                        for p, para in enumerate(cell.findall(q('p')), 1):
                            paragraph(para, f'DOCX:T{counts["T"]}:R{r}:C{c}:P{p}')
                        if cell.find(q('tbl')) is not None: notes.append('嵌套表格未提取，请手动核对。')
    else: raise DemoError('本阶段只支持TXT与DOCX规范，不支持PDF/OCR')
    if not segments: raise DemoError('没有可提取的普通文本，请改用文字输入')
    if sum(len(s['text']) for s in segments) > 100000:
        raise DemoError('规范可提取文字超过100000字符，请先缩小文件，不会截断')
    return {'file_sha256': sha256(data), 'kind': kind, 'segments': segments, 'notes': notes}


def marked_text(segments):
    return '\n'.join(f'【{s["location"]}】{s["text"]}' for s in segments)


def selected_segments(text):
    """编辑后的摘录使用本地行号，绝不猜测其仍精确来自原文件的某一行。"""
    from .spec_validation import DANGEROUS
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise DemoError('请选择或编辑1–12000字符的规范摘录，不会自动截断')
    if DANGEROUS.search(text): raise DemoError('规范摘录不接受代码、路径、密钥或工具调用指令')
    return [{'location': f'摘录:L{i}', 'text': t} for i, t in enumerate(text.splitlines(), 1) if t.strip()]

# A provenance namespace disambiguates actual TXT/DOCX positions from different excerpts.
# It never renumbers lines or edits quotations. The digest can be recomputed offline.
def source_group(location):
    import re
    m=re.match(r'^SRC:([0-9a-f]{64}):',str(location))
    return m[0] if m else ''

def evidence_segments(segments,location):
    group=source_group(location)
    return [s for s in segments if source_group(s['location'])==group]

def qualify_segments(segments):
    plain=[s for s in segments if not source_group(s['location'])]
    group='SRC:'+sha256(marked_text(plain).encode())+':'
    return [{'location':s['location'] if source_group(s['location']) else group+s['location'],'text':s['text']} for s in segments]

def verify_namespaces(segments):
    for group in {source_group(s['location']) for s in segments}-{''}:
        original=[{'location':s['location'][len(group):],'text':s['text']} for s in segments if s['location'].startswith(group)]
        if group!='SRC:'+sha256(marked_text(original).encode())+':':raise DemoError('规范来源命名空间与原始摘录哈希不符')
