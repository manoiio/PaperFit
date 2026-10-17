"""Versioned data-only project archives. Never extract user paths or trust verdicts."""
from io import BytesIO
from pathlib import Path, PurePosixPath
from uuid import uuid4
from datetime import datetime, timezone
import json, re, stat, shutil, zipfile
from .package import DemoError, Package, sha256, write_new
from .rule_config import strict_json
from .classification import TYPES, validate_classification

VERSION = 1
MAX_TOTAL = 100 * 1024 * 1024
MAX_DOCX = 10 * 1024 * 1024
MAX_MEMBERS = 100
MAX_ROUNDS = 30
MAX_MANIFEST = 8 * 1024 * 1024
HASH = re.compile(r'[0-9a-f]{64}\Z')

def require(ok, reason):
    if not ok: raise DemoError('项目包：'+reason)

def exact(value, keys, label):
    require(type(value) is dict and set(value)==set(keys),label+'字段或结构无效')

def hash_value(value):
    require(type(value) is str and HASH.fullmatch(value),'哈希无效')
    return value

def scope(pkg, data):
    require(type(data) is dict and set(data)-{'table_scope','front_scope','toc_scope','citation_scope','note_scope','reference_scope','caption_scope','material_exclusions','backmatter_policy_sha256'}=={'file_sha256','body','types','saved_confirmed'},'范围字段或结构无效')
    require(data['file_sha256']==pkg.hash, '范围与DOCX哈希不匹配')
    require(type(data['saved_confirmed']) is bool, '确认状态无效')
    body=data['body']; types=data['types']
    require(type(body) is list and all(type(i) is int and 1<=i<=len(pkg.paragraphs) for i in body) and len(set(body))==len(body),'正文编号无效')
    validate_classification(pkg, {'input_sha256':pkg.hash,'paragraph_types':types,'confirmed':True,'confirmation':'导入结构校验（尚非用户恢复确认）'})
    if data.get('backmatter_policy_sha256') is not None:
        from .backmatter import PATH as BACK_PATH
        require(hash_value(data['backmatter_policy_sha256'])==sha256(BACK_PATH.read_bytes()),'附录/致谢默认依据版本已变化，请明确核对新规则，不能原样恢复旧结论')
    if data.get('material_exclusions') is not None:
        from .backmatter import validate_exclusions
        validate_exclusions(pkg,data['material_exclusions'],types)
    if data.get('caption_scope') is not None:
        from .captions import validate_scope as vcapt
        vcapt(pkg,data['caption_scope'],{'paragraph_types':types},confirmed=False)
    if data.get('reference_scope') is not None:
        from .internal_refs import validate_scope as vr
        vr(pkg,data['reference_scope'],confirmed=False)
    if data.get('note_scope') is not None:
        from .notes import validate_scope as vn
        vn(pkg,data['note_scope'],confirmed=False)
    if data.get('table_scope') is not None:
        from .table_text import validate_scope
        validate_scope(pkg,data['table_scope'],confirmed=False)
    if data.get('toc_scope') is not None:
        from .toc import validate_scope as validate_toc
        validate_toc(pkg,data['toc_scope'],confirmed=False)
    if data.get('front_scope') is not None:
        from .front import validate_scope as validate_front
        validate_front(pkg,data['front_scope'],confirmed=False)
    if data.get('citation_scope') is not None:
        from .citations import validate_scope as vc
        vc(pkg,data['citation_scope'],{'paragraph_types':data['types']},confirmed=False)
    return data

def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()

