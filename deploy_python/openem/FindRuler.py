""" Module for finding ruler masks in raw images """
import numpy as np
import cv2

from openem.models import ImageModel
from openem.models import Preprocessor

class RulerMaskFinder(ImageModel):
    """ Class for finding ruler masks from raw images """
    preprocessor=Preprocessor(1.0/128.0,
                              np.array([-1,-1,-1]),
                              True)

    def addImage(self, image):
        """ Add an image to process in the underlying ImageModel after
            running preprocessing on it specific to this model.

        image: np.ndarray the underlying image (not pre-processed) to add
               to the model's current batch
        """
        return self._addImage(image, self.preprocessor)

    def process(self):
        """ Runs the base ImageModel and does a high-pass filter only allowing
            matches greater than 127 to make it into the resultant mask

        Returns the mask of the ruler in the size of the network image,
        the user must resize to input image if different.
        """
        model_masks = super(RulerMaskFinder,self).process()
        if model_masks is None:
            return None

        mask_images = []
        num_masks = model_masks.shape[0]
        for idx in range(num_masks):
            # Tensorflow output is 0 to 1
            scaled_image = model_masks[idx] * 255
            ret, mask_image = cv2.threshold(scaled_image,
                                            127,
                                            255,
                                            cv2.THRESH_BINARY)
            blurred_image = cv2.medianBlur(mask_image,5)
            mask_images.append(blurred_image)

        return np.array(mask_images)

def rulerPresent(image_mask):
    """ Returns true if a ruler is present in the frame """
    return cv2.sumElems(image_mask)[0] > 1000.0

def rulerEndpoints(image_mask):
    """
    Find the ruler end points given an image mask
    image_mask: 8-bit single channel image_mask
    """
    image_height = image_mask.shape[0]

    image_mask = image_mask.astype(np.float64)
    image_mask /= 255.0

    # Find center of rotation of the mask
    moments = cv2.moments(image_mask)
    centroid_x = moments['m10'] / moments['m00']
    centroid_y = moments['m01'] / moments['m00']
    centroid = (centroid_x, centroid_y)

    # Find the transofrm to translate the image to the
    # center of the of the ruler
    center_y = image_mask.shape[0] / 2.0
    center_x = image_mask.shape[1] / 2.0
    center = (center_x, center_y)

    diff_x = center_x - centroid_x
    diff_y = center_y - centroid_y

    translation=np.array([[1,0,diff_x],
                         [0,1,diff_y],
                         [0,0,1]])

    min_moment = float('+inf')
    best = None
    best_angle = None
    for angle in np.linspace(-90,90,181):
        rotation = cv2.getRotationMatrix2D(centroid,
                                           float(angle),
                                           1.0)
        # Matrix needs bottom row added
        # Warning: cv2 dimensions are width, height not height, width!
        rotation = np.vstack([rotation, [0,0,1]])
        rt_matrix = np.matmul(translation,rotation)
        rotated = cv2.warpAffine(image_mask,
                                 rt_matrix[0:2],
                                 (image_mask.shape[1],
                                  image_mask.shape[0]))

        rotated_moments = cv2.moments(rotated)
        if rotated_moments['mu02'] < min_moment:
            best_angle = angle
            min_moment = rotated_moments['mu02']
            best = np.copy(rt_matrix)

    #Now that we have the best rotation, find the endpoints
    warped = cv2.warpAffine(image_mask,
                            best[0:2],
                            (image_mask.shape[1],
                             image_mask.shape[0]))

    # Reduce the image down to a 1d line and up convert to 64-bit
    # float between 0 and 1
    col_sum = cv2.reduce(warped,0, cv2.REDUCE_SUM).astype(np.float64)

    # Find the left/right of masked region in the line vector
    # Then, knowing its the center of the transformed image
    # back out the y coordinates in the actual image inversing
    # the transform above
    cumulative_sum = np.cumsum(col_sum[0])
    # Normalize the cumulative sum from 0 to 1
    max_sum=np.max(cumulative_sum)
    cumulative_sum /= max_sum

    # Find the left,right indices based on thresholds
    left_idx = np.searchsorted(cumulative_sum, 0.06, side='left')
    right_idx = np.searchsorted(cumulative_sum, 0.94, side='right')
    width = right_idx - left_idx

    # Add 10% of the ruler width
    left_idx = left_idx-(width*0.10)
    right_idx = right_idx+(width*0.10)

    endpoints=np.array([[[left_idx, image_height / 2],
                         [right_idx, image_height / 2]]])
    # Finally inverse the transform to get the actual y coordinates
    inverse = cv2.invertAffineTransform(best[0:2])
    inverse = np.vstack([inverse, [0,0,1]])
    return cv2.perspectiveTransform(endpoints, inverse)[0]

def crop(image, roi):
    """ Returns a *copy* of the region of interest from the image
    image: ndarray
           Represents image data
    roi: tuple
         (x,y,w,h) tuple -- presumably from openem.FindRuler.findRoi
    """
    x0=roi[0]
    y0=roi[1]
    x1=roi[0]+roi[2]
    x2=roi[1]+roi[3]
    cropped=np.copy(image[y0:y1,x0:x1])
