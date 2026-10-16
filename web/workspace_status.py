"""Read-only labels from existing state; observed history is UI-local, never authority."""
from pathlib import Path
from core.package import sha256


def input_label(model):
    return '原稿' if model.current_round == 0 else f'第{model.current_round}轮副本'


def check_status(model, observed=False):
    if model.inventory is None:
        return '尚未载入文件', 'neutral'
    if model.report is not None and model.confirmed is not None:
        return '已有有效检查', 'ready'
    if observed:
        return '原检查当前不可用 · 请重新核对并检查', 'attention'
    if model.confirmed is not None:
        return '范围已确认 · 尚未检查', 'neutral'
    return '范围待核对 · 尚未检查', 'neutral'


def latest_output(model):
    """Record identity is distinct from download availability and input identity."""
    result = model.result or (model.history[-1]['result'] if model.history else None)
    if not result:
        return None
    digest = result['output_body_manifest']['input_sha256']
    path = Path(result['output'])
    try:
        valid = path.is_file() and sha256(path.read_bytes()) == digest
    except OSError:
        valid = False
    number = result['round']['number']
    current = bool(model.inventory and model.current_round == number and model.inventory['input_sha256'] == digest)
    relation = '已是当前输入' if current else '与当前输入不同'
    return {'number': number, 'current': current, 'available': valid,
            'label': f'最新正式记录：第{number}轮 · ' + (relation if valid else '文件不可用，须核对')}


def output_relation(model, number):
    latest = latest_output(model)
    if latest and latest['number'] == number and latest['current'] and latest['available']:
        return f'当前处理输入已是第{number}轮副本。查看记录不会再次切换输入。'
    return f'当前处理输入：{input_label(model)}。第{number}轮输出与当前输入分开；仅明确点击继续处理才切换。'


def pending_rehearsal(model):
    r = model.rehearsal
    return bool(r and r.get('view') and not (r.get('adopted_round') or r.get('adopted_rounds')))


def view_label(model, step, ui):
    if not model.inventory:
        return None
    seed = model.task_dir.name
    if step == 4:
        return '尚未采用的预演记录' if pending_rehearsal(model) else '已采用的修正记录' if model.rehearsal else '本次明确选择'
    if step == 5 and ui.get('reader-open-' + seed):
        if ui.get('reader-section-' + seed) == '排版辅助':
            return '排版辅助（输入由下方明确选择）'
        request = ui.get('reader-request-' + seed)
        compare = request['compare'] if request else ui.get('reader-mode-' + seed) == '并排对比'
        def name(key):
            if key == 'original': return '原稿'
            if key == 'input': return '当前输入（' + input_label(model) + '）'
            if isinstance(key, str) and key.startswith('round-') and key[6:].isdigit(): return '第' + key[6:] + '轮副本'
            return '待选择文件'
        target = request.get('target') if request else None
        return (name('original' if request else ui.get('reader-left-' + seed, 'original')) + ' / ' + name(target or ui.get('reader-right-' + seed, 'input'))) if compare else name(target or ui.get('reader-file-' + seed, 'input'))
    if step == 5 and ui.get('history-view-' + str(model.revision)) and model.history:
        key = ui.get('history-object-' + seed, model.history[0]['stem'])
        h = next((h for h in model.history if h['stem'] == key), None)
        if h: return f"历史第{h['result']['round']['number']}轮记录（不切换输入）"
    if step in (3, 5):
        return f"第{model.result['round']['number']}轮输出记录" if model.result else '当前输入的检查记录'
    return None
