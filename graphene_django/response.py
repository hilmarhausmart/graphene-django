"""
The Response class in REST framework is similar to HTTPResponse, except that
it is initialized with unrendered data, instead of a pre-rendered string.

The appropriate renderer is called during Django's template response rendering.
"""
from __future__ import unicode_literals

from django.http import HttpResponse
from django.template.response import SimpleTemplateResponse
from django.utils import six
from django.utils.six.moves.http_client import responses

from rest_framework.serializers import Serializer


class Response(HttpResponse):
    """
    A Response that keeps the original data as an attribute.
    """

    def __init__(self, data=None, *args, **kwargs):
        """
            Alter the response to keep original data.
        """
        super(Response, self).__init__(content=data, *args, **kwargs)

        self.data = data
