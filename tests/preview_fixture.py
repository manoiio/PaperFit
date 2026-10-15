"""Portable fake renderer configuration, for mock-only cache/timeout tests."""
from copy import deepcopy
from core.preview import CONFIG
from core.package import sha256
import json
def configuration():
 data={**deepcopy(CONFIG),'renderer':'mock-only test renderer','renderer_version':'test','bundle':'mock','renderer_script_sha256':'0'*64,'font_environment_sha256':'1'*64}
 return data,sha256(json.dumps(data,sort_keys=True).encode())
