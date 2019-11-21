from keras_retinanet.models.resnet import custom_objects

import tensorflow as tf

from openem.models import ImageModel

import cv2

from openem.Detect import Detection

class SubtractMeanImage:
    """ Subtract a mean image from the input
        Meets the callable interface of openem.Detect.Preprocessor
    """
    def __init__(self,meanImage):
        self.mean_image = meanImage

    def __call__(self, image, requiredWidth, requiredHeight):
        resized_image = cv2.resize(image, (requiredWidth, requiredHeight))
        for dim in [0,1,2]:
            resized_image[:,:,dim] -= self.mean_image[:,:,dim]
        return resized_image

NETWORK_IMAGE_SHAPE=(720,1280)  
class RetinaNetDetector(ImageModel):
    def __init__(self, modelPath, meanImage, gpuFraction=1.0):

        # TODO: Get network output prior to NMS to support
        # batch operations
        super(RetinaNetDetector,self).__init__(modelPath,
                                               gpuFraction,
                                               'input_1:0',
                                               'nms/ExpandDims:0')
        self.input_shape[1:3] = NETWORK_IMAGE_SHAPE
        
        resized_mean = cv2.resize(meanImage,(NETWORK_IMAGE_SHAPE[1],
                                             NETWORK_IMAGE_SHAPE[0]))
        self.preprocessor=SubtractMeanImage(resized_mean)
        self._imageSizes = None

    def addImage(self, image):
        if self._imageSizes is None:
            self._imageSizes = []
        if len(self._imageSizes) >= 1:
            raise Exception('RetinaNet does not support batching (yet)')
        self._imageSizes.append(image.shape)
        return super(RetinaNetDetector, self)._addImage(image,
                                                        self.preprocessor)

    def process(self, threshold=0.0):
        detections = super(RetinaNetDetector,self).process()

        # clip to image shape
        detections[:, :, 0] = np.maximum(0, detections[:, :, 0])
        detections[:, :, 1] = np.maximum(0, detections[:, :, 1])
        detections[:, :, 2] = np.minimum(image_dims[1], detections[:, :, 2])
        detections[:, :, 3] = np.minimum(image_dims[0], detections[:, :, 3])

        num_images = detections.shape[0]
        for idx in range(num_images):
            # correct boxes for image scale
            h_scale = NETWORK_IMAGE_SHAPE[0] / self.imageSizes[idx][0]
            w_scale = NETWORK_IMAGE_SHAPE[1] / self.imageSizes[idx][1]
            
            detections[idx, :, 0] /= w_scale
            detections[idx, :, 1] /= h_scale
            detections[idx, :, 2] /= w_scale
            detections[idx, :, 3] /= h_scale
            

        # change to (x, y, w, h) (MS COCO standard)
        detections[:, :, 2] -= detections[:, :, 0]
        detections[:, :, 3] -= detections[:, :, 1]

        results=[]
        # compute predicted labels and scores
        for detection in detections[0, ...]:
            label = np.argmax(detection[4:])
            confidence = float(detection[4 + label])
            if confidence > threshold:
                detection = Detection(location=detection[:4],
                                      confidence=confidence,
                                      species=label,
                                      frame=None,
                                      video_id=None)
                results.append(detection)
            
        self._imageSizes = None
        return results

            