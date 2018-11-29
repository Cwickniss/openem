import numpy as np
import pandas as pd
from typing import List
import pickle
import os

NB_FOLDS = 4

def video_clips(config, is_test=False) -> {str}:
    if is_test:
        return video_clips_test(config)

    clips = {}
    for dir_name in os.listdir(config.train_imgs_dir()):
        clip_dir = os.path.join(config.train_imgs_dir(), dir_name)
        frames = []
        for frame_name in os.listdir(clip_dir):
            if not frame_name.endswith('.jpg'):
                continue
            frames.append(frame_name[:-len('.jpg')])
        clips[dir_name] = frames
    return clips


def video_clips_test(config) -> {str}:
    clips = {}
    for dir_name in os.listdir(config.test_imgs_dir()):
        clip_dir = os.path.join(config.test_imgs_dir(), dir_name)
        frames = []
        for frame_name in os.listdir(clip_dir):
            if not frame_name.endswith('.jpg'):
                continue
            frames.append(frame_name[:-len('.jpg')])
        clips[dir_name] = frames
    return clips


def fold_test_video_ids(fold: int) -> List[str]:
    all_video_ids = sorted(video_clips().keys())

    if fold == 0:
        return []
    return all_video_ids[(fold-1)::NB_FOLDS]


def image_fn(config, video_id, frame, is_test=False):
    if is_test:
        return '{}/{}/{:04}.jpg'.format(
                config.test_imgs_dir(), 
                video_id, 
                int(frame))
    else:
        return '{}/{}/{:04}.jpg'.format(
                config.train_imgs_dir(), 
                video_id, 
                int(frame))


def image_crop_fn(config, video_id, frame, is_test=False):
    if is_test:
        return '{}/{}/{:04}.jpg'.format(
                config.test_roi_imgs_dir(), 
                video_id, 
                int(frame))
    else:
        return '{}/{}/{:04}.jpg'.format(
                config.train_roi_imgs_dir(), 
                video_id, 
                int(frame))
