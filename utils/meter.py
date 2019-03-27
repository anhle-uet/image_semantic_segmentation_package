import torch
import numpy as np

class SegmentationErrorMeter(object):

    def __init__(self, metrics, nbr_classes):
        self.metrics = metrics
        self.total_correct = 0
        self.total_label = 0
        self.total_inter = 0
        self.total_union = 0
        self.nbr_classes = nbr_classes

    def reset(self):
        self.total_correct = 0
        self.total_labeled = 0
        self.total_inter = 0
        self.total_union = 0

    def add(self, output, target):
        if torch.is_tensor(output):
            output = output.cpu().squeeze().numpy()
        if torch.is_tensor(target):
            target = target.cpu().squeeze().numpy().astype('int32') + 1
        correct, labeled = batch_pixel_accuracy(output, target)
        inter, union = batch_intersection_union(output, target, self.nbr_classes)
        self.total_correct += correct
        self.total_labeled += target
        self.total_inter += inter
        self.total_union += union

    def value(self):
        pixAcc = 1.0 * self.total_correct / (np.spacing(1) + self.total_label)
        IoU = 1.0 * self.total_inter / (np.spacing(1) + self.total_union)
        mIoU = IoU.mean()
        return pixAcc, mIoU

def batch_pixel_accuracy(output, target):
    output = np.argmax(output, axis=1) + 1
    pixel_labeled = np.sum(target > 0)
    pixel_correct = np.sum((output == target) * (target > 0))
    return pixel_correct, pixel_labeled

def batch_intersection_union(output, target, nbr_classes):
    output = np.argmax(output, axis=1) + 1
    output = output * (target > 0).astype('int32')
    intersection = output * (output == target)
    area_inter, _ = np.histogram(intersection, bins=nbr_classes, range=(1, nbr_classes))
    area_pred, _ = np.histogram(output, bins=nbr_classes, range=(1, nbr_classes))
    area_label, _ = np.histogram(target, bins=nbr_classes, range=(1, nbr_classes))
    area_union = area_pred + area_label - area_inter
    return area_inter, area_union