"""保守读取直接格式、docDefaults、常见段落/字符样式及basedOn继承。"""
from .package import q, NS, parse, DemoError
from posixpath import normpath
from urllib.parse import unquote
from lxml import etree as ET
import re

class Unresolved(ValueError):
    pass

class Resolver:
    def __init__(self, pkg):
        self.pkg = pkg
        self.conflicting_styles = set()
        if pkg.styles is not None:
            ids=[x.get(q("styleId")) for x in pkg.styles.findall(q("style"))]
            self.conflicting_styles={i for i in ids if ids.count(i)>1}
        self.styles = {} if pkg.styles is None else {s.get(q('styleId')): s for s in pkg.styles.findall(q('style'))}
        self.defaults = None if pkg.styles is None else pkg.styles.find(q('docDefaults'))
        self.default_styles = {}
        self.conflicting_defaults = set()
        for ident, s in self.styles.items():
            if s.get(q('default')) in ('1', 'true', 'on'):
                if s.get(q('type')) in self.default_styles:self.conflicting_defaults.add(s.get(q('type')))
                self.default_styles[s.get(q('type'))] = ident

    def chain(self, ident, kind):
        if not ident:
            return []
        seen, result = set(), []
        while ident:
            if ident in seen or ident not in self.styles or ident in self.conflicting_styles:
                raise Unresolved('样式缺失或basedOn循环')
            seen.add(ident)
            s = self.styles[ident]
            if s.get(q('type')) != kind:
                raise Unresolved('样式类型不支持')
            result.insert(0, s)
            base = s.find(q('basedOn'))
            ident = base.get(q('val')) if base is not None else None
        return result

    def layers(self, p, r=None, kind='rPr'):
        layers = []
        if self.pkg.styles is not None and len(self.pkg.styles.findall(q('docDefaults')))>1:raise Unresolved('重复docDefaults，无法确定继承')
        if p.find('w:pPr/w:pStyle',NS) is None and 'paragraph' in self.conflicting_defaults:raise Unresolved('重复默认段落样式，无法确定继承')
        if self.defaults is not None:
            d = self.defaults.find(f'w:{kind}Default/w:{kind}', NS)
            if d is not None:
                layers.append(d)
        if len(p.findall('w:pPr/w:pStyle',NS))>1:raise Unresolved('重复段落样式引用，继承路径冲突')
        ps = p.find('w:pPr/w:pStyle', NS)
        ident = ps.get(q('val')) if ps is not None else self.default_styles.get('paragraph')
        for s in self.chain(ident, 'paragraph'):
            x = s.find(q(kind))
            if x is not None:
                layers.append(x)
        if r is not None:
            if len(r.findall('w:rPr/w:rStyle',NS))>1:raise Unresolved('重复字符样式引用，继承路径冲突')
            rs = r.find('w:rPr/w:rStyle', NS)
            # Default character style is not an additional layer over a paragraph style.
            default_char = self.default_styles.get('character')
            if rs is None and default_char and self.styles[default_char].find(q('rPr')) is not None:
                raise Unresolved('带格式的默认字符样式：本阶段待复核')
            if rs is not None:
                for s in self.chain(rs.get(q('val')), 'character'):
                    x = s.find(q(kind))
                    if x is not None:
                        layers.append(x)
            x = r.find(q(kind))
        else:
            x = p.find(q(kind)) if kind == 'pPr' else None
        if x is not None:
            layers.append(x)
        for layer in layers:
            for tag in ('rFonts', 'sz', 'spacing', 'ind', 'vertAlign', 'lang'):
                if len(layer.findall(q(tag))) > 1:
                    raise Unresolved('重复格式属性元素，不能确定有效值')
        return layers

    def attrs(self, layers, tag):
        out = {}
        for layer in layers:
            e = layer.find(q(tag))
            if e is not None:
                out.update({k.split('}')[-1]: v for k, v in e.attrib.items()})
        return out

    def value(self, layers, tag, default=None):
        out = default
        for layer in layers:
            e = layer.find(q(tag))
            if e is not None:
                out = e.get(q('val'), '1')
        return out

    def _layer_origin(self, layer):
        parent=layer.getparent()
        if parent is None:return '独立格式层'
        if parent.tag==q('style'):
            return parent.get(q('type'),'')+'样式:'+str(parent.get(q('styleId')))
        if parent.tag in (q('rPrDefault'),q('pPrDefault')):return 'docDefaults'
        if parent.tag==q('lvl'):return '编号层级符号格式'
        return '直接run格式' if parent.tag==q('r') else '直接段落格式'

    def _theme_font(self, token):
        a='http://schemas.openxmlformats.org/drawingml/2006/main'
        enums={x+y:(x,y) for x in ('major','minor') for y in ('Ascii','HAnsi','EastAsia')}
        if token not in enums:raise Unresolved('未支持的主题字体枚举 '+str(token))
        group,region=enums[token]
        try:
            rels=parse(self.pkg.parts.get('word/_rels/document.xml.rels',b'<Relationships/>'))
            if any(e.get('Type','').endswith('/themeOverride') for e in rels):raise Unresolved('主题覆盖关系暂不支持')
            matches=[e for e in rels if e.get('Type','').endswith('/theme')]
            if len(matches)!=1 or matches[0].get('TargetMode')=='External':raise Unresolved('主题关系缺失、重复或外部关系')
            target=unquote(matches[0].get('Target',''));member=normpath(target.lstrip('/') if target.startswith('/') else 'word/'+target)
            if member not in self.pkg.parts:raise Unresolved('主题部件缺失')
            root=parse(self.pkg.parts[member])
            if root.tag!='{'+a+'}theme':raise Unresolved('主题不是支持的Transitional DrawingML')
            groups=root.findall('./{'+a+'}themeElements/{'+a+'}fontScheme/{'+a+'}'+group+'Font')
            if len(groups)!=1:raise Unresolved('主题major/minor定义缺失或重复')
            collection=groups[0]
            settings=parse(self.pkg.parts.get('word/settings.xml',b'<settings/>'))
            langs=settings.findall(q('themeFontLang'))
            if len(langs)>1:raise Unresolved('重复themeFontLang，语言映射不唯一')
            attr='eastAsia' if region=='EastAsia' else 'val'
            lang=langs[0].get(q(attr)) if langs else None
            selector='ea' if region=='EastAsia' else 'latin'
            script=None
            if lang:
                low=lang.lower();prefix=low.split('-')[0]
                if low in ('zh-cn','zh-sg','zh-hans'):script='Hans'
                elif low in ('zh-tw','zh-hk','zh-mo','zh-hant'):script='Hant'
                elif region=='EastAsia' and low=='ja-jp':script='Jpan'
                elif region=='EastAsia' and low=='ko-kr':script='Hang'
                elif prefix in ('en','fr','de','es','it','pt','nl','sv','no','da','fi','pl','cs','sk','hu','ro','tr','hr','sl','id','ms','ca') and region!='EastAsia' and re.fullmatch(r'[a-z]{2,3}(?:-latn)?(?:-[a-z]{2}|-[0-9]{3})?',low):script='Latn'
                else:raise Unresolved('主题语言 '+lang+' 未纳入当前唯一映射范围')
                selector='latin' if script=='Latn' else 'font'
            if script=='Latn' and any(e.tag=='{'+a+'}font' and e.get('script')=='Latn' for e in collection):raise Unresolved('补充Latn与latin主题同时出现，本阶段不猜测其覆盖关系')
            candidates=[e for e in collection if e.tag=='{'+a+'}'+selector and (selector!='font' or e.get('script')==script)]
            if len(candidates)!=1 or not candidates[0].get('typeface','').strip():raise Unresolved('主题 '+group+'Font/'+selector+('['+script+']' if script else '')+' 字体缺失或不唯一（主题语言 '+str(lang)+'）')
            return candidates[0].get('typeface'),{'theme':token,'member':member,'theme_font_lang':lang,'script':script,'selector':group+'Font/'+selector}
        except Unresolved:raise
        except (DemoError,ET.XMLSyntaxError):raise Unresolved('主题或设置XML损坏/不安全，不能解析') from None

    def font_info(self, layers, slot, text=None, _fallback=True):
        """Document-declared font only; never consult installed fonts or invent defaults."""
        theme={'eastAsia':'eastAsiaTheme','ascii':'asciiTheme','hAnsi':'hAnsiTheme'}[slot]
        origins=[self._layer_origin(x) for x in layers]
        result={'font':None,'slot':slot,'source_type':'missing','inheritance_path':origins,'declared_at':None,
                'hint':self.attrs(layers,'rFonts').get('hint','default'),'run_language':self.attrs(layers,'lang'),
                'computer_font_installation_checked':False,'safe_to_fix_slot':True}
        try:
            hint=result['hint']
            if hint not in ('default','eastAsia'):raise Unresolved('字体hint='+str(hint)+' 未支持；未套用其他槽位')
            if slot=='hAnsi' and hint=='eastAsia' and _fallback:raise Unresolved('Latin扩展字符受eastAsia hint、语言及字符集映射影响；当前保留待复核，ASCII检查仍可完成')
            out=None;token=None
            for layer,origin in zip(layers,origins):
                f=layer.find(q('rFonts'))
                if f is None:continue
                if f.get(q(theme)) is not None:token=f.get(q(theme));out=None;result['declared_at']=origin
                elif f.get(q(slot)) is not None:out=f.get(q(slot));token=None;result['declared_at']=origin
            if token is not None:
                result['theme']=token
                # Unusual cross-region theme references are explicitly outside this prototype.
                suffix={'ascii':'Ascii','hAnsi':'HAnsi','eastAsia':'EastAsia'}[slot]
                if token not in (('majorAscii','minorAscii','majorHAnsi','minorHAnsi') if slot in ('ascii','hAnsi') else ('major'+suffix,'minor'+suffix)):raise Unresolved('主题枚举与字体槽位不对应，需人工确认')
                out,proof=self._theme_font(token);result['theme_basis']=proof;result['source_type']='theme'
            else:result['source_type']=result['declared_at'] or 'missing'
            if not isinstance(out,str) or not out.strip():raise Unresolved(slot+'槽位在直接格式、样式及docDefaults中没有可解析字体；不补默认值')
            if slot=='eastAsia' and same_font(out,'Times New Roman') and _fallback:
                left=self.font_info(layers,'ascii',_fallback=False);right=self.font_info(layers,'hAnsi',_fallback=False)
                if left['font'] is None or right['font'] is None:raise Unresolved('eastAsia为Times New Roman，但ASCII/hAnsi不足以判定特殊回退映射')
                if same_font(left['font'],right['font']):
                    out=left['font'];result['fallback_basis']='MS-OI29500回退：eastAsia=Times New Roman且ascii=hAnsi时使用ascii字体';result['safe_to_fix_slot']=False
            if text and slot in ('ascii','hAnsi') and scripts(text)[0]:
                ea=self.font_info(layers,'eastAsia',_fallback=False)
                if ea['font'] is None or same_font(ea['font'],'Times New Roman'):
                    result['safe_to_fix_slot']=False
                    result['dependency']='混合run的eastAsia缺失或使用Times New Roman特殊回退；不能证明改西文槽位后中文有效字体保持，请人工核对'
            result['font']=out
            result['explanation']=out+'；来源 '+str(result['declared_at'])+(' → '+str(result.get('theme_basis')) if token else '')
        except Unresolved as exc:
            result['reason']=str(exc);result['safe_to_fix_slot']=False
        return result

    def font(self, layers, slot):
        info=self.font_info(layers,slot)
        return info['font'] if info['font'] is not None else {'unresolved':info['reason'],'slot':slot,**({'theme':info['theme']} if info.get('theme') else {})}

    def size(self, layers):
        raw = self.value(layers, 'sz')
        try:
            return int(raw) / 2 if raw is not None and int(raw) > 0 else None
        except ValueError:
            return None

    def special(self, r, layers):
        if any(e.tag not in {q('rPr'), q('t'), q('tab'), q('br'), q('cr')} for e in r):
            return '图片、域、注释引用或其他非普通run结构'
        if self.value(layers, 'vertAlign', 'baseline') != 'baseline':
            return '上角标/下角标'
        if self.value(layers, 'position', '0') != '0':
            return '文字基线偏移'
        for tag in ('rtl', 'cs', 'vanish', 'webHidden'):
            if self.value(layers, tag, '0') not in ('0', 'false', 'off'):
                return '复杂文字/隐藏文字'
        if any(layer.find(q('rPrChange')) is not None for layer in layers):
            return '修订格式'
        if any(layer.find(q(tag)) is not None for layer in layers for tag in ('fitText', 'eastAsianLayout', 'oMath')):
            return '文字适配、东亚特殊布局或公式属性'
        return None


