# To run this script in the background while outputting the debug messages, run the following command (Replace the log file with whatever log file you want):
# nohup sudo ./reimport_images_run.sh > ~/Reimport_Logs.txt &
# NOTE: Before running this script, edit this file and replace following placeholders with the appropriate credentials in the command below:
# omero_server_docker_container_name, path_to_reimport_images_script_in_docker, username, password, path_to_import_folder_in_docker
docker exec -i omero_server_docker_container_name /opt/omero/server/venv3/bin/python3 path_to_reimport_images_script_in_docker -u username -w password -i path_to_import_folder_in_docker -v