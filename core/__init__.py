"""论文有格本地核心：显式范围、格式修改、另存复查；可选预览与排版辅助。"""
from .engine import inspect_document, check_document, fix_document, verify_document, load_rules, load_custom_rules

__all__ = ['inspect_document', 'check_document', 'fix_document', 'verify_document', 'load_rules', 'load_custom_rules']

from .classification import suggest_paragraph_types, TYPES
from .engine import effective_rules

__all__ += ['suggest_paragraph_types', 'effective_rules', 'TYPES']

from .layout import suggest_figure_pairs, apply_figure_layout, suggest_pagination_aids, apply_pagination_layout
from .preview import render_preview
__all__ += ['suggest_figure_pairs', 'apply_figure_layout', 'render_preview']

__all__ += ['suggest_pagination_aids', 'apply_pagination_layout']

from .widths import check_widths, apply_width_adaptation
__all__ += ['check_widths', 'apply_width_adaptation']

from .table_text import inventory as inspect_tables, validate_scope as validate_table_scope
__all__ += ['inspect_tables','validate_table_scope']

from .front import inventory as inspect_front, validate_scope as validate_front_scope
__all__ += ['inspect_front','validate_front_scope']

from .captions import inventory as inspect_captions
from .caption_move import apply_caption_positions
__all__ += ['inspect_captions','apply_caption_positions']
