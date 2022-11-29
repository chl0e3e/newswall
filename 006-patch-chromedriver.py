#!/usr/bin/env python3
import sys
import os

print("getting build vars")
from buildutil import get_build_var
chromedriver_path = get_build_var("chromedriver")

# import the patcher
print("importing patcher")
from uc import patcher

print("creating patcher instance")
patcher_inst = patcher.Patcher(executable_path=chromedriver_path)
print(patcher_inst)

print("checking chromedriver patched")
patched = patcher_inst.is_binary_patched()
print("patched: %s" % (str(patched)))

if not patched:
    print("patching chromedriver binary")
    linect = patcher_inst.patch_exe()
    print("patch result: %d" % (linect))

    if linect != 0:
        print("patched successfully!")
        sys.exit(0)
    else:
        print("could not patch chromedriver")
        sys.exit(2)