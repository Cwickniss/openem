#!/usr/bin/env python3

import os
import pandas as pd
import subprocess
import json

if __name__=="__main__":
    work_dir = os.getenv('TATOR_WORK_DIR')
    pipeline_args_str = os.getenv('TATOR_PIPELINE_ARGS')
    if pipeline_args_str:
        pipeline_args = json.loads(pipeline_args_str)
    else:
        pipeline_args = {}
    work_filepath=os.path.join(work_dir, "work.csv")

    keep_threshold = pipeline_args.get('keep_threshold', None)
    img_max_side = pipeline_args.get('img_max_side', None)
    img_min_side = pipeline_args.get('img_min_side', None)
    img_ext = pipeline_args.get('img_ext', None)
    media_type = pipeline_args.get('media_type', None)
    
    args = ['python3', '/scripts/infer.py',
            '--graph-pb', '/work/graph.pb',
            '--keep-threshold', str(keep_threshold),
            '--csv-flavor', media_type,
            '--img-base-dir', '/',
            '--img-min-side', img_min_side,
            '--img-max-side', img_max_side,
            '--img-ext', img_ext,
            '--output-csv', '/work/results.csv',
            '/work/work.csv' ]

    cmd = " ".join(args)
    print(f"Inference Command = '{cmd}'")
    p=subprocess.Popen(args)
    p.wait()
    return p.returncode
