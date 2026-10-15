import importlib.util, os, sys
def load():
    T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if T not in sys.path: sys.path.insert(0, T)
    sp = importlib.util.spec_from_file_location("prompt_v3_r3", os.path.join(T, "prompt_v3.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
