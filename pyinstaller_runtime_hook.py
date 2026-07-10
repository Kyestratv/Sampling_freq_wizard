import os
import sys


base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
tcl_root = os.path.join(base_dir, "runtime_tcl")

os.environ["TCL_LIBRARY"] = os.path.join(tcl_root, "tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(tcl_root, "tk8.6")
