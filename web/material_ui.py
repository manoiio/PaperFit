import streamlit as st
from .session import public_error

def render_materials(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('附录特殊材料排除 · 明确保留代码与数据'):
  st.caption('明确排除后，批量/逐项分类不能把这些段落改为普通文字。下一轮和项目恢复保留。解除需要明确确认；不改变文档内容。')
  prefix=model.task_dir.name+'-'+str(model.revision)
  numbers=st.multiselect('明确选择需保护的材料段落',[int(n) for n in model.paragraph_types],format_func=lambda n:f'段{n} · '+model.inventory['paragraphs'][n-1]['text'][:45],key='material-ids-'+prefix)
  ranges=st.text_input('或输入材料编号范围',key='material-range-'+prefix)
  try:chosen=sorted(set(numbers+model.parse_paragraph_ranges(ranges)))
  except Exception as e:st.warning(public_error(e));chosen=[]
  reason=st.selectbox('材料排除原因',['程序代码/代码空白须保留','数据/运行输出','图表/公式/嵌入或其他特殊材料','用途尚未确定'],key='material-reason-'+prefix)
  st.caption(f'将明确保护{len(chosen)}个段落；表格单元格仍不属于顶层编号。')
  st.button('确认排除并保护所选材料',disabled=not chosen,on_click=lambda:guard(lambda:model.exclude_materials(chosen,reason)))
  if model.material_exclusions:
   st.dataframe([{'段落':int(n),'保护原因':why,'范围':'不纳入普通文字；批量分类不会覆盖'} for n,why in model.material_exclusions.items()],hide_index=True,width='stretch')
   release=st.multiselect('明确选择要解除保护的段落',list(model.material_exclusions),key='material-release-'+prefix)
   ack=st.checkbox('已核对并确认解除上述材料保护',key='material-ack-'+prefix)
   st.button('解除所选材料保护（不自动改分类）',disabled=not release or not ack,on_click=lambda:guard(lambda:model.release_materials(release,acknowledged=ack)))
