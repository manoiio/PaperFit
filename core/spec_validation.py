"""短规范字段和证据的保守本地校验；AI客户端及自定义配置复用。"""
import re
from .package import DemoError
from .rule_config import validate_value

REASONS={'title','fixed_spacing','minimum_spacing','ambiguous','conflict','out_of_range','unsupported'}
FONT_NAMES={'小四':12,'四':14,'五':10.5,'小五':9,'三':16,'小三':15,'二':22,'小二':18}

DANGEROUS=re.compile(r'```|(?:https?|file)://|(?:[A-Za-z]:[\\/]|/(?:Users|Volumes|home|tmp|private|etc)/)|(?:/[^\s，。；:,]+){2,}|(?<![A-Za-z0-9_])(?:exec|eval|import|subprocess|tool_calls?|function_call)(?![A-Za-z0-9_])|调用工具|执行代码|<script|DEEPSEEK_API_KEY|\bsk-[A-Za-z0-9]',re.I)

def validate_text(text):
    if not isinstance(text,str) or not text.strip() or len(text)>2000:
        raise DemoError('请输入1–2000字符的短格式要求')
    if DANGEROUS.search(text):raise DemoError('短规范不接受代码、文件路径、密钥或工具指令，请只输入公开格式要求')
    return text

def _body_context(text, quote):
    positions=[m.start() for m in re.finditer(re.escape(quote),text)]
    for start in positions:
        sentence=re.split(r'[。；;\n]',text[:start+len(quote)])[-1]
        subjects=re.findall(r'正文|标题|摘要|图题|表题|参考文献|页眉|页脚|目录',sentence)
        if not subjects or subjects[-1]!='正文':return False
    return bool(positions)

def _numbers(text, field_name):
    result=[]
    if field_name=='font_size':
        for m in re.finditer(r'(小四|小五|小三|小二|四|五|三|二)号',text):result.append(FONT_NAMES[m.group(1)])
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',text,re.I):result.append(float(m.group(1)))
    else:
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*倍',text):result.append(float(m.group(1)))
        if '单倍' in text:result.append(1.0)
    return set(result)

def validate_draft(payload,text):
    validate_text(text)
    if not isinstance(payload,dict) or set(payload)!= {'font_size','line_spacing','unsupported'}:
        raise DemoError('AI返回结构不符，拒绝未知字段；只接受字号、倍数行距和未支持提示')
    if not isinstance(payload['unsupported'],list) or len(payload['unsupported'])>20:
        raise DemoError('未支持提示结构无效')
    for note in payload['unsupported']:
        if not isinstance(note,dict) or set(note)!= {'quote','reason'} or note['reason'] not in REASONS:
            raise DemoError('未支持提示含未知字段或指令')
        if not isinstance(note['quote'],str) or not 1<=len(note['quote'])<=200 or note['quote'] not in text or DANGEROUS.search(note['quote']):
            raise DemoError('未支持提示的原文依据无效')
    for name,rule in [('font_size','R05'),('line_spacing','R06')]:
        f=payload[name]
        if f is None:continue  # Missing fields remain missing, never inferred defaults.
        if not isinstance(f,dict) or set(f)!= {'value','quote'}:raise DemoError('AI字段结构无效')
        validate_value(rule,f['value'])
        quote=f['quote']
        if not isinstance(quote,str) or not 1<=len(quote)<=200 or quote not in text or DANGEROUS.search(quote):
            raise DemoError('AI字段原文短句不在输入中或不安全')
        if not _body_context(text,quote):raise DemoError('字段原文没有明确正文范围，不能把标题要求套到正文')
        if name=='line_spacing' and any(w in quote for w in ('固定','最小','磅','pt')):
            raise DemoError('固定或最小值行距不能转换为倍数')
        if _numbers(quote,name)!={f['value']}:
            raise DemoError('提取值与原文数值不一致或含糊，请手动确认')
        # Conservative sentence-wide conflict check. Stop at explicit non-body subjects.
        for sentence in re.split(r'[。；;\n]',text):
            subjects=list(re.finditer(r'正文|标题|摘要|图题|表题|参考文献|页眉|页脚|目录',sentence))
            for i,subject in enumerate(subjects):
                if subject.group()!='正文':continue
                segment=sentence[subject.start():subjects[i+1].start() if i+1<len(subjects) else len(sentence)]
                if name=='font_size':segment=re.split(r'行距',segment)[0]
                values=_numbers(segment,name)
                if (values and values != {f['value']}) or len(values)>1 or any(w in segment for w in ('或','任选','大约','左右','建议','可能')):
                    raise DemoError('正文要求冲突或含糊，不自动提取，请手动确认')
                if name=='line_spacing' and any(w in segment for w in ('固定','最小值')):
                    raise DemoError('正文行距含固定值或冲突，不自动转倍数')
    return payload

