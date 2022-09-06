from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pycocotools.coco as coco


import datasets.eval_protocals.kidpath_circle as kidpath_circle
from datasets.eval_protocals.circle_eval import CIRCLEeval
from pycocotools.cocoeval import COCOeval

import numpy as np
import json
import os

import torch.utils.data as data


class Grapes(data.Dataset):
    num_classes = 2
    default_resolution = [1024, 576]
    mean = np.array([0.40789654, 0.44719302, 0.47026115],
                    dtype=np.float32).reshape(1, 1, 3)
    std = np.array([0.28863828, 0.27408164, 0.27809835],
                   dtype=np.float32).reshape(1, 1, 3)

    def __init__(self, opt, split):
        super(Grapes, self).__init__()
        self.data_dir = os.path.join(opt.data_dir, 'grapes')
        self.img_dir = os.path.join(self.data_dir, '{}'.format(split))  # os.path.join(self.data_dir, '{}'.format(split))
        if opt.task == 'exdet':
            self.annot_path = os.path.join(
                self.data_dir, 'grapes_{}.json'.format(split))
        else:
            self.annot_path = os.path.join(
                self.data_dir, 'grapes_{}.json'.format(split))
        self.max_objs = 1000
        self.class_name = [
            '__background__', 'complete', 'uncomplete']
        self._valid_ids = [1, 2]
        self.cat_ids = {v: i for i, v in enumerate(self._valid_ids)}
        self.voc_color = [(v // 32 * 64 + 64, (v // 8) % 4 * 64, v % 8 * 32) \
                          for v in range(1, self.num_classes + 1)]
        self._data_rng = np.random.RandomState(123)
        self._eig_val = np.array([0.2141788, 0.01817699, 0.00341571],
                                 dtype=np.float32)
        self._eig_vec = np.array([
            [-0.58752847, -0.69563484, 0.41340352],
            [-0.5832747, 0.00994535, -0.81221408],
            [-0.56089297, 0.71832671, 0.41158938]
        ], dtype=np.float32)
        # self.mean = np.array([0.485, 0.456, 0.406], np.float32).reshape(1, 1, 3)
        # self.std = np.array([0.229, 0.224, 0.225], np.float32).reshape(1, 1, 3)

        self.split = split
        opt.default_resolution = self.default_resolution
        self.opt = opt

        print('==> initializing Grapes 2022 {} data.'.format(split))
        self.coco = coco.COCO(self.annot_path)
        self.images = self.coco.getImgIds()
        self.num_samples = len(self.images)

        self.circle = kidpath_circle.CIRCLE(self.annot_path)
        self.images_circle = self.circle.getImgIds()
        self.num_samples_circle = len(self.images_circle)

        print('Loaded {} {} samples'.format(split, self.num_samples))

    def _to_float(self, x):
        return float("{:.2f}".format(x))

    def convert_eval_format(self, all_bboxes):
        # import pdb; pdb.set_trace()
        detections = []
        for image_id in all_bboxes:
            for cls_ind in all_bboxes[image_id]:
                category_id = self._valid_ids[cls_ind - 1]
                for bbox in all_bboxes[image_id][cls_ind]:
                    bbox[2] -= bbox[0]
                    bbox[3] -= bbox[1]
                    score = bbox[4]
                    bbox_out = list(map(self._to_float, bbox[0:4]))

                    detection = {
                        "image_id": int(image_id),
                        "category_id": int(category_id),
                        "bbox": bbox_out,
                        "score": float("{:.2f}".format(score))
                    }
                    if len(bbox) > 5:
                        extreme_points = list(map(self._to_float, bbox[5:13]))
                        detection["extreme_points"] = extreme_points
                    detections.append(detection)
        return detections

    def convert_eval_circle_format(self, all_circles):
        # import pdb; pdb.set_trace()
        detections = []
        for image_id in all_circles:
            for cls_ind in all_circles[image_id]:
                try:
                    category_id = self._valid_ids[cls_ind - 1]
                except:
                    aaa  =1
                for circle in all_circles[image_id][cls_ind]:
                    score = circle[3]
                    circle_out = list(map(self._to_float, circle[0:3]))

                    detection = {
                        "image_id": int(image_id),
                        "category_id": int(category_id),
                        "score": float("{:.2f}".format(score)),
                        'circle_center': [circle_out[0], circle_out[1]],
                        'circle_radius': circle_out[2]
                    }
                    if len(circle) > 5:
                        extreme_points = list(map(self._to_float, circle[5:13]))
                        detection["extreme_points"] = extreme_points

                    # output_h = 512  # hard coded
                    # output_w = 512  # hard coded
                    # cp = [0, 0]
                    # cp[0] = circle_out[0]
                    # cp[1] = circle_out[1]
                    # cr = circle_out[2]
                    # if cp[0] - cr < 0 or cp[0] + cr > output_w:
                    #     continue
                    # if cp[1] - cr < 0 or cp[1] + cr > output_h:
                    #     continue

                    detections.append(detection)
        return detections

    def __len__(self):
        return self.num_samples

    def save_results(self, results, save_dir):
        json.dump(self.convert_eval_format(results),
                  open('{}/results.json'.format(save_dir), 'w'))

    def run_eval(self, results, save_dir):
        # result_json = os.path.join(save_dir, "results.json")
        # detections  = self.convert_eval_format(results)
        # json.dump(detections, open(result_json, "w"))
        # coco_dets = results
        # print(results)
        self.save_results(results, save_dir)
        coco_dets = self.coco.loadRes('{}/results.json'.format(save_dir))
        coco_eval = COCOeval(self.coco, coco_dets, "bbox")
        coco_eval.evaluate()
        coco_eval.accumulate()
        coco_eval.summarize()


    def save_circle_results(self, results, save_dir):
        json.dump(self.convert_eval_circle_format(results),
                  open('{}/results.json'.format(save_dir), 'w'))

    def run_circle_eval(self, results, save_dir):
        # result_json = os.path.join(save_dir, "results.json")
        # detections  = self.convert_eval_format(results)
        # json.dump(detections, open(result_json, "w"))
        self.save_circle_results(results, save_dir)
        circle_dets = self.circle.loadRes('{}/results.json'.format(save_dir))
        circle_eval = CIRCLEeval(self.circle, circle_dets, "circle")
        # circle_eval = CIRCLEeval(self.circle, circle_dets, "circle_box")
        circle_eval.evaluate()
        circle_eval.accumulate()
        circle_eval.summarize()
