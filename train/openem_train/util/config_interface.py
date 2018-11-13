import os
import glob
import configparser

class ConfigInterface:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def work_dir(self):
        return self.config.get('Paths', 'WorkDir')

    def train_dir(self):
        return self.config.get('Paths', 'TrainDir')

    def num_classes(self):
        return self.config.getint('Data', 'NumClasses')

    def detect_width(self):
        return self.config.getint('Detect', 'Width')

    def detect_height(self):
        return self.config.getint('Detect', 'Height')

    def detect_batch_size(self):
        return self.config.getint('Detect', 'BatchSize')

    def detect_val_batch_size(self):
        return self.config.getint('Detect', 'ValBatchSize')

    def detect_num_epochs(self):
        return self.config.getint('Detect', 'NumEpochs')

    def train_vids(self):
        patt = os.path.join(self.train_dir(), 'train_videos', '*.mp4')
        return glob.glob(patt)

    def test_vids(self):
        patt = os.path.join(self.train_dir(), 'test_videos', '*.mp4')
        return glob.glob(patt)

    def no_fish_examples(self):
        patt = os.path.join(self.train_dir(), 'cover', 'no_fish', '*.jpg')
        return glob.glob(patt)

    def clear_examples(self):
        patt = os.path.join(self.train_dir(), 'cover', 'clear', '*.jpg')
        return glob.glob(patt)

    def covered_examples(self):
        patt = os.path.join(self.train_dir(), 'cover', 'covered', '*.jpg')
        return glob.glob(patt)

    def train_ann_path(self):
        return os.path.join(self.train_dir(), 'train_annotations.csv')

    def train_imgs_dir(self):
        return os.path.join(self.work_dir(), 'train_imgs')

    def test_imgs_dir(self):
        return os.path.join(self.work_dir(), 'test_imgs')

    def train_roi_imgs_dir(self):
        return os.path.join(self.work_dir(), 'train_roi_imgs')

    def test_roi_imgs_dir(self):
        return os.path.join(self.work_dir(), 'test_roi_imgs_dir')

    def checkpoints_dir(self):
        return os.path.join(self.work_dir(), 'checkpoints')

    def checkpoint_best(self):
        fname = "checkpoint-best-{epoch:03d}-{val_loss:.4f}.hdf5"
        return os.path.join(self.checkpoints_dir(), fname)

    def checkpoint_periodic(self):
        fname = "checkpoint-{epoch:03d}-{val_loss:.4f}.hdf5"
        return os.path.join(self.checkpoints_dir(), fname)

    def tensorboard_dir(self):
        return os.path.join(self.work_dir(), 'tensorboard')

    def ruler_points(self):
        return os.path.join(self.work_dir(), 'ruler_points.csv')
