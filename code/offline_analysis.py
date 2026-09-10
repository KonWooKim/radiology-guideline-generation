"""Execute a released analysis in its restored workspace, with model clients disabled."""
import argparse
from pathlib import Path
import runpy
import sys
from experiment import block_api_imports


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--script', required=True)
    a, extra = p.parse_known_args()
    scripts = (a.workspace/'scripts').resolve()
    path = (scripts/a.script).resolve()
    if path.parent != scripts or path.suffix != '.py' or not path.is_file():
        raise ValueError('Select a released analysis script by filename')
    if path.name.startswith('run_'):
        raise ValueError('Use experiment.py for experiment entry points')
    block_api_imports()
    # Historical analyzers write new table/figure outputs here. No manuscript
    # drafts need to be distributed just to create this output directory.
    (a.workspace/'manuscript/figures').mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(scripts))
    sys.argv = [str(path), *extra]
    runpy.run_path(str(path), run_name='__main__')


if __name__ == '__main__':
    main()
