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
parser.add_argument('-w', '--password', type=str, metavar='', required=True, help='Omero password for the importer user')
parser.add_argument('-ut', '--username_target', type=str, metavar='', required=True, help='Omero username that is hosting the images on their page (not the importer). The images will be imported for this user.')
parser.add_argument('-od', '--output-dir', type=str, metavar='', required=True, help='Path of the temp output files')
parser.add_argument('-p', '--project', type=str, metavar='', required=False, help='Name of the Omero project that you want to import to' )
parser.add_argument('-c', '--container-name', type=str, metavar='',  default='docker-omero-omeroserver-1', required=False, help='Path of the Docker compose file used to start the Omero containers')
parser.add_argument('-ud', '--upload-dir', type=str, metavar='', required=True, help='Path of the directory containing the upload.txt files for uploading the images')
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

    return bind_mounts

def apply_mount(bind_mounts, path):
    for mount in bind_mounts:
        if path.startswith(mount['Source']):
            new_path = os.path.join(mount['Destination'], os.path.relpath(path, mount['Source']))
            return new_path
            


# def get_container_filepath(omeserver_volumes, file_path):
#     '''
#     This function takes in a list of bind mounts and the path of a file on the Docker host in order 
#     to get the path of the file on the Docker container filesystem.
#     '''

#     for volume in omeserver_volumes:
     

#         if volume.split(':')[0] != 'omero':
            
#             rel = os.path.relpath(file_path, volume.split(':')[0])
#             new_file_path = os.path.join(volume.split(':')[1], rel)

#             # print(rel)
#             # print(new_file_path)
#             if not ('..' in new_file_path):
  
#                 return new_file_path

    # raise Exception("Unable to get the file path")



if __name__=='__main__':

    #if the project name is provided but not the dataset, then print error (a project must have a dataset)
    if args.project and not args.dataset:
        print("Error: A project must have a dataset. Please also provide the name of a dataset to import to.", file = sys.stderr)
        exit(1)

    bind_mounts = get_container_bind_mounts(args.container_name)

    #no bind mounts found (bind mounts are needed for in-place import to Omero)
    if len(bind_mounts) == 0:
        print("Error: No bind mounts found between the host server and the omero server docker container", file = sys.stderr)
        exit(1)

    #bind_mounts = [{'Source': '/mnt/XLIN/', 'Destination': '/mnt/images/'}, {'Source': '/mnt/bye', 'Destination': '/mnt/images/'}]
    
    

    if not (os.path.isfile(args.image_path) or os.path.isdir(args.image_path)) :
        print("Error: The image path provided is not a file or a directory of images", file = sys.stderr)
        exit(1)

    image_path = apply_mount(bind_mounts, args.image_path)
    
    if args.project:
        command = ['docker', 'exec', '-it', args.container_name, '/opt/omero/server/venv3/bin/omero', '--sudo', args.username, '-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Project:name:{args.project}/Dataset:name:{args.dataset}', image_path]
    elif args.dataset:
        command = ['docker', 'exec', '-it', args.container_name, '/opt/omero/server/venv3/bin/omero', '--sudo', args.username, '-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', '-T', f'Dataset:name:{args.dataset}', image_path]
    else:
        command = ['docker', 'exec', '-it', args.container_name, '/opt/omero/server/venv3/bin/omero', '--sudo', args.username, '-u', args.username_target, '-s', 'localhost', '-w', args.password, 'import', '--transfer=ln_s', image_path]

    #run the command
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, error = process.communicate()

    print("----------------ERROR-----------------")
    print(error)
    print("----------------OUTPUT-----------------")
    print(output)

    #ex: /mnt/XLINUXDIATOMS
    exit()
    uploadTxtPaths = [os.path.join(args.upload_dir, file) for file in os.listdir(args.upload_dir) if os.path.isfile(os.path.join(args.upload_dir, file))]

    #imgs = [f for f in glob.glob(os.path.join(args.img_dir, '**/*.ome.tiff'), recursive=True)]
    
    imgPaths = []

    for uploadTxtPath in uploadTxtPaths:

        with open(uploadTxtPath) as f:

            for line in f.readlines():
                imgPaths.append(line.rstrip())
	
   
    
   
    #for each image path 
    for img in imgPaths:

        #print(img)
        if not os.path.exists(img):
            continue

        #use the new image path to get the path of the image on the Docker container filesystem
        img_path = get_container_filepath(omeserver_volumes, img)

        #get the path of the csv file used to bulk import the images
        notImportedCsvPathHost = os.path.join(args.output_dir, 'not_imported_images.csv')


        importedImagesCsv = os.path.join(args.output_dir, 'imported_images.csv')

        # open the file in append mode
        with open(notImportedCsvPathHost, 'a') as f:

            # create the csv writer
            writer = csv.writer(f)

            # write a row to the csv file
            #first column is the image path in the Docker container filesystem
            #second column is the Project and Dataset names that the image will reside
            writer.writerow([img_path, f'Project:name:{args.project}/Dataset:name:{os.path.splitext(os.path.basename(img_path))[0]}'])

        
    print(notImportedCsvPathHost)
    #get the path of the csv file in the Docker container filesystem
    notImportedCsvPathContainer = get_container_filepath(omeserver_volumes, notImportedCsvPathHost)

    
    print(notImportedCsvPathContainer)
    #generate dictionary used to write the bulk.yml file
    data = dict(
        transfer = 'ln_s',
        path = f"{notImportedCsvPathContainer}",
        columns = ['path', 'target']
            
    )

    #create a path for the bulk.yml file on the Docker host
    bulkYmlPathHost = os.path.join(args.output_dir, 'bulk.yml')

    #create the bulk.yml file
    with open(bulkYmlPathHost, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    
    #get the path of the bulk.yml file on the Docker container filesystem
    bulkYmlPathContainer = get_container_filepath(omeserver_volumes, bulkYmlPathHost)

    #with open(importedImagesCsv, 'r') as f1, open(notImportedCsvPathHost, 'r') as f2:
    #    importedImages = f1.readlines()
    #    newImages = f2.readlines()

    #with open(notImportedCsvPathHost, 'w') as outFile:
    #    for image_detail in newImages:
    #        if image_detail not in importedImages:
    #            outFile.write(image_detail)



    #get the docker container name used for importing 
    dockerContainerName = os.path.dirname(args.docker_compose).split('/')[-1] + '-omeroserver-1'

    #generate the command used for importing the images to Omero
    #NOTE: You may need to run this python file as sudo in order to run this command or else you may get an error
    command = f'docker exec -it {dockerContainerName} /opt/omero/server/venv3/bin/omero --sudo {args.username} -u {args.username_target} -s localhost -w {args.password} import --bulk {bulkYmlPathContainer}'
    
    #run the command
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    print("----------------ERROR-----------------")
    print(error)
    print("----------------OUTPUT-----------------")
    print(output)
 
    #remove the bulk import files
    os.remove(bulkYmlPathHost)
    os.remove(notImportedCsvPathHost)