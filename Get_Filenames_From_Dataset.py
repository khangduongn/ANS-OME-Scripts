'''
Author: 
    Khang Duong

Last Updated: 
    11/25/2024

Description: 
    This Omero script allows the user to obtain the filenames of the images in Omero dataset(s).
    After running this script, a csv file of the filenames of the images in the dataset(s) will appear in the corresponding dataset(s) under the "Attachments" section. 
    The csv file has the filename "<dataset-name>_filenames.csv"

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
        3. Select "Get Filenames From Dataset". The interface for the script should appear.
        4. Enter the ID(s) of the dataset(s) where you want to retrieve the filenames of the images, separated by a comma (only needed if you are doing this for multiple datasets). There is a shortcut where you can select the dataset(s) before clicking on the gears icon, which will fill in the IDs entry without you having to enter the IDs yourself.
        5. Click "Run Script" once you have the dataset ID(s) entered
        6. After the script finishes running, you should see a "done" message.
        7. Click on the dataset and look at the "Attachments" tab, where you should see the csv file generated with the filenames. The file is usually called "<dataset_name>_filenames.csv"
'''

#import modules
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rstring, rlong
import omero.scripts as scripts
from omero.cmd import Delete2
import tempfile
import os


def attach_csv_file(conn, dataset, filenames: list[str]):
    '''
    Description:
        This function writes the filenames to the csv file to attach it to the dataset
    Input:
        conn - the object used for establishing a connection with the Omero server
        dataset - the Omero dataset object that the csv file will get attached to
        filenames - the list of filenames in the dataset
    Output:
        success - a boolean representing whether the metadata has been successfully imported 
    '''

    # create the temp directory and then temp file to write the csv data
    tmp_dir = tempfile.mkdtemp(prefix='Dataset_Image_Filenames')
    (fd, tmp_file) = tempfile.mkstemp(dir=tmp_dir, text=True)
    tmp_file = os.fdopen(fd, 'w')

    #this function to writes a line to the csv file
    def to_csv(ll):
        nl = len(ll)
        fmstr = "{}, "*(nl-1)+"{}\n"
        return fmstr.format(*ll)

    #construct the header of the csv file
    header = ['Filename']
    tmp_file.write(to_csv(header))

    # write the filename for each file to the csv file
    for filename in filenames:
        row = [filename]
        tmp_file.write(to_csv(row))
    tmp_file.close()

    #generate the name for the csv file
    name = "{}_filenames.csv".format(dataset.getName())

    #link the csv file to the dataset
    ann = conn.createFileAnnfromLocalFile(
        tmp_file, origFilePathAndName=name,
        ns='Dataset_Image_Filenames')
    ann = dataset.linkAnnotation(ann)

    #remove the temp file and temp directory
    os.remove(tmp_file)
    os.rmdir(tmp_dir)

    return "Done attaching csv to dataset"


def run_script():

    data_types = [rstring('Dataset')]
    client = scripts.client(
        'Get Filenames in Dataset(s)',
        """
    This script returns the list of filenames of the images in dataset(s).
        """,
        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="Choose source of images",
            values=data_types, default="Dataset"),

        scripts.List(
            "IDs", optional=False, grouping="2",
            description="Dataset IDs").ofType(rlong(0)),


        authors=["Khang Duong"],
        institutions=["Drexel ANS"],
    )

    try:
        #process the list of args above.
        script_params = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                script_params[key] = client.getInput(key, unwrap=True)

        #wrap client to use the Blitz Gateway
        conn = BlitzGateway(client_obj=client)
        print("Connection Established")

        data_type = script_params["Data_Type"]
        print(data_type)
        ids = script_params["IDs"]

        #get the datasets
        datasets = list(conn.getObjects(data_type, ids))
        print(ids)
        print("Dataset(s):")
        print(datasets)

        #if the datasets don't exist
        if len(datasets) == 0:
            client.setOutput("Message", rstring("No Dataset Found"))
            raise Exception
            
        #for each dataset
        for ds in datasets:

            # name of the file
            csv_name = "{}_filenames.csv".format(ds.getName())
            print(csv_name)

            # remove the csv if it exists
            for ann in ds.listAnnotations():
                if isinstance(ann, omero.gateway.FileAnnotationWrapper):
                    if ann.getFileName() == csv_name:
                        # if the name matches delete it
                        try:
                            delete = Delete2(
                                targetObjects={'FileAnnotation':
                                               [ann.getId()]})
                            handle = conn.c.sf.submit(delete)
                            conn.c.waitOnCmd(
                                handle, loops=10,
                                ms=500, failonerror=True,
                                failontimeout=False, closehandle=False)
                            print("Deleted existing csv")
                        except Exception as ex:
                            print("Failed to delete existing csv: {}".format(
                                ex.message))
                else:
                    print("No exisiting file")

            #get the filenames of the images
            filenames = []
            for img in ds.listChildren():
                filenames.append(img.getName())

            #attach the filenames data to csv file
            message = attach_csv_file(conn, ds, filenames)
            print(message)

        client.setOutput("Message", rstring("The script has finished"))

    finally:
        client.closeSession()


if __name__ == "__main__":
    run_script()