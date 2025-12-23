from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """OpenAPI extension that describes the project's API key auth.

    drf-spectacular discovers subclasses of `OpenApiAuthenticationExtension`
    when the module is imported. We import this module from the app's
    `ready()` so the extension is registered and the schema generator can
    produce the proper `securitySchemes` entry.
    """

    target_class = "integrations.authentication.APIKeyAuthentication"
    match_subclasses = True
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        # Match the project's settings which use the `Authorization` header
        # with the `Api-Key` scheme. Keep this aligned with
        # `SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"]["ApiKeyAuth"]`.
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
        }