def scripts(text):
    cn, slots, unknown = False, set(), False
    for ch in text:
        n = ord(ch)
        if ch.isspace():
            continue
        if (0x3400 <= n <= 0x9FFF or 0xF900 <= n <= 0xFAFF or 0x20000 <= n <= 0x323AF
                or 0x3000 <= n <= 0x303F or 0xFF01 <= n <= 0xFF60):
            cn = True
        elif n < 128:
            slots.add('ascii')
        elif 0x00C0 <= n <= 0x024F or 0x1E00 <= n <= 0x1EFF:
            slots.add('hAnsi')
        else:
            unknown = True
    return cn, sorted(slots), unknown


def paragraph_unsafe(p):
    # Unknown paragraph children (including hyperlinks, equations, revisions, SDT, fields)
    # cause the whole confirmed paragraph to be skipped, retaining its original structure.
    allowed = {q('pPr'), q('r'), q('bookmarkStart'), q('bookmarkEnd'), q('proofErr')}
    if any(c.tag not in allowed for c in p):
        return '链接、公式、修订、内容控件或未支持段落结构：整段跳过'
    if p.find('w:pPr/w:pPrChange', NS) is not None:
        return '段落格式修订：整段跳过'
    if p.find('w:pPr/w:framePr', NS) is not None:
        return '浮动框架段落：整段跳过'
    if any(r.find(q('fldChar')) is not None or r.find(q('instrText')) is not None for r in p.findall(q('r'))):
        return '域：整段跳过（包括域显示文字）'
    return None


def same_font(actual, expected):
    # Localized family names only; never infer a missing slot or installation.
    aliases={'simsun':'宋体','宋体':'宋体','simhei':'黑体','黑体':'黑体','kaiti':'楷体','楷体':'楷体','fangsong':'仿宋','仿宋':'仿宋'}
    if not isinstance(actual,str) or not isinstance(expected,str):return False
    a,b=actual.strip().casefold(),expected.strip().casefold()
    return aliases.get(a,a)==aliases.get(b,b)
