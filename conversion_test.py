
from conversion import stitch_tiles, saveImages
from skimage.metrics import structural_similarity as ssim
import numpy as np
import glob
import tifffile
import os
import argparse



def parseArguments():
    parser = argparse.ArgumentParser(description = 'Testing Conversion Features')

    parser.add_argument('-td', '--tiles-dir', type=str, metavar='', required=True, help='Path of the directory containing the tiles that need to be stitched (directory must also contain XYZPositions.txt file)')
    parser.add_argument('-pd', '--planes-dir', type=str, metavar='', required=True, help='Path of the directory containing mosaic full resolution stitched planes of the same image as the tiles (these stitched planes are used for validation to ensure the stitching was done correctly)')
    parser.add_argument('-od', '--output-dir', type=str, metavar='', required=True, help='Path of the directory where the full stitched converted images will be')
    
    args = parser.parse_args()

    return args

def test_stitching(tilesPath, planesPath, outputPath):
    filename, imgShape, _, _ = stitch_tiles(tilesPath, outputPath)
    
    images = np.memmap(filename, dtype='uint8', mode='r', shape = imgShape)
    
    i = 0
    for planeFile in sorted(glob.glob(os.path.join(planesPath, '*.tif'))):
        imgPlane = tifffile.imread(planeFile)

        score = ssim(images[i], imgPlane)
        
        
        assert 1 == score, f'The SSIM score should be 1, instead it is {score}'
        i +=1 

    xShape = images[i - 1].shape[0]
    yShape = images[i - 1].shape[1]
    
    assert imgShape == (i, xShape, yShape), f'The final image shape should be ({i}, {xShape}, {yShape}), instead it is {imgShape}'

def testImageSaving(tilesPath, planesPath, outputPath):

    saveImages([tilesPath.rstrip('/')], outputPath, None, 0, 2, False, 256, 256)

    assert(os.path.exists(os.path.join(outputPath, "SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff")))
    
    images = tifffile.imread(os.path.join(outputPath, "SAR000001_100x_BF_z_4tiles_50steps_0.59um.ome.tiff"))

    i = 0
    for planeFile in sorted(glob.glob(os.path.join(planesPath, '*.tif'))):
        imgPlane = tifffile.imread(planeFile)

        score = ssim(images[i], imgPlane)
        
        assert 1 == score, f'The SSIM score should be 1, instead it is {score}'
        i +=1 


if __name__ == '__main__':

    args = parseArguments()
    tilesPath = args.tiles_dir
    planesPath = args.planes_dir
    outputPath = args.output_dir

    test_stitching(tilesPath, planesPath, outputPath)
    testImageSaving(tilesPath, planesPath, outputPath)

    for tempFile in glob.glob(os.path.join(outputPath, '*.dat')):
        os.remove(tempFile)