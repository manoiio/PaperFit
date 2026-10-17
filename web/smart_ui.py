"""Only the intelligent entry; local shortcuts live inside the five-step workbench."""
def render_smart(model,root,load_builtin,upload_changed,render_results):
    from .onepass_ui import render_onepass
    return render_onepass(model,root,load_builtin,upload_changed,render_results)
