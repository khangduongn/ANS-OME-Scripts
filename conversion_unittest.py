import unittest
from conversion import stitch_tiles, saveImages
from skimage.metrics import structural_similarity as ssim
import numpy as np
import glob
import tifffile
import os

class TestConversionMethods(unittest.TestCase):

    def testStitching(self):
        filename, imgShape, _, _ = stitch_tiles('./SAR000001_100x_BF_z_4tiles_50steps_0.59um/SAR000001_100x_BF_z_4tiles_50steps_0.59um', './Output')
        
        images = np.memmap(filename, dtype='uint8', mode='r', shape = imgShape)
        
        i = 0
        for planeFile in sorted(glob.glob("./SAR000001_100x_BF_z_4tiles_50steps_0.59um/Mosaic_stitched files/SAR000001_100x_BF_z_4tiles_50steps_0.59um_MosTIFFFulRes/*.tif")):
            imgPlane = tifffile.imread(planeFile)

            score = ssim(images[i], imgPlane)
            
            self.assertEqual(1, score)
            i +=1 

        self.assertEqual(imgShape, (51, 4040, 4040))

    def testImageSaving(self):

        saveImages(["./SAR000001_100x_BF_z_4tiles_50steps_0.59um/SAR000001_100x_BF_z_4tiles_50steps_0.59um"], "./Output", None, 0, 2, False, 256, 256)

        self.assertTrue(os.path.exists("./Output/SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff"))
        
        images = tifffile.imread("./Output/SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff")

        i = 0
        for planeFile in sorted(glob.glob("./SAR000001_100x_BF_z_4tiles_50steps_0.59um/Mosaic_stitched files/SAR000001_100x_BF_z_4tiles_50steps_0.59um_MosTIFFFulRes/*.tif")):
            imgPlane = tifffile.imread(planeFile)

            score = ssim(images[i], imgPlane)
            
            self.assertEqual(1, score)
            i +=1 
  

if __name__ == '__main__':
    unittest.main()