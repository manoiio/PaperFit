"""Whitelist validation of non-executable editor drafts in a snapshot."""
from .project import exact, require
from .templates import validate_draft, validate_template, validate_segments, validate_value, field_map, FIELDS, ALL_FIELDS, safe_text
from .spec_validation import validate_draft as short_draft, validate_text
from .rule_config import validate_value as short_value
from .engine import load_rules

KEYS=('norm_text','norm_segments','historical_norm_sha256','template_draft','template_import','template_modes','template_values','template_touched','template_name','template_receipt','spec_text','ai_draft','ai_receipt','draft_modes','draft_values','draft_edited','workbench','page_layout_draft')

def receipt(data):
    if data is None:return
    exact(data,('kind','model','timestamp_utc'),'解析来源摘要')
    require(data['kind'] in ('real_api','mock_api') and data['model'] in ('deepseek-flash','deepseek-v4-pro'),'历史解析来源无效')
    safe_text(data['timestamp_utc'],40)

def validate_editor(data, rules_path):
    exact({k:v for k,v in data.items() if k not in ('workbench','page_layout_draft')},[k for k in KEYS if k not in ('workbench','page_layout_draft')],'编辑草稿')
    if data.get('page_layout_draft') is not None:
        from .page_policy import validate
        d=data['page_layout_draft'];exact({k:v for k,v in d.items() if k!='explicit'},('enabled','policy','input_sha256','regions'),'页码方案草稿');require(type(d.get('explicit',False)) is bool,'页码方案选择无效');require(type(d['enabled']) is bool and type(d['regions']) is list and len(d['regions'])<=60,'页码草稿容量无效');validate(d['policy'])
        from .project import hash_value
        hash_value(d['input_sha256'])
    if 'workbench' in data:
        from .rule_bundle import validate_state
        data['workbench']=validate_state(data['workbench'],load_rules(rules_path))
    require(type(data['norm_text']) is str and len(data['norm_text'])<=12000,'规范摘录超限')
    validate_segments(data['norm_segments'])
    require('\n'.join(x for x in data['norm_text'].splitlines() if x.strip())=='\n'.join(x['text'] for x in data['norm_segments']) or not data['norm_segments'],'规范摘录与来源不一致')
    if data['norm_text']:safe_text(data['norm_text'],12000)
    if data['template_draft'] is not None:validate_draft(data['template_draft'],data['norm_segments'])
    if data['template_import'] is not None:validate_template(data['template_import'],load_rules(rules_path))
    fields=field_map(data['template_import'] or data['template_draft'] or {})
    require(type(data['template_modes']) is dict and set(data['template_modes'])==set(fields) and all(v in ('choose','ai','manual','default','imported','disabled') for v in data['template_modes'].values()),'模板编辑模式无效')
    require(type(data['template_values']) is dict and set(data['template_values'])<=set(fields),'模板草稿值无效')
    for name,value in data['template_values'].items():
        require(data['template_modes'][name]!='disabled' or '__' in name or name=='content_checks','旧模板字段不能禁用')
        validate_value(name,value)
    require(type(data['template_touched']) is list and all(type(n) is str and n in fields for n in data['template_touched']),'模板人工编辑字段无效')
    safe_text(data['template_name'],80)
    receipt(data['template_receipt']);receipt(data['ai_receipt'])
    if data['historical_norm_sha256'] is not None:
        from .project import hash_value
        hash_value(data['historical_norm_sha256'])
    require(data['template_draft'] is None or data['template_receipt'] is not None,'解析草稿缺少历史来源')
    require(data['ai_draft'] is None or data['ai_receipt'] is not None,'短规范草稿缺少历史来源')
    if data['spec_text']:validate_text(data['spec_text'])
    else:require(type(data['spec_text']) is str,'短规范无效')
    if data['ai_draft'] is not None:short_draft(data['ai_draft'],data['spec_text'])
    exact(data['draft_modes'],('R05','R06'),'短规范模式')
    exact(data['draft_values'],('R05','R06'),'短规范草稿值')
    require(all(m in ('choose','ai','manual','default') for m in data['draft_modes'].values()),'短规范模式无效')
    for rid,value in data['draft_values'].items():short_value(rid,value)
    require(type(data['draft_edited']) is list and all(x in ('R05','R06') for x in data['draft_edited']),'短规范人工编辑字段无效')
    return data
