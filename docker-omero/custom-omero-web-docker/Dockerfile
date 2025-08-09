FROM openmicroscopy/omero-web-standalone:5

USER root

RUN /opt/omero/web/venv3/bin/pip install -U omero-gallery

ADD omero-gallery-app.omero /opt/omero/web/config/

USER omero-web
