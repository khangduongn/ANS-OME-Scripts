'''
Author: 
    Khang Duong

Last Updated: 
    5/28/2024

Description: 
    This script allows the user to import images in a directory or a single image to Omero. It is recommended that the images being imported are in OME-TIFF format. However, you can use other file formats that are compatible with Omero.
    The script imports image(s) in-place from a mounted folder on the host server to the Omero server docker container. The project and dataset names can be provided to directly import images to specific folders in Omero.

Future Improvements:
    TODO: Low Priority: Add option for bulk-import (most likely not needed unless trying to automate large folders with converted images to specific projects/datasets for each image)
    TODO: Medium Priority: Add option for the user to provide the project or dataset id instead of just the name for importing images to a project/dataset.
    
    NOTE: This script must run using sudo in order for the docker commands to work.
    NOTE: This import script uses in place import to import images mounted from the host server to the Omero server ran on a docker container. 
    Therefore, at least one bind mount from the host machine to the Omero server docker container is required for the images to be in-place imported from the Omero server docker container.
    NOTE: If the project name is provided, then the dataset name must also be provided. If only the dataset name is provided, then that's fine. The images will be imported to the dataset in Omero.
    If no dataset is provided, then the images are imported to the "Orphaned Images" folder in Omero.
    NOTE: An importer user can be used when importing the images so that the importer does the job of importing (recommended by Omero) instead of the user where the images will be imported to. The user where the images will be imported to can also be the importer just as long as 
    the username and the username-target arguments are the same. Otherwise, the username and password arguments correspond to the importer user (the user doing the importing). For more help, read the argument descriptions on the help page.
'''

#import modules
import os
import argparse
import subprocess
import sys
import json
import logging
import time

#parse arguments
parser = argparse.ArgumentParser(description = 'Import images to Omero')
parser.add_argument('-u', '--username', type=str, metavar='', required=True, help='Omero username that is importing the images (Recommend using an importer account to import for other users)')
parser.add_argument('-w', '--password', type=str, metavar='', required=True, help='Omero password for the user importing the images')
parser.add_argument('-ut', '--username-target', type=str, metavar='', required=True, help='Omero username that is hosting the images on their page (could be the same as the importer). The images will be imported for this user and show up on their page')
parser.add_argument('-p', '--project', type=str, metavar='', required=False, help='Name of the Omero project that you want to import the images to' )
parser.add_argument('-c', '--container-name', type=str, metavar='',  default='docker-omero-omeroserver-1', required=False, help='The name of the docker container that is hosting the Omero server')
parser.add_argument('-i', '--image-path', type=str, metavar='', required=True, help='Path of a single OME-TIFF image or a directory of OME-TIFF images to import to Omero. The image(s) must be in a directory on the host machine that is mounted on the Omero server docker container')
parser.add_argument('-d', '--dataset', type=str, metavar='', required=False, help='Name of the Omero dataset that you want to import the images to' )
parser.add_argument('-v','--verbose', action='store_true', required=False, help='Enable verbose mode (Prints out information as the script is running)')
args = parser.parse_args()


def get_container_bind_mounts(container_name: str) -> list:
    '''
    Description:
        This function takes the name of the docker container that is hosting the Omero server instance and returns all bind mounts from the host machine to that docker container.
        This is used to replace the first part of the image path with the path that corresponds to the path in the Omero server docker container (needed for in-place import).
    Input:
        container_name - the name of the Docker container that is hosting the Omero server instance
    Output:
        bind_mounts - a list of dictionaries of the bind mounts from the host machine to the Omero server docker container 
            For example (not real directories just for demonstration):
            bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/XLINE3W', 'Destination': '/mnt/images2/'}]
    '''

    #the command to check all bind mounts for the docker container
    cmd = ['docker', 'inspect', '-f', '{{ json .Mounts }}', container_name]

    #grab the result from the command and convert it to json for easy processing
    result = subprocess.run(cmd, capture_output=True, text=True)
    mounts_data = json.loads(result.stdout)

    #list to store the dictionaries of the bind mounts
    bind_mounts = []

    #for each mount in the docker container
    for mount in mounts_data:

        #if the mount type is a bind mound
        if mount["Type"] == "bind":

            #then append the dictionary with the source and destination information for the mount
            bind_mounts.append({
                "Source": mount["Source"],
                "Destination": mount["Destination"]
            })

    return bind_mounts


