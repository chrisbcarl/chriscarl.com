'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2024-11-26
Description:

Given an SVG, convert it into a json
'''
import argparse
import os
import json
import subprocess
import xml.etree.ElementTree as et


def main(filepath):
    '''
    arguments:
        filepath: str
            the svg you want to convert, you get a .js with the same name and same directory
    '''
    basename = os.path.basename(filepath)
    dirname = os.path.dirname(filepath)
    filename = os.path.splitext(basename)[0]
    js_filepath = os.path.join(dirname, f'{filename}.js')
    print(f'reading "{filepath}"')
    tree = et.parse(filepath)
    root = tree.getroot()
    paths = []
    for path in root:
        paths.append(path.attrib)
    print(f'writing "{js_filepath}"')
    with open(js_filepath, 'w', encoding='utf-8') as w:
        # w.write(f'version = "{root.attrib["version"]}"\n')
        w.write(f'viewBox = "{root.attrib["viewBox"]}"\n')
        w.write('paths = [\n')
        for path in paths:
            w.write(f'    {json.dumps(path)},\n')
        w.write(']\n')
        w.write('msg = `${paths.length} paths discovered`\n')
        w.write('console.log(msg)\n')
    print(f'invoking "{js_filepath}"')
    subprocess.check_call(['node', js_filepath])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath')

    args = parser.parse_args()
    args.filepath = os.path.abspath(args.filepath)

    main(args.filepath)
