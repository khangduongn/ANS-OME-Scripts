'''
Author: 
    Khang Duong

Last Updated: 
    11/25/2024

Description: 
    This script allows the user to import metadata for images in Omero. It is recommended that the image 

    NOTE: Run this script within the Omero Docker container server to utilize the omero module and the file system within the container. Must have this script and the metadata file mounted to the container
    e.g.
        sudo docker exec -i <container-name> /opt/omero/server/venv3/bin/python3 /<path-to-script-in-container>/import_metadata.py -u <username> -w <password> -m <path-to-metadata-file-in-container>
'''

#import modules
from omero.gateway import BlitzGateway, MapAnnotationWrapper
from omero.constants.metadata import NSCLIENTMAPANNOTATION
import csv
import argparse
import logging

parser = argparse.ArgumentParser(description = 'Import metadata for images in Omero')
parser.add_argument('-u', '--username', type=str, required=True, help='Omero username that is importing the metadata to their images')
parser.add_argument('-w', '--password', type=str, required=True, help='Omero password for the user importing the metadata to their images')
parser.add_argument('-m', '--metadata-path', type=str, required=True, help='Path of the metadata file containing the metadata for the images in Omero')
parser.add_argument('-v','--verbose', action='store_true', required=False, help='Enable verbose mode (Prints out information as the script is running)')
args = parser.parse_args()


def add_annotations_to_image(conn, image_id: str, keys: list[str], values: list[str]) -> bool:
    '''
    Description:   
        This function adds the metadata information to the image with the provided id. The metadata shows up in Omero as key value pairs.
    Input:
        conn - the object used for establishing a connection with the Omero server
        image_id - the id of the image in Omero
        keys - the key attributes of the metadata for the image
        values - the values belonging to the attributes of the metadata for the image
    Output:
        success - a boolean representing whether the metadata has been successfully imported 
    '''

    #get the image object using the id
    image = conn.getObject("Image", image_id)

    #check that image exists with the id
    if image is None:
        print(f"Image with id {image_id} is not found")
        return False

    #check that the metadata keys and values line up
    if len(keys) != len(values):
        print(f"Error: The keys and values don't have the same length in the metadata for image with id: {image_id}")
        return False
    
    #delete existing metadata for the image to replace them with new ones
    annotations_to_delete = []

    #for each annotation
    for annotation in image.listAnnotations():
        annotations_to_delete.append(annotation.id)
    conn.deleteObjects('Annotation', annotations_to_delete, wait=True)

    #add the new metadata to image as an annotation    
    annotation = MapAnnotationWrapper(conn)
    namespace = NSCLIENTMAPANNOTATION #this enables client editing in Omero web
    annotation.setNs(namespace)
    annotation.setValue(zip(keys, values))
    annotation.save()

    #link the annotation to the image
    image.linkAnnotation(annotation)
    
    return True

            
def import_metadata(conn, metadata_path: str):
    '''
    Description:   
        This function imports the metadata information to the images dictated in the metadata file
    Input:
        conn - the object used for establishing a connection with the Omero server
        metadata_path - the file path of the metadata file
    '''
 
    #open the csv metadata file
    with open(metadata_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:

        #initalize reader and read the header row
        reader = csv.reader(csvfile)
        headers = next(reader)

        #for each header name (reformat header names if needed)
        # for i in range(len(headers)):

        #     #rem
        #     headers[i] = " ".join([h.capitalize() for h in headers[i].replace('_', ' ').split()])


        #for each row of the metadata file
        for row in reader:
            
            #retrieve the name of the image
            partial_name = row[0]
            
            #sql query to find all images in Omero that contains the partial name
            query = f"from Image as img where img.name like '%{partial_name}%'"
            matching_images = conn.getQueryService().findAllByQuery(query, None)

            #for each matching image
            for image in matching_images:

                #add the metadata annotation to the image
                success = add_annotations_to_image(conn, image.id.val, headers, row)

                if success:
                    logging.info(f"The metadata for image with id {image.id.val} is imported")
                else:
                    logging.error(f"Failed to import metadata for image with id: {image.id.val}")
   

if __name__ == "__main__":

    #connect to the Omero server
    conn = BlitzGateway(args.username, args.password, host="localhost", port=4064, secure=True)
    conn.connect()
    
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
    
    #import the metadata to Omero
    import_metadata(conn, args.metadata_path)

    #close the connection
    conn.close()