def pack(manifest, members):
    raw=json_bytes(manifest)
    require(len(raw)<=MAX_MANIFEST, '清单过大，请减少历史')
    require(len(members)+1<=MAX_MEMBERS and sum(map(len,members.values()))+len(raw)<=MAX_TOTAL,'体积或文件数超限，请明确减少保存历史')
    require(all(len(v)<= (MAX_DOCX if k.endswith('.docx') else 160*1024) for k,v in members.items()),'单DOCX超过10MB或规则超过64KB')
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in {'project.json':raw,**members}.items():
            info=zipfile.ZipInfo(name, date_time=(2026,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    return stream.getvalue()

def stage(raw, work_root):
    """Validate into a fresh owned directory; any failure removes only this directory."""
    directory=None
    try:
        require(type(raw) is bytes and 0<len(raw)<=MAX_TOTAL,'压缩包最大100MB且不能为空')
        with zipfile.ZipFile(BytesIO(raw)) as z:
            infos=z.infolist();names=[i.filename for i in infos]
            require(1<=len(infos)<=MAX_MEMBERS and len(set(names))==len(names),'成员过多或重复成员')
            require(sum(i.file_size for i in infos)<=MAX_TOTAL,'解压总量超过100MB')
            for i in infos:
                name=i.filename; p=PurePosixPath(name)
                require(not p.is_absolute() and not any(s in ('..','.') for s in name.split('/')) and '\\' not in name and ':' not in name and not i.is_dir(), '成员路径不安全')
                require(not stat.S_ISLNK(i.external_attr>>16) and not (i.flag_bits&1), '不接受符号链接或加密成员')
                require(name=='project.json' or re.fullmatch(r'(?:documents/\d{4}\.docx|rules/\d{4}\.json)',name), '不是受支持的项目包成员')
                require(i.file_size<= (MAX_MANIFEST if name=='project.json' else MAX_DOCX if name.endswith('.docx') else 160*1024),'单文件超限')
            require('project.json' in names, '缺少project.json，不是论文有格项目包')
            data=strict_json(z.read('project.json').decode('utf-8'))
            exact(data, ('format','version','saved_at','display_name','documents','rules','state'), '清单')
            require(data['format']=='paper-grid-project' and type(data['version']) is int and data['version']==VERSION,'不支持的项目结构版本')
            require(type(data['saved_at']) is str and len(data['saved_at'])<=80,'保存时间无效')
            require(type(data['display_name']) is str and 0<len(data['display_name'])<=100 and '/' not in data['display_name'] and '\\' not in data['display_name'],'显示名称无效')
            require(type(data['documents']) is list and 1<=len(data['documents'])<=MAX_ROUNDS+2,'DOCX数量无效')
            require(type(data['rules']) is list and 1<=len(data['rules'])<=MAX_ROUNDS+1,'规则数量无效')
            expected={'project.json'}; blobs={};configs={};filehashes=set()
            for collection, dest, prefix, suffix in ((data['documents'],blobs,'documents/','.docx'),(data['rules'],configs,'rules/','.json')):
                for item in collection:
                    exact(item, ('sha256','member') if dest is blobs else ('sha256','member','kind'),'文件引用')
                    h=hash_value(item['sha256']);name=item['member']
                    require(type(name) is str and re.fullmatch(re.escape(prefix)+r'\d{4}'+re.escape(suffix),name) and name in names and name not in expected and h not in dest,'文件缺失、重复引用或未去重')
                    if dest is configs:require(item['kind'] in ('default','custom'),'规则类型无效')
                    content=z.read(name);require(sha256(content)==h,'文件哈希不符')
                    dest[h]=content;expected.add(name);filehashes.add(h)
            require(set(names)==expected,'含未引用文件')
        state=data['state']
        exact(state, ('original','current','current_round','generation_count','mode','rule','scope','selected','editor','history','history_policy','preview_history','checkpoint'), '项目状态')
        require(state['original'] in blobs and state['current'] in blobs and state['rule'] in configs,'当前输入、原稿或规则缺失')
        require(state['mode'] in ('basic','extended','academic') and state['history_policy'] in ('all','current'),'模式或历史策略无效')
        require(type(state['current_round']) is int and type(state['generation_count']) is int and 0<=state['current_round']<=state['generation_count']<=100000,'轮次无效')
        require(type(state['selected']) is list and len(state['selected'])<=10000 and len(set(state['selected']))==len(state['selected']) and all(type(x) is str and len(x)<=160 for x in state['selected']),'修正选择无效')
        require(type(state['preview_history']) is bool,'预览历史摘要无效')
        require(type(state['history']) is list and len(state['history'])<=MAX_ROUNDS,'历史超限，请减少历史')
        work_root=Path(work_root).resolve();work_root.mkdir(parents=True,exist_ok=True)
        directory=work_root/uuid4().hex;directory.mkdir()
        paths={}; rulepaths={}; pkgs={}
        expanded=0
        for n,(h,content) in enumerate(blobs.items()):
            p=directory/('document-'+str(n)+'.docx');write_new(p,content);paths[h]=p;pkgs[h]=Package(p)
            expanded+=sum(len(v) for v in pkgs[h].parts.values())
            require(expanded<=MAX_TOTAL,'全部DOCX内部展开数据超过100MB，请减少历史')
        from .engine import load_rules,load_custom_rules,DEFAULT_RULES,effective_rules
        for n,item in enumerate(data['rules']):
            h=item['sha256'];p=directory/('rules-'+str(n)+'.json');write_new(p,configs[h]);rulepaths[h]=p
            if item['kind']=='default':
                load_rules(p);require(configs[h]==DEFAULT_RULES.read_bytes(),'默认模板已变化；不能静默恢复旧含义')
            else:load_custom_rules(p)
        scope(pkgs[state['current']],state['scope'])
        if state['mode']!='basic':require(set(state['scope']['body'])=={int(n) for n,t in state['scope']['types'].items() if t=='body'},'正文范围与扩展分类不一致')
        rounds={}
        cp=state['checkpoint'];exact(cp,('round','file'),'省略历史的检查点')
        require(type(cp['round']) is int and 0<=cp['round']<=state['generation_count'] and cp['file'] in blobs,'检查点无效')
        require(cp['round']!=0 or cp['file']==state['original'],'原稿检查点不一致')
        for r in state['history']:
            exact({k:v for k,v in r.items() if k!='input_scope'}, ('number','parent','input','output','rule','mode','scope','changes','kind','saved_summary'), '历史轮次')
            require(type(r['number']) is int and 1<=r['number']<=state['generation_count'] and r['number'] not in rounds and type(r['parent']) is int and 0<=r['parent']<r['number'],'轮次重复或循环/倒置关系')
            require(r['input'] in blobs and r['output'] in blobs and r['rule'] in configs and r['mode'] in ('basic','extended','academic'),'轮次文件、规则或模式引用无效')
            scope(pkgs[r['output']],r['scope'])
            inputscope={**r['scope'],'file_sha256':r['input']}
            if inputscope.get('table_scope'):
                inputscope['table_scope']={**inputscope['table_scope'],'input_sha256':r['input']}
            if inputscope.get('toc_scope'):
                inputscope['toc_scope']={**inputscope['toc_scope'],'input_sha256':r['input']}
            if inputscope.get('front_scope'):
                inputscope['front_scope']={**inputscope['front_scope'],'input_sha256':r['input']}
            if inputscope.get('reference_scope'):inputscope['reference_scope']={**inputscope['reference_scope'],'input_sha256':r['input']}
            if inputscope.get('note_scope'):inputscope['note_scope']={**inputscope['note_scope'],'input_sha256':r['input']}
            if inputscope.get('citation_scope'):inputscope['citation_scope']={**inputscope['citation_scope'],'input_sha256':r['input']}
            if inputscope.get('caption_scope'):inputscope['caption_scope']={**inputscope['caption_scope'],'input_sha256':r['input']}
            if 'input_scope' in r:inputscope=r['input_scope']
            if r['kind'] in ('caption_position','dynamic_text','section_pages','field_update'):require('input_scope' in r,'对象/文字变化历史缺少原始范围，不可猜测定位')
            scope(pkgs[r['input']],inputscope)
            if r['mode']=='extended':require(set(r['scope']['body'])=={int(n) for n,t in r['scope']['types'].items() if t=='body'},'历史正文与分类不一致')
            require(type(r['changes']) is list and len(r['changes'])<=10000 and type(r['saved_summary']) is dict and r['kind'] in ('format','width_adaptation','figure_layout','pagination_layout','caption_position','dynamic_text','section_pages','field_update'),'历史记录类型无效')
            for c in r['changes']:
                require(type(c) is dict and {'rule_id','locator','before','after','verification','source'}<=set(c),'修改记录无效')
            rounds[r['number']]=r
        for r in rounds.values():
            require(r['number']>cp['round'] and (r['parent']==cp['round'] and r['input']==cp['file'] or r['parent'] in rounds and rounds[r['parent']]['output']==r['input']),'父轮次与输入文件不一致')
        if state['history_policy']=='all':
            require(state['current_round']==cp['round'] and state['current']==cp['file'] or state['current_round'] in rounds and rounds[state['current_round']]['output']==state['current'],'当前输入不能唯一对应轮次')
        else:require(not rounds,'精简快照不能伪造完整历史')
        used_docs={state['original'],state['current'],cp['file']}|{h for r in rounds.values() for h in (r['input'],r['output'])}
        used_rules={state['rule']}|{r['rule'] for r in rounds.values()}
        require(set(blobs)==used_docs and set(configs)==used_rules,'含未使用的DOCX或规则引用')
        from .project_editor import validate_editor
        validate_editor(state['editor'],DEFAULT_RULES)
        active_raw=strict_json(configs[state['rule']].decode('utf-8'));wb=state['editor'].get('workbench')
        if active_raw.get('format')=='paper-grid-rule-bundle':
            require(wb is not None and wb['active']==active_raw,'生效规则包与项目规则文件不一致；不信任编辑状态中的成功声明')
        elif wb is not None:require(wb['active'] is None,'项目工作台生效状态与原生规则文件不一致')
        return {'directory':directory,'manifest':data,'paths':paths,'rulepaths':rulepaths,'package_sha256':sha256(raw)}
    except Exception as exc:
        if directory is not None:shutil.rmtree(directory,ignore_errors=True)
        if isinstance(exc,DemoError):raise
        raise DemoError('项目包损坏或字段类型无效，未改变当前任务') from None
