'''
Author: 
    Khang Duong

Last Updated: 
    1/21/2025

Description: 
    This script allows the user to import any missing images to Omero. Missing images are images that exist in the Imports folder but not in the Omero interface.
'''

#import modules
from omero.gateway import BlitzGateway
import os
import subprocess
import os
import argparse
import sys
import logging

parser = argparse.ArgumentParser(description = 'Reimport missing images to Omero')
parser.add_argument('-u', '--username', type=str, required=True, help='Omero username that is importing the images (Recommend using an importer account to import for other users)')
parser.add_argument('-w', '--password', type=str, required=True, help='Omero password for the user importing the images')
parser.add_argument('-ut', '--username-target', type=str, required=False, help='Omero username that is hosting the images on their page (could be the same as the importer). The images will be imported for this user and show up on their page. This flag is optional. If not set, then the username provided in the username flag will be used, meaning that the user is importing images to their own page.')
parser.add_argument('-p', '--project', type=str, required=False, help='Name of the Omero project that you want to import the images to (This is optional. However, if the project name is specified but the dataset name is not specified, then an error will occur. A project must have a dataset to store an image)' )
parser.add_argument('-i', '--images-path', type=str, required=True, help='Path of the directory where the stitched and converted OME-TIFF images will be stored for import to Omero. NOTE: This is the directory on the Omero server docker container')
parser.add_argument('-d', '--dataset', type=str, required=False, help='Name of the Omero dataset that you want to import the images to (This is optional. If the dataset name is not specified, then the image will be imported to the Orphaned Images folder)' )
parser.add_argument('-v','--verbose', action='store_true', required=False, help='Enable verbose mode (Prints out information as the script is running)')
args = parser.parse_args()


def import_image(image_path: str) -> None:
    '''
    Description:
        This function takes the image path in the Omero server Docker container (needed for in-place import) and imports that image to Omero.
    Input:
        image_path - a string with the path that corresponds to the path of the image that needs to be imported in the Omero server Docker container
    Output:
        NONE
    '''
        
    #image_path is the path of the image in the Omero Docker container

    logging.info(f"Importing the image to Omero from the Omero container: {image_path}")
   
    #starting generating the command for importing to Omero
    command = ['/opt/omero/server/venv3/bin/omero']

    #if the importer and the target user is not the same then add the command for the importer to have sudo permission to import images for another user
    if args.username != args.username_target:
        command.extend(['--sudo', args.username])

    #if the project is provided, then import the images to the project and dataset
    if args.project:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Project:name:{args.project}/Dataset:name:{args.dataset}', image_path])
    
    #if only dataset is provided, then import the images to the dataset
    elif args.dataset:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Dataset:name:{args.dataset}', image_path])
    
    #otherwise import the images as orphans
    else:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', image_path])

    #logging.info("The command used to import the image: " + " ".join(command))

    try:
        #run the command
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        output, debug = process.communicate()

        if (debug):
            debug = debug.decode().replace('\\r', '\r').replace('\\n', '\n').replace('\\t', '\t')
            logging.info("----------------DEBUG-----------------")
            logging.info(debug)
        
        if (output):
            output = output.decode().replace('\\r', '\r').replace('\\n', '\n').replace('\\t', '\t')
            logging.info("----------------OUTPUT-----------------")
            logging.info(output)
            
    
        logging.info(f"Successfully imported the image: {image_path}")

    except Exception as error:
        logging.error(f"Unable to import image: {error}")
    

def find_missing_images(images_path: str) -> None:
    '''
    Description:
        This function finds the image files that are missing a corresponding image in the Omero UI and imports those images to Omero
    Input:
        images_path - a string with the path that corresponds to the path with the images ready for import in the Omero server Docker container
    Output:
        NONE
    '''

    try:
        #connect to omero
        with BlitzGateway(args.username, args.password, host="localhost", port=4064, secure=True) as conn:
           
            #for each file in the images directory
            for file in os.listdir(images_path):
                if file.endswith(".ome.tiff"): #only the image file
                
                    #query the file name
                    query = f"from Image as img where img.name='{file}'"
                    matching_images = conn.getQueryService().findAllByQuery(query, None)

                    #check the images with the matching name
                    if len(matching_images) == 0:

                        #if there are is no matching image, then import the image
                        logging.info(f"The image file {file} doesn't have a corresponding image in the Omero UI.")
            
                        import_image(os.path.join(images_path, file))
                        
                
    except Exception as error:
        print(f"Error: Unable check for missing images. The following error occurred: {error}", file=sys.stderr)
        exit(1)

 
if __name__=='__main__':

    #create logger
    logger = logging.getLogger()
    
    #if verbose is set, allow more information to be logged
    if args.verbose:
        logger.setLevel(logging.INFO)
    else:
        #otherwise only display errors/warnings
        logger.setLevel(logging.WARNING)
    

    #create a stream handler and ensure that all messages are printed to stdout
    streamHandler = logging.StreamHandler()
    streamHandler.setLevel(logger.level)  

    #create a formatter and set the formatter for the handler
    formatter = logging.Formatter("%(asctime)s - %(levelname)-8s: %(message)s")
    streamHandler.setFormatter(formatter)
    
    #add the handler to the logger
    logger.addHandler(streamHandler)
  
    #if the target username is not provided, then the username of the user that is doing the importing is used, meaning that the user is importing the images to their own page
    if not args.username_target:
        args.username_target = args.username

    logging.info(f"Starting the import process. The user {args.username} is importing images to the page of user {args.username_target}")

    #if the project name is provided but not the dataset, then print error (a project must have a dataset)
    if args.project and not args.dataset:
        print("Error: A project must have a dataset. Please also provide the name of a dataset to import to.", file = sys.stderr)
        exit(1)

   
    logging.info(f"The images path in the container: {args.images_path}")

    #check if path is a valid path in the Omero server docker container
    if not os.path.isdir(args.images_path):
        print("Error: The images path provided is not a valid directory to watch for images in the Omero server docker container", file = sys.stderr)
        exit(1)

    #find the missing images and import them to Omero
    find_missing_images(args.images_path)