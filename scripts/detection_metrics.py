#!/usr/bin/env python3

""" Generate statistics on detections given a truth file + a detect inference output

This script sweeps across different keep thresholds based on the provided
CLI arguments (`--keep-threshold-[min,max,steps]`) and generates a
precision/recall graph. It also calculates 'double count' metric which is
the number of boxes that matched a truth box, but already had a box associated
with it. Imagine two boxes around the same object, with slightly different
confidences.

The True Positive is based on the IoU of the detection box against the truth
data. If the detection box is not within the IoU threshold of the truth it is
counted as a false positive.

The false negatives are calculated per frame, such that if a frame has 4 truth
detections, but 2 inference detections, 2 false negatives are added to the
metric.

"""

import argparse
import pandas as pd
import progressbar
import numpy as np
import pickle
from pprint import pprint

def _rowToBoxDict(row):
    """ Converts a row from a csv to a dictionary """
    box_dict={}
    box_dict['x'] = row.x
    box_dict['y'] = row.y
    # Support both row formats for detect versus truth
    try:
        box_dict['w'] = row.width
        box_dict['h'] = row.height
        box_dict['species'] = row.species_id
    except:
        box_dict['w'] = row.w
        box_dict['h'] = row.h
        box_dict['species'] = row.det_species
    return box_dict
def _intersection_over_union(boxA, boxB):
    """ Computes intersection over union for two bounding boxes.
        Inputs:
        boxA -- First box. Must be a dict containing x, y, w, h.
        boxB -- Second box. Must be a dict containing x, y, w, h.
        Return:
        Intersection over union.
    """
    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(int(boxA["x"]), int(boxB["x"]))
    yA = max(int(boxA["y"]), int(boxB["y"]))
    xB = min(int(boxA["x"]) + int(boxA["w"]), int(boxB["x"]) + int(boxB["w"]))
    yB = min(int(boxA["y"]) + int(boxA["h"]), int(boxB["y"]) + int(boxB["h"]))

    # compute the area of intersection rectangle
    interX = xB - xA + 1
    interY = yB - yA + 1
    if interX < 0 or interY < 0:
        iou = 0.0
    else:
        interArea = float((xB - xA + 1) * (yB - yA + 1))
        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = int(boxA["w"]) * int(boxA["h"])
        boxBArea = int(boxB["w"]) * int(boxB["h"])

        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        if float(boxAArea + boxBArea - interArea) <= 0.0:
            return 0.01
        try:
            iou = interArea / float(boxAArea + boxBArea - interArea)
        except:
            print("interArea: {}".format(interArea))
            print("Union: {}".format(float(boxAArea + boxBArea - interArea)))
        # return the intersection over union value
    return iou

def max_score(row):
    vals=np.array(str(row).split(":"))
    vals=vals.astype(np.float)
    return vals.max()

