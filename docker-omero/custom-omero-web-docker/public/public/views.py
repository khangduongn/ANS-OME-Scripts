#
# Copyright (c) 2017 University of Dundee.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from django.http import Http404
from concurrent.futures import ThreadPoolExecutor
from omeroweb.decorators import login_required, render_response
from omero.gateway import MapAnnotationWrapper

def get_annotations(image, conn):
    """Retrieve image metadata for a given result."""
    image = conn.getObject("Image", image.getId())
    annotations = image.listAnnotations()
    
    metadata = []
    for ann in annotations:
        if isinstance(ann, MapAnnotationWrapper):
            metadata = ann.getValue()
            break

    return {'name': image.getName(), 'id': image.getId(), 'metadata': metadata}


@login_required()
@render_response()
def show_dataset(request, dataset_id, conn=None, **kwargs):
    """
    Show a dataset
    """

    dataset = conn.getObject("Dataset", dataset_id)

    if dataset is None:
        raise Http404

    context = {'template': "public/show_dataset.html"}
    context['dataset'] = dataset

    return context

# login_required: if not logged-in, will redirect to webclient
# login page. Then back to here, passing in the 'conn' connection
# and other arguments **kwargs.
@login_required()
@render_response()
def index(request, conn=None, **kwargs):

    context = {'template': "public/index.html"}
  
    return context

@login_required()
@render_response()
def search(request, conn=None, **kwargs):

    context = {'template': "public/search.html"}

    if request.method == 'GET' and 'value' in request.GET:
        value = request.GET.get('value').replace('"', '\\"')

        results = conn.getQueryService().findAllByFullText("Image", f'annotation:"{value}"', None)

        with ThreadPoolExecutor(max_workers=20) as executor:
            context['images'] = list(executor.map(lambda result: get_annotations(result, conn), results))

    return context