"""Real five-step UI paths used by legacy interaction regressions."""
def show(app,step,area=None,rules=False):
 app.button(key=f'workspace-nav-{step}').click().run()
 if area is not None:
  app.button(key='enter-scope-'+area).click().run()
 if rules:app.radio(key='workspace-rule-entry').set_value('导入规则包 / 编辑规则').run()
 return app

def click(app,label):
 ranges=('确认正文范围','开始检查','确认分类并应用范围','核对完成并开始检查','应用分类调整')
 selection=('选择全部可修正问题','清空选择','选择本页可修正项')
 if label.startswith('使用') or label in ('重新开始',):show(app,1)
 elif label in ranges:show(app,2,'paragraph')
 elif label in selection:show(app,3)
 elif label in ('生成修正版','预演所选修正'):show(app,4)
 elif label.startswith('以本轮') or label.startswith('以计划'):show(app,5)
 elif label in ('填入示例B','解析要求','确认并应用','切换回默认演示规则','沿用已记录的真实解析B','导入演示规范A（TXT）','已核对，确认待发送文本','解析R01–R07要求','确认并应用完整模板'):show(app,1,rules=True)
 next(b for b in app.button if b.label==label).click().run()
 return app