def calculateStats(truth, detections, keep_threshold, recall_by_species):
    eval_detects = detections
    eval_detects['max_score'] = eval_detects['det_conf'].transform(max_score)
    eval_detects = eval_detects.loc[eval_detects.max_score > keep_threshold]
    count = len(eval_detects)
    true_positives_by_species = {}
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    double_counts = 0

    num_of_classes=truth['species_id'].max() + 1
    confusion_matrix = np.zeros((num_of_classes,num_of_classes))
    matches={}
    # Iterate over all detections from inference over keep threshold
    # calculate true and false positives
    for idx, row in eval_detects.iterrows():
        matching_truth_df = truth.loc[(truth.video_id == row.video_id) & (truth.frame == row.frame)]
        if len(matching_truth_df) == 0:
            false_positives += 1
        else:
            got_match = False
            for truth_idx, truth_row in matching_truth_df.iterrows():
                truth_box = _rowToBoxDict(truth_row)
                canidate_box = _rowToBoxDict(row)
                iou = _intersection_over_union(truth_box, canidate_box)
                if iou > args.iou_threshold:
                    got_match = True
                    if truth_row.name in matches:
                        double_counts += 1
                    else:
                        matches[truth_row.name] = row
                    break

            if got_match == True:
                true_positives += 1
                if not truth_box['species'] in true_positives_by_species:
                    true_positives_by_species[truth_box['species']] = 0
                true_positives_by_species[truth_box['species']] += 1
                confusion_matrix[truth_box['species'],canidate_box['species']] += 1
            else:
                false_positives += 1
                confusion_matrix[0,canidate_box['species']] += 1

    # Normalize each col of the confusion_matrix
    for idx in range(num_of_classes):
        col_sum = np.sum(confusion_matrix[:,idx])
        if col_sum > 0:
            confusion_matrix[:,idx] /= col_sum

    counted=[]
    results_by_species = {}

    if recall_by_species:
        species_list=list(truth.species_id.unique())
        for species in species_list:
            species_df = truth.loc[truth.species_id==species]
            counted=[]
            #Reset these globals for each species
            false_negatives=0
            for idx, row in species_df.iterrows():
                matching_detection_df = eval_detects.loc[(eval_detects.video_id == row.video_id) & (eval_detects.frame == row.frame)]
                boxes_in_truth=species_df.loc[(species_df.video_id == row.video_id) & (species_df.frame == row.frame)]
                boxes_in_detection = matching_detection_df
                vid_tag=f"{row.video_id}_{row.frame}_{species}"
                if not vid_tag in counted:
                    # If this image hasn't been processed yet, check its detections against matches
                    counted.append(vid_tag)
                    for _, truth_row in boxes_in_truth.iterrows():
                        # Check each truth box and see if it has a det match, if not its a FN
                        match_found = False
                        truth_box = _rowToBoxDict(truth_row)
                        for _,det_row in boxes_in_detection.iterrows():
                            det_box = _rowToBoxDict(det_row)
                            if _intersection_over_union(truth_box, det_box) > args.iou_threshold:
                                match_found = True
                                break
                        if match_found is False:
                            false_negatives += 1

            # Precision is not by species (yet)
            precision = true_positives / (true_positives + false_positives)
            try:
                recall = true_positives_by_species[species] / (true_positives_by_species[species] + false_negatives)
            except:
                print(f"No true positives for {species} @ {keep_threshold}!")
                recall = 0
            print(f"Species '{species}' @ {keep_threshold}: FN = {false_negatives}")
            results_by_species[species] = (precision, recall, double_counts / true_positives)
    else:
        for idx, row in truth.iterrows():
            matching_detection_df = eval_detects.loc[(eval_detects.video_id == row.video_id) & (eval_detects.frame == row.frame)]
            boxes_in_truth=truth.loc[(truth.video_id == row.video_id) & (truth.frame == row.frame)]
            boxes_in_detection = matching_detection_df           
            vid_tag=f"{row.video_id}_{row.frame}"
            if not vid_tag in counted:
                counted.append(vid_tag)
                for _, truth_row in boxes_in_truth.iterrows():
                    # Check each truth box and see if it has a det match, if not its a FN
                    match_found = False
                    truth_box = _rowToBoxDict(truth_row)
                    for _,det_row in boxes_in_detection.iterrows():
                        det_box = _rowToBoxDict(det_row)
                        if _intersection_over_union(truth_box, det_box) > args.iou_threshold:
                            match_found = True
                            break
                    if match_found is False:
                        false_negatives += 1

        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / (true_positives + false_negatives)
        results_by_species[None] = (precision, recall, double_counts / true_positives)

    return results_by_species,confusion_matrix

if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", help="Truth CSV file")
    parser.add_argument("--keep-threshold-min",
                        type=float,
                        default=0.05,
                        help="Minimum keep threshold to scan")
    parser.add_argument("--keep-threshold-max",
                        type=float,
                        default=0.80,
                        help="Maximum keep threshold to scan")
    parser.add_argument("--keep-threshold-steps",
                        type=int,
                        default=10,
                        help="Number of steps to use between min/max")
    parser.add_argument("--iou-threshold",
                        type=float,
                        default=0.4,
                        help="IoU threshold for determining True Positive")
    parser.add_argument("--output-matrix",
                        type=str,
                        help="If supplied, dumps the matrix to a file, else just prints")
    parser.add_argument("--recall-by-species",
                        action="store_true",
                        help="Calculate recall metric using species id.")
    parser.add_argument("detect_csv", help="Inference result CSV")
    args = parser.parse_args()

    detections=pd.read_csv(args.detect_csv)
    truth = pd.read_csv(args.truth)
    results={"CONFUSION_MATRICES":{}}
    keep_thresholds = np.linspace(args.keep_threshold_min,
                                  args.keep_threshold_max,
                                  args.keep_threshold_steps)
    bar = progressbar.ProgressBar(redirect_stdout=True)
    for keep_threshold in bar(keep_thresholds):
        threshold_results, confusion_matrix = calculateStats(truth, detections, keep_threshold, args.recall_by_species)
        for species in threshold_results:
            if species not in results:
                results[species] = []
            results[species].append([keep_threshold, *threshold_results[species]])
        results["CONFUSION_MATRICES"][keep_threshold] = confusion_matrix

    pprint(results)
    if args.output_matrix:
        with open(args.output_matrix, 'wb') as output:
            pickle.dump(results, output)
