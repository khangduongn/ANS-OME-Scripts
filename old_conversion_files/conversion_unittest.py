
from conversion import stitch_tiles, saveImages
from skimage.metrics import structural_similarity as ssim
import numpy as np
import glob
import tifffile
import os
import argparse
import unittest


def parseArguments():
    parser = argparse.ArgumentParser(description = 'Testing Conversion Features')

    parser.add_argument('-td', '--tiles-dir', type=str, metavar='', required=True, help='Path of the directory containing the tiles that need to be stitched (directory must also contain XYZPositions.txt file)')
    parser.add_argument('-pd', '--planes-dir', type=str, metavar='', required=True, help='Path of the directory containing mosaic full resolution stitched planes of the same image as the tiles (these stitched planes are used for validation to ensure the stitching was done correctly)')
    parser.add_argument('-od', '--output-dir', type=str, metavar='', required=True, help='Path of the directory where the full stitched converted images will be')
    
    args = parser.parse_args()

    return args


   


class TestConversionMethods(unittest.TestCase):

    tilesPath = ''
    mosaicStitchedPlanesPath = ''
    stitchedFilePath = ''

    def testStitching(self):
        filename, imgShape, _, _ = stitch_tiles(self.tilesPath, self.stitchedFilePath)
        
        images = np.memmap(filename, dtype='uint8', mode='r', shape = imgShape)
        
        i = 0
        for planeFile in sorted(glob.glob(self.mosaicStitchedPlanesPath)):
            imgPlane = tifffile.imread(planeFile)

            score = ssim(images[i], imgPlane)
            
            xShape = images[i].shape()[1]
            yShape = images[i].shape()[2]
            self.assertEqual(1, score)
            i +=1 

        self.assertEqual(imgShape, (i + 1, xShape, yShape))

    def testImageSaving(self):

        saveImages([self.tilesPath], self.stitchedFilePath, None, 0, 2, False, 256, 256)

        self.assertTrue(os.path.exists(os.path.join(self.stitchedFilePath, "SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff")))
        
        images = tifffile.imread(os.path.join(self.stitchedFilePath, "SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff"))

        i = 0
        for planeFile in sorted(glob.glob(self.mosaicStitchedPlanesPath)):
            imgPlane = tifffile.imread(planeFile)

            score = ssim(images[i], imgPlane)
            
            self.assertEqual(1, score)
            i +=1 
  



if __name__ == '__main__':
    
    args = parseArguments()
    TestConversionMethods.tilesPath = args.tiles_dir
    TestConversionMethods.mosaicStitchedPlanesPath = args.planes_dir
    TestConversionMethods.stitchedFilePath = args.output_dir
    unittest.main()
   