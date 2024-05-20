#import modules
import os
import argparse
# import yaml
import csv
import subprocess
import sys
import json

#parse arguments
parser = argparse.ArgumentParser(description = 'Import images to Omero')
parser.add_argument('-u', '--username', type=str, metavar='', required=True, help='Omero username that is importing the images (Recommend using an importer account to import for other users')
parser.add_argument('-w', '--password', type=str, metavar='', required=True, help='Omero password for the user importing the images')
parser.add_argument('-ut', '--username-target', type=str, metavar='', required=True, help='Omero username that is hosting the images on their page (could be the same as the importer). The images will be imported for this user and show up on their page.')
parser.add_argument('-p', '--project', type=str, metavar='', required=False, help='Name of the Omero project that you want to import to' )
parser.add_argument('-c', '--container-name', type=str, metavar='',  default='docker-omero-omeroserver-1', required=False, help='Path of the Docker compose file used to start the Omero containers')
parser.add_argument('-i', '--image-path', type=str, metavar='', required=True, help='Path of a single OME-TIFF image or a directory of OME-TIFF images to import to Omero')
parser.add_argument('-d', '--dataset', type=str, metavar='', required=False, help='Name of the Omero dataset that you want to import to' )
args = parser.parse_args()

#NOTE: This import script uses in place import to import images mounted from the host server to the Omero server. Therefore, at least one bind mount from the host machine to the Omero server docker container is required.
#must provide dataset if project is provided
#if only dataset is provided then thats fine
#if no dataset is provided then import to orphan 


def get_container_bind_mounts(container_name):
    cmd = ['docker', 'inspect', '-f', '{{ json .Mounts }}', container_name]
    result = subprocess.run(cmd, capture_output=True, text=True)
    mounts_json = result.stdout
    mounts_data = json.loads(mounts_json)

    bind_mounts = []
    for mount in mounts_data:
        if mount["Type"] == "bind":
            bind_mounts.append({
                "Source": mount["Source"],
                "Destination": mount["Destination"]
            })

    
    #Example of a bind_mounts
    #bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/bye', 'Destination': '/mnt/images2/'}]
    return bind_mounts

def apply_mount(bind_mounts, path):
    for mount in bind_mounts:
        if path.startswith(mount['Source']):
            new_path = os.path.join(mount['Destination'], os.path.relpath(path, mount['Source']))
            return new_path
            

def is_valid_path_in_container(container_name, path):

    try:
        
        #run command to check if path exists in docker container environment
        result = subprocess.run(["docker", "exec", container_name, "test", "-e", path], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return result.returncode == 0
        
    except Exception:
        print(f"Error: Unable to determine if the provided path exists in the Omero server docker container. Please try again.", file=sys.stderr)
        exit(1)


if __name__=='__main__':

    #if the project name is provided but not the dataset, then print error (a project must have a dataset)
    if args.project and not args.dataset:
        print("Error: A project must have a dataset. Please also provide the name of a dataset to import to.", file = sys.stderr)
        exit(1)

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


    command = ['docker', 'exec', '-it', args.container_name, '/opt/omero/server/venv3/bin/omero']

    #if the importer and the target user is not the same then add the command for the importer to have sudo permission to import images for another user
    if args.username != args.username_target:
        command.extend(['--sudo', args.username])

    if args.project:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Project:name:{args.project}/Dataset:name:{args.dataset}', image_path])
    elif args.dataset:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Dataset:name:{args.dataset}', image_path])
    else:
        command.extend(['-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', image_path])

    #run the command
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, error = process.communicate()

    print("----------------ERROR-----------------")
    print(error)
    print("----------------OUTPUT-----------------")
    print(output)
