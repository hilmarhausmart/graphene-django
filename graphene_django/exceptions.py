class GraphQLAPIException(Exception):
    def __init__(self, response, message=None, *args, **kwargs):
        self.response = response
        self.message = message = message or response.content.decode()
        super(GraphQLAPIException, self).__init__(message, *args, **kwargs)
