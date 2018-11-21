import codecs

from django.conf import settings
from django.utils import six

from rest_framework import renderers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser, JSONParser
from rest_framework.settings import api_settings


class GraphQLJSONParser(JSONParser):
    """
    Parses JSON-serialized data.
    """

    media_type = "application/json"
    renderer_class = renderers.JSONRenderer
    strict = api_settings.STRICT_JSON

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        request_json = super(GraphQLJSONParser, self).parse(
            stream, media_type, parser_context
        )
        parser_context = parser_context or {}
        view = parser_context.get("view", None)
        graphene_batch = (
            view and hasattr(view, "graphene_batch") and view.graphene_batch
        )

        try:
            if graphene_batch:
                assert isinstance(request_json, list), (
                    "Batch requests should receive a list, but received {}."
                ).format(repr(request_json))
                assert (
                    len(request_json) > 0
                ), "Received an empty list in the batch request."
            else:
                assert isinstance(
                    request_json, dict
                ), "The received data is not a valid JSON query."
        except AssertionError as e:
            raise ParseError("JSON parse error - %s" % six.text_type(e))

        return request_json


class GraphQLParser(BaseParser):
    """
    Parses GraphQL-serialized data.
    """

    media_type = "application/graphql"
    renderer_class = renderers.JSONRenderer

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as GraphQL and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)
        decoded_stream = codecs.getreader(encoding)(stream)

        return {"query": decoded_stream.read()}
