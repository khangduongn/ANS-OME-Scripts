'''
Author: 
    Khang Duong

Last Updated: 
    11/26/2024

Description: 
    This Omero script allows the user to compare the list of images in the Omero UI with the list of image files in the server's Imports folder to ensure that they align.
    After running this script, a message should pop up indicating whether the images and the files align.

    NOTE: This script can only be ran in the Omero Script UI under the custom_scripts tab

    INSTRUCTIONS ON HOW TO DEPLOY THIS SCRIPT:
        1. Make sure that the script is mounted to the Omero server scripts directory in the Docker container
            Add this bind mount to the volumes section in the docker compose file that is creating the Omero server Docker container
            "<path-to-directory-with-script-in-host-server>:/opt/omero/server/OMERO.server/lib/scripts/omero/custom_scripts:ro"
        2. Restart the Docker containers
        3. When you are logged in to the Omero website, you should see the gears icon on the top right corner of the interface (close to the search bar). Click on the icon and you should see a "custom_scripts" tab if done correctly
    INSTRUCTIONS ON HOW TO RUN THIS SCRIPT:
        1. When you are logged in to the website, you should see the gears icon on the top right corner of the interface (close to the search bar). Click on the icon.
        2. Select "custom_scripts"
        3. Select "Validate Image List". The interface for the script should appear.
        5. Click "Run Script"
        6. After the script finishes running, you should see a message displaying the result.
'''

#import modules
from omero.gateway import BlitzGateway
from omero.rtypes import rstring
import omero.scripts as scripts
import os


def run_script():

    #Omero client
    client = scripts.client(
        'Validate Image List',
        "This script compares the list of images in the Omero UI with the list of image files in the server's Imports folder to ensure that they align.",
        scripts.String(
            "Imports_Path", optional=False, grouping="1",
            description="Path of the directory with the image files that were imported",
            default="/mnt/images/Imports"),
        authors=["Khang Duong"],
        institutions=["Drexel ANS"],
    )

    try:
       
        #wrap client to use the Blitz Gateway
        conn = BlitzGateway(client_obj=client)
        print("Connection Established")

        #get the path of the Imports folder from the client
        imports_path = client.getInput("Imports_Path", unwrap=True)
        
        #if the path doesn't exist in the server, then display error and exit
        if not os.path.isdir(imports_path):
            client.setOutput("Message", rstring("The path of the directory with the imported image files does not exist."))
            raise Exception("The path of the directory with the imported image files does not exist.")

        missing_images = [] #store the files that don't have a corresponding image in the UI
        duplicate_images = [] #store the files that have duplicate images in the UI
        img_count = 0 #count the number of images in the UI
        file_count = 0 #count the number of files in the server

        #for each file
        for file in os.listdir(imports_path):
            if file.endswith(".ome.tiff"): #only the image file
            
                #query the file name
                query = f"from Image as img where img.name='{file}'"
                matching_images = conn.getQueryService().findAllByQuery(query, None)

                #check the images with the matching name
                #if there are more than 1
                if len(matching_images) > 1:  

                    print(f"The image file {file} has more than one corresponding image in the Omero UI.")
                    duplicate_images.append(file)
                    img_count += len(matching_images)
                elif len(matching_images) == 0:

                    #if there are is no matching image
                    print(f"The image file {file} doesn't have a corresponding image in the Omero UI.")
                    missing_images.append(file)
                else: 
                    #if there is exactly one matching image
                    img_count += 1
                    
                file_count += 1

        #print the missing image names if there are any
        if len(missing_images) == 0:
            missing_images_msg = 'No missing images found.'
        else:
            missing_images_text_list = ', '.join(missing_images)
            missing_images_msg = f"The following image files don't have a corresponding image in the Omero UI: {missing_images_text_list}"
        
        #print the duplicate image names if there are any
        if len(duplicate_images) == 0:
            duplicate_images_msg = 'No duplicate images found.'
        else:
            duplicate_images_text_list = ', '.join(duplicate_images)
            duplicate_images_msg = f"The following image files have duplicate images with the same name in the Omero UI: {duplicate_images_text_list}"
            
        #message to display after the script is done
        message = f''' 
        The script has finished. There are {img_count} images in Omero and {file_count} image files in the server.
        {missing_images_msg}
        {duplicate_images_msg}
        '''
        client.setOutput("Message", rstring(message))

    finally:
        client.closeSession()


if __name__ == "__main__":
    run_script()