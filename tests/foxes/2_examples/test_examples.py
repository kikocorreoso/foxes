from pathlib import Path
import inspect
import argparse
import os

from foxes.utils import load_module

thisdir = Path(inspect.getfile(inspect.currentframe())).parent


def test():
    rdir = thisdir.parent.parent.parent / "examples/foxes"
    rpath = rdir / "run_all.py"
    print(rpath)

    run_all = load_module("run_all", rpath)

    args = argparse.Namespace()
    args.include = None
    args.exclude = []
    args.incopt = False
    args.forceopt = False
    args.step = 0
    args.dry = False
    args.Dry = False
    args.nofig = True

    os.chdir(rdir)
    run_all.run(args)


if __name__ == "__main__":
    test()
