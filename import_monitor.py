'''
Author: 
    Khang Duong

Last Updated: 
    9/5/2024

Description: 
    This script allows the user to import images in a directory or a single image to Omero. It is recommended that the images being imported are in OME-TIFF format. However, you can use other file formats that are compatible with Omero.
    The script imports image(s) in-place from a mounted folder on the host server to the Omero server docker container. The project and dataset names can be provided to directly import images to specific folders in Omero.

Future Improvements:
    TODO: Low Priority: Add option for bulk-import (most likely not needed unless trying to automate large folders with converted images to specific projects/datasets for each image)
    TODO: Low Priority: Add a better way to display or save the output/error generated from the import (maybe saving to log file?)
    
    TODO: Medium Priority: Add option for the user to provide the project or dataset id instead of just the name for importing images to a project/dataset.
    TODO: Medium Priority: Test some error handling
    
   
    NOTE: This script must run using sudo in order for the docker commands to work.
    NOTE: This import script uses in place import to import images mounted from the host server to the Omero server ran on a docker container. 
    Therefore, at least one bind mount from the host machine to the Omero server docker container is required for the images to be in-place imported from the Omero server docker container.
    NOTE: After an image has been imported via in-place import, it cannot be moved in the host server otherwise Omero might still try to reference it causing weird behaviors that will require you to restart Docker.
    NOTE: If the project name is provided, then the dataset name must also be provided. If only the dataset name is provided, then that's fine. The images will be imported to the dataset in Omero.
    If no dataset is provided, then the images are imported to the "Orphaned Images" folder in Omero.
    NOTE: An importer user can be used when importing the images so that the importer does the job of importing (recommended by Omero) instead of the user where the images will be imported to. The user where the images will be imported to can also be the importer just as long as 
    the username and the username-target arguments are the same. Otherwise, the username and password arguments correspond to the importer user (the user doing the importing). For more help, read the argument descriptions on the help page.
    NOTE: The Omero folder structure goes from Project -> Dataset -> Image. A project can only contain datasets and cannot contain images unless the images are stored in a dataset within a project. Datasets can exist outside of projects. Images cannot exist outside of datasets
'''

#import modules
import os
import argparse
import sys
import logging
import time
import docker
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

#parse arguments
parser = argparse.ArgumentParser(description = 'Import images to Omero automated by watching a directory for new images')
parser.add_argument('-u', '--username', type=str, metavar='', required=True, help='Omero username that is importing the images (Recommend using an importer account to import for other users)')
parser.add_argument('-w', '--password', type=str, metavar='', required=True, help='Omero password for the user importing the images')
parser.add_argument('-ut', '--username-target', type=str, metavar='', required=True, help='Omero username that is hosting the images on their page (could be the same as the importer). The images will be imported for this user and show up on their page')
parser.add_argument('-p', '--project', type=str, metavar='', required=False, help='Name of the Omero project that you want to import the images to (This is optional. However, if the project name is specified but the dataset name is not specified, then an error will occur. A project must have a dataset to store an image)' )
parser.add_argument('-c', '--container-name', type=str, metavar='',  default='docker-omero-omeroserver-1', required=False, help='The name of the docker container that is hosting the Omero server')
parser.add_argument('-i', '--images-path', type=str, metavar='', required=True, help='Path of a directory where the stitched and converted OME-TIFF images will be stored for import to Omero. The directory on the host machine must be mounted on the Omero server docker container')
parser.add_argument('-d', '--dataset', type=str, metavar='', required=False, help='Name of the Omero dataset that you want to import the images to (This is optional. If the dataset name is not specified, then the image will be imported to the Orphaned Images folder)' )
parser.add_argument('-v','--verbose', action='store_true', required=False, help='Enable verbose mode (Prints out information as the script is running)')
args = parser.parse_args()


def get_container_bind_mounts(client, container_name: str) -> list:
    '''
    Description:
        This function takes the name of the docker container that is hosting the Omero server instance and returns all bind mounts from the host machine to that docker container.
        This is used to replace the first part of the images path with the path that corresponds to the path in the Omero server docker container (needed for in-place import).
    Input:
        client - the Docker client instance
        container_name - the name of the Docker container that is hosting the Omero server instance
    Output:
        bind_mounts - a list of dictionaries of the bind mounts from the host machine to the Omero server docker container 
            For example (not real directories just for demonstration):
            bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/XLINE3W', 'Destination': '/mnt/images2/'}]
    '''

    try:
        #get the Docker container and retrieve all mounts in this container
        container = client.containers.get(container_name)
        mounts = container.attrs['Mounts']
        
        #list to store all bind mounts for the Docker container
        bind_mounts = [{"Source": mount['Source'], "Destination": mount['Destination']} for mount in mounts if mount["Type"] == "bind"]

    except docker.errors.NotFound:
        print(f"Error: The Docker container {container_name} was not found.", file=sys.stderr)
        exit(1)
    except Exception as error:
        print(f"Error: Unable to retrieve bind mounts: {error}", file=sys.stderr)
        exit(1)
    
    return bind_mounts