def apply_mount(bind_mounts: list, path: str) -> (str | None):
    '''
    Description:
        This function takes the list of bind mounts and the path of the image(s) on the host server and converts the path to the appropriate path in the Omero server docker container.
        This function basically replaces first part of the image path (which points to the directory or image in the host server) with the path that corresponds to the path in the Omero server docker container (needed for in-place import).
    Input:
        bind_mounts - a list of dictionaries of the bind mounts from the host machine to the Omero server docker container 
            For example (not real directories just for demonstration):
            bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/XLINE3W', 'Destination': '/mnt/images2/'}]
    Output:
        new_path - a string with the new path that corresponds to the path in the Omero server docker container
            Returns None if new path cannot be generated
    '''

    #for each bind mount
    for mount in bind_mounts:

        #if the original path in the host machine matches the source path in the bind mount
        if path.startswith(mount['Source']):

            #then, replace the start of the path with the destination path (corresponds to the path in the Omero server docker container)
            new_path = os.path.join(mount['Destination'], os.path.relpath(path, mount['Source']))

            return new_path
            

def is_valid_path_in_container(container_name: str, path: str) -> bool:
    '''
    Description:
        This function takes the container name of the docker container hosting the Omero server and the path of the image or directory of images in this container and checks to ensure that this path exists in the docker conatainer.
    Input:
        container_name - the name of the Docker container that is hosting the Omero server instance
        path - the path of the image or directory of images in the Omero server docker container
    Output:
        isValid - a boolean representing whether the path provided is a valid path in the Omero server docker container (true for valid and false for invalid)
    '''

    try:
        
        #run command to check if path exists in docker container environment
        result = subprocess.run(["docker", "exec", container_name, "test", "-e", path], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        #0 means success (is valid path)
        return result.returncode == 0
        
    except Exception:
        print(f"Error: Unable to determine if the provided path exists in the Omero server docker container. Please try again.", file=sys.stderr)
        exit(1)


if __name__=='__main__':

    # create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # add a file handler and ensure that all error messages are logged to file
    fileHandler = logging.FileHandler(os.path.join(args.output_dir, 'flagged_images.csv'))
    fileHandler.setLevel(logging.ERROR) 

    # create a formatter and set the formatter for the handler
    formatting = logging.Formatter('%(message)s')
    fileHandler.setFormatter(formatting)

    # add the handler to the logger
    logger.addHandler(fileHandler)

    #if verbose is set, then output debug information and error messages to stdout
    if args.verbose:

        #create a stream handler and ensure that all messages are printed to stdout
        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(logging.DEBUG)

        # create a formatter and set the formatter for the handler
        formatter = logging.Formatter("%(levelname)-8s: %(message)s")
        streamHandler.setFormatter(formatter)

        # add the handler to the logger
        logger.addHandler(streamHandler)

    
    startTimeScript = time.time()

    #if the project name is provided but not the dataset, then print error (a project must have a dataset)
    if args.project and not args.dataset:
        print("Error: A project must have a dataset. Please also provide the name of a dataset to import to.", file = sys.stderr)
        exit(1)

    #get the list of bind mounts using the name of the docker container that is hosting the Omero server
    bind_mounts = get_container_bind_mounts(args.container_name)

    #no bind mounts found (bind mounts are needed for in-place import to Omero)
    if len(bind_mounts) == 0:
        print("Error: No bind mounts found between the host server and the Omero server docker container.", file = sys.stderr)
        exit(1)

    #apply the mount to the path so that it is a valid path in the Omero server docker container
    image_path = apply_mount(bind_mounts, args.image_path)
    
    if image_path == None:
        print("Error: The provided image path cannot be applied to any bind mounts on the Omero server docker container.", file = sys.stderr)
        exit(1)

    #check if path is a valid path in the Omero server docker container
    if not is_valid_path_in_container(args.container_name, image_path):
        print("Error: The image path provided is not a file or a directory of images in the Omero server docker container", file = sys.stderr)
        exit(1)

    #starting generating the command for importing to Omero
    command = ['docker', 'exec', '-it', args.container_name, '/opt/omero/server/venv3/bin/omero']

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

    #run the command
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, error = process.communicate()

    print("----------------ERROR-----------------")
    print(error)
    print("----------------OUTPUT-----------------")
    print(output)

    
    logging.info("This script took --- %s seconds ---\n\n\n" % (time.time() - startTimeScript))
