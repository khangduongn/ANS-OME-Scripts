# ANS OME Scripts

This repository contains scripts used in the conversion to Omero pipeline. The `conversion.py` script is a Python script used to stitch .tif tile images into full stitched .ome.tiff images that are compatible with the Omero image viewer web application.

## Image Stitching and Conversion

The `conversion.py` script was developed in Python 3.9.18

### Installation

Install [Python](https://www.python.org/downloads/) (make sure the version is compatible with the script)

You can create a virtual environment or use the default environment in Python to install the dependencies needed to run the script. I recommend using a virtual environment to keep all of the dependencies and scripts in the same, contained environment for the project.

You can install all of the dependencies (modules) required to run the script into your Python environment using the following command (the `requirements.txt` file is provided in this repository):

`pip3 install -r requirements.txt`

Navigate into the directory with the script and ensure that the current Python environment you are in has the necessary dependencies to run the script. Run the script using the following command:

`python3 conversion.py -h`

The help flag `-h` will provide you with more information on how to run the script with the required and optional arguments depending on your conversion needs.