def apply_mount(bind_mounts: list, path: str):
    '''
    Description:
        This function takes the list of bind mounts and the path of the directory to watch for new images on the host server and converts the path to the appropriate path in the Omero server Docker container.
        This function basically replaces first part of the images path (which points to the directory in the host server) with the path that corresponds to the path in the Omero server Docker container (needed for in-place import).
    Input:
        bind_mounts - a list of dictionaries of the bind mounts from the host machine to the Omero server docker container 
            For example (not real directories just for demonstration):
            bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/XLINE3W', 'Destination': '/mnt/images2/'}]
        path - a string with the path that corresponds to the path to watch for new images in the host server running the Omero Docker containers
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
            

def is_valid_path_in_container(client, container_name: str, path: str) -> bool:
    '''
    Description:
        This function takes the container name of the docker container hosting the Omero server and the path of the image or directory of images in this container and checks to ensure that this path exists in the docker conatainer.
    Input:
        client - the Docker client instance
        container_name - the name of the Docker container that is hosting the Omero server instance
        path - the path of the directory of images to watch for in the Omero server docker container
    Output:
        isValid - a boolean representing whether the path provided is a valid path in the Omero server docker container (true for valid and false for invalid)
    '''

    try:
        container = client.containers.get(container_name)
        result = container.exec_run(f"test -e {path}", demux=True)

        return result.exit_code == 0
    
    except Exception as error:
        print(f"Error: Unable to check the path {path} existence in the container: {error}", file=sys.stderr)
        exit(1)



#class for monitoring when there are new images in the image directory
class NewImagesHandler(FileSystemEventHandler):

    def __init__(self, client):
        self.dockerClient = client

    def on_created(self, event):
        #check that the new entry in the directory is not a directory and that it ends with .ome.tiff (to ensure that it is an image)
        if not event.is_directory and event.src_path.endswith('.ome.tiff'):
            logging.info(f"New image detected in the folder: {event.src_path}. Importing the image to Omero.")
            
            #wait until the image finishes converting first before importing
            self.wait_for_completion(event.src_path)

            #import the image
            self.import_image(event.src_path)

    def wait_for_completion(self, image_path):
        #image_path is the path of the image in the host server

        logging.info(f"Waiting for the image to be completely saved and converted: {image_path}")

        #keep iterating until the size of the file does not change 
        while True:
            initial_size = os.path.getsize(image_path)
            time.sleep(10)
            current_size = os.path.getsize(image_path)
            if initial_size == current_size:
                break

    def import_image(self, image_path):
        #image_path is the path of the image in the host server

        #apply the mount to the path so that it is a valid path in the Omero server docker container
        image_path = apply_mount(bind_mounts, image_path)
        
        if image_path == None:
            logging.error("Error: The provided images path cannot be applied to any bind mounts on the Omero server docker container.")
            return

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

        logging.info("The command used to import the image: " + " ".join(command))

        try:

            #run the command
            result = self.dockerClient.containers.get(args.container_name).exec_run(command, demux=True)
            
            print("OUTPUT")
            print(str(result[0]))

            print("ERROR")
            print(str(result[1]))
            #if the exit code of the command is not 0, then raise an error
            if result.exit_code != 0:
                logging.error(f"Image import failed with exit code {result.exit_code}.")
            else:
                logging.info("Image import completed successfully.")
        
        except Exception as error:
            logging.error(f"Error: Unable to import image: {error}")




if __name__=='__main__':

    #initialize Docker client
    dockerClient = docker.from_env()

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
    formatter = logging.Formatter("%(levelname)-8s: %(message)s")
    streamHandler.setFormatter(formatter)
    
    #add the handler to the logger
    logger.addHandler(streamHandler)
    

    #if the project name is provided but not the dataset, then print error (a project must have a dataset)
    if args.project and not args.dataset:
        print("Error: A project must have a dataset. Please also provide the name of a dataset to import to.", file = sys.stderr)
        exit(1)

    #check if path of the directory to watch for new images is a valid directory path 
    if not os.path.isdir(args.images_path):
        print("Error: The path provided is not a valid directory path to watch for images. Check to see if the directory exists.", file = sys.stderr)
        exit(1)

    logging.info(f"Getting the list of bind mounts for the Docker container: {args.container_name}")

    #get the list of bind mounts using the name of the docker container that is hosting the Omero server
    bind_mounts = get_container_bind_mounts(dockerClient, args.container_name)

    #no bind mounts found (bind mounts are needed for in-place import to Omero)
    if len(bind_mounts) == 0:
        print("Error: No bind mounts found between the host server and the Omero server docker container. Check the container name to ensure that it is the correct name for the docker container is running the Omero server instance. Check that there are bind mounts by looking in the docker compose file.", file = sys.stderr)
        exit(1)

    logging.info(f"Applying the bind mount to the images path: {args.images_path}")

    #apply the mount to the path so that it is a valid path in the Omero server docker container
    images_path = apply_mount(bind_mounts, args.images_path)
    
    if images_path == None:
        print("Error: The provided images path cannot be applied to any bind mounts on the Omero server docker container.", file = sys.stderr)
        exit(1)

    logging.info(f"The new images path on the Omero server docker container: {images_path}")

    #check if path is a valid path in the Omero server docker container
    if not is_valid_path_in_container(dockerClient, args.container_name, images_path):
        print("Error: The images path provided is not a valid directory to watch for images in the Omero server docker container", file = sys.stderr)
        exit(1)


    new_images_handler = NewImagesHandler(dockerClient)

    #observer to watch for new images in the provided directory 
    #It is not recursive meaning it only checks for new images in the parent directory and not any sub/child directories)
    observer = Observer()
    observer.schedule(new_images_handler, path=args.images_path, recursive=False)

    #start the observer
    observer.start()
    logging.info(f"Monitoring the directory {args.images_path} for new images")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


    
    
