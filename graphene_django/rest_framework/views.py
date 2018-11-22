import json
import copy

from django.utils import six

from graphql import get_default_backend
from graphql.error import format_error as format_graphql_error
from graphql.error import GraphQLError
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import exception_handler as rest_framework_exception_handler
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

from ..settings import graphene_settings
from ..views import instantiate_middleware
from .parsers import GraphQLJSONParser, GraphQLParser


def exception_handler(exc, context):
    #if isinstance(exc, GraphQLError):
    #    exc = exceptions.NotFound()

    response = rest_framework_exception_handler(exc, context)

    if response and hasattr(response, "data"):
        if isinstance(response.data, dict):
            errors = copy.deepcopy(response.data)
            response.data.clear()

            if "detail" in errors:
                errors["message"] = errors.pop("detail")

            if isinstance(errors, dict):
                response.data["errors"] = [errors]
            else:
                response.data["errors"] = errors

    return response


class GraphQLAPIView(APIView):
    graphiql_version = "0.11.10"
    graphiql_template = "graphene/graphiql.html"
    graphiql = False

    graphene_schema = None
    graphene_executor = None
    graphene_backend = None
    graphene_middleware = None
    graphene_root_value = None
    graphene_batch = False
    graphene_pretty = False

    renderer_classes = (JSONRenderer, TemplateHTMLRenderer)
    parser_classes = (GraphQLJSONParser, GraphQLParser, FormParser, MultiPartParser)

    def __init__(
        self,
        graphene_schema=None,
        graphene_executor=None,
        graphene_middleware=None,
        graphene_root_value=None,
        graphiql=False,
        graphene_pretty=False,
        graphene_batch=False,
        graphene_backend=None,
    ):
        if not graphene_schema:
            graphene_schema = graphene_settings.SCHEMA

        if graphene_backend is None:
            graphene_backend = get_default_backend()

        if graphene_middleware is None:
            graphene_middleware = graphene_settings.MIDDLEWARE

        self.graphene_schema = self.graphene_schema or graphene_schema
        if graphene_middleware is not None:
            self.graphene_middleware = list(instantiate_middleware(graphene_middleware))
        self.graphene_executor = graphene_executor
        self.graphene_root_value = graphene_root_value
        self.graphene_pretty = self.graphene_pretty or graphene_pretty
        self.graphiql = self.graphiql or graphiql
        self.graphene_batch = self.graphene_batch or graphene_batch
        self.graphene_backend = graphene_backend

        assert isinstance(
            self.graphene_schema, GraphQLSchema
        ), "A Schema is required to be provided to GraphQLView."
        assert not all(
            (graphiql, graphene_batch)
        ), "Use either graphiql or batch processing"

    # noinspection PyUnusedLocal
    def get_graphene_root_value(self, request):
        return self.graphene_root_value

    def get_graphene_middleware(self, request):
        return self.graphene_middleware

    def get_graphene_context(self, request):
        return {
            'view': self,
            'request': request,
        }

    def get_graphene_backend(self, request):
        return self.graphene_backend

    def get_renderer_context(self):
        """
        Add indent to rendered JSON if prettyprint is specified.
        """
        renderer_context = super(GraphQLAPIView, self).get_renderer_context()

        if self.graphene_pretty or renderer_context.get('request').GET.get('pretty', False):
            renderer_context["indent"] = 2

        return renderer_context

    def get_exception_handler(self):
        """
        Returns the exception handler that this view uses.
        """
        return exception_handler

    @classmethod
    def can_display_graphiql(cls, request, data):
        raw = "raw" in request.GET or "raw" in data
        return not raw and request.accepted_renderer.format == "html"

    @staticmethod
    def get_graphql_params(request, data):
        query = request.GET.get("query") or data.get("query")
        variables = request.GET.get("variables") or data.get("variables")
        id = request.GET.get("id") or data.get("id")

        if variables and isinstance(variables, six.text_type):
            try:
                variables = json.loads(variables)
            except Exception:
                raise exceptions.ParseError({"message": "Variables are invalid JSON."})

        operation_name = request.GET.get("operationName") or data.get(
            "operationName"
        )
        if operation_name == "null":
            operation_name = None

        return query, variables, operation_name, id

    @staticmethod
    def format_graphene_error(error):
        if isinstance(error, GraphQLError):
            return format_graphql_error(error)

        return {"message": six.text_type(error)}

    def execute_graphql_request(
        self, request, query, variables, operation_name, show_graphiql=False
    ):
        if not query:
            if show_graphiql:
                return None
            raise exceptions.ValidationError({"message": "Must provide query string."})

        try:
            backend = self.get_graphene_backend(request)
            document = backend.document_from_string(self.graphene_schema, query)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        if request.method.lower() == "get":
            operation_type = document.get_operation_type(operation_name)
            if operation_type and operation_type != "query":
                if show_graphiql:
                    return None

                raise exceptions.MethodNotAllowed(
                    method=request.method,
                    detail="Can only perform a {} operation from a POST request.".format(
                        operation_type
                    ),
                )

        try:
            extra_options = {}
            if self.graphene_executor:
                # We only include it optionally since
                # executor is not a valid argument in all backends
                extra_options["executor"] = self.graphene_executor

            return document.execute(
                root=self.get_graphene_root_value(request),
                variables=variables,
                operation_name=operation_name,
                context=self.get_graphene_context(request),
                middleware=self.get_graphene_middleware(request),
                **extra_options
            )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

    def get(self, request, format=None):
        return self.process_request(request, format)

    def post(self, request, format=None):
        return self.process_request(request, format)

    def process_request(self, request, format=None):
        show_graphiql = self.graphiql and self.can_display_graphiql(request, request.data)

        if self.graphene_batch:
            responses = [self.get_response(request, entry) for entry in request.data]
            result = [response[0] for response in responses]
            status_code = (
                responses and max(responses, key=lambda response: response[1])[1] or 200
            )
        else:
            result, status_code = self.get_response(request, request.data, show_graphiql)

        if show_graphiql:
            query, variables, operation_name, id = self.get_graphql_params(request, request.data)
            return Response(
                {
                    "graphiql_version": self.graphiql_version,
                    "query": query or "",
                    "variables": json.dumps(variables) or "",
                    "operation_name": operation_name or "",
                    "result": json.dumps(result) or "",
                },
                template_name=self.graphiql_template,
            )

        return Response(result, status=status_code)

    def get_response(self, request, data, show_graphiql=False):
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(
            request, query, variables, operation_name, show_graphiql
        )

        status_code = 200
        if execution_result:
            response = {}

            if execution_result.errors:
                response["errors"] = [
                    self.format_graphene_error(e) for e in execution_result.errors
                ]

            if execution_result.invalid:
                status_code = 400
            else:
                response["data"] = execution_result.data

            if self.graphene_batch:
                response["id"] = id
                response["status"] = status_code

            result = response
        else:
            result = None

        return result, status_code
