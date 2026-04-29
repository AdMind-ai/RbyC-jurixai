from datetime import datetime, timezone
from unittest.mock import Mock, patch

import jwt
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from integrations.models import DocumentIndex, IntegrationApiKey, IntegrationClient
from integrations.services.mcp_auth import (
    build_mcp_access_token,
    decode_mcp_access_token,
)
from integrations.views.document_index import query_terms_for_search, search_variants


class MCPAuthServiceTests(TestCase):
    def setUp(self):
        self.integration_client = IntegrationClient.objects.create(
            client_name="Cliente Teste",
            customer_code="cliente_teste",
            bucket_name="bucket-cliente-teste",
            active=True,
        )

    @override_settings(
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_build_mcp_access_token_contains_expected_claims(self):
        token = build_mcp_access_token(self.integration_client)
        payload = decode_mcp_access_token(token)

        self.assertEqual(payload["iss"], "backend-integrations")
        self.assertEqual(payload["aud"], "mcp-ricerca")
        self.assertEqual(payload["client_id"], self.integration_client.pk)
        self.assertEqual(payload["customer_code"], "cliente_teste")
        self.assertEqual(payload["bucket_name"], "bucket-cliente-teste")
        self.assertGreater(payload["exp"], payload["iat"])


class RicercaDocumentaleViewMCPAuthTests(TestCase):
    def setUp(self):
        self.integration_client = IntegrationClient.objects.create(
            client_name="Cliente Teste",
            customer_code="cliente_teste",
            bucket_name="bucket-cliente-teste",
            active=True,
        )
        raw_api_key = "integration-test-key"
        IntegrationApiKey.objects.create(
            client=self.integration_client,
            key_hash=IntegrationApiKey.hash_key(raw_api_key),
            active=True,
            description="test key",
        )
        self.api_client = APIClient()
        self.api_client.credentials(HTTP_AUTHORIZATION=f"Api-Key {raw_api_key}")

    @override_settings(
        OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE="pmpt_test",
        MCP_SERVER_URL="https://mcp.example.test/sse",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    @patch("integrations.views.ricerca_documentale.client.conversations.create")
    @patch("integrations.views.ricerca_documentale.client.responses.create")
    def test_ricerca_documentale_sends_bearer_token_to_mcp(
        self,
        mock_create_response,
        mock_create_conversation,
    ):
        mock_create_conversation.return_value = Mock(id="conv_test")
        mock_create_response.return_value = Mock(
            output_text='{"response":"ok","keys":[]}'
        )

        response = self.api_client.post(
            "/api/integrations/v1/ricerca-documentale/",
            {"input": "Liste os documentos sobre compliance"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        request_kwargs = mock_create_response.call_args.kwargs
        self.assertEqual(request_kwargs["tools"][0]["type"], "mcp")
        self.assertEqual(
            request_kwargs["tools"][0]["server_url"],
            "https://mcp.example.test/sse",
        )

        authorization_header = request_kwargs["tools"][0]["headers"][
            "Authorization"
        ]
        self.assertTrue(authorization_header.startswith("Bearer "))

        token = authorization_header.split(" ", 1)[1]
        payload = jwt.decode(
            token,
            "test-mcp-secret",
            algorithms=["HS256"],
            audience="mcp-ricerca",
            issuer="backend-integrations",
        )
        self.assertEqual(payload["client_id"], self.integration_client.pk)
        self.assertEqual(payload["customer_code"], "cliente_teste")
        self.assertEqual(payload["bucket_name"], "bucket-cliente-teste")

    @override_settings(
        OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE="pmpt_test",
        MCP_SERVER_URL="https://mcp.example.test/sse",
        INTEGRATION_API_KEY="legacy-shared-key",
    )
    @patch("integrations.views.ricerca_documentale.client.conversations.create")
    @patch("integrations.views.ricerca_documentale.client.responses.create")
    def test_ricerca_documentale_keeps_fallback_without_mcp_header_for_legacy_key(
        self,
        mock_create_response,
        mock_create_conversation,
    ):
        legacy_client = APIClient()
        legacy_client.credentials(HTTP_AUTHORIZATION="Api-Key legacy-shared-key")
        mock_create_conversation.return_value = Mock(id="conv_test")
        mock_create_response.return_value = Mock(
            output_text='{"response":"ok","keys":[]}'
        )

        response = legacy_client.post(
            "/api/integrations/v1/ricerca-documentale/",
            {"input": "Liste os documentos sobre compliance"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        request_kwargs = mock_create_response.call_args.kwargs
        self.assertNotIn("headers", request_kwargs["tools"][0])

    @override_settings(
        OPENAI_PROMPT_ID_RICERCA_DOCUMENTALE="pmpt_test",
        MCP_SERVER_URL="https://mcp.example.test/sse",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        AWS_STORAGE_BUCKET_NAME="bucket-cliente-teste",
    )
    @patch("integrations.views.ricerca_documentale.get_presigned_urls")
    @patch("integrations.views.ricerca_documentale.client.conversations.create")
    @patch("integrations.views.ricerca_documentale.client.responses.create")
    def test_ricerca_documentale_extracts_document_keys_from_tool_output(
        self,
        mock_create_response,
        mock_create_conversation,
        mock_get_presigned_urls,
    ):
        mock_create_conversation.return_value = Mock(id="conv_test")
        response_mock = Mock()
        response_mock.output_text = '{"response":"Encontrei 1 documento relevante."}'
        response_mock.model_dump.return_value = {
            "output": [
                {
                    "type": "mcp_call",
                    "output": [
                        {
                            "key": "pasta/documento-teste.pdf",
                            "filename": "documento-teste.pdf",
                        }
                    ],
                }
            ]
        }
        mock_create_response.return_value = response_mock
        mock_get_presigned_urls.return_value = {
            "pasta/documento-teste.pdf": "https://signed.example/pasta/documento-teste.pdf"
        }

        response = self.api_client.post(
            "/api/integrations/v1/ricerca-documentale/",
            {"input": "Liste os documentos sobre compliance"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_get_presigned_urls.assert_called_once_with(
            ["pasta/documento-teste.pdf"],
            bucket="bucket-cliente-teste",
        )
        self.assertEqual(
            response.data["documents_urls"],
            {
                "pasta/documento-teste.pdf": (
                    "https://signed.example/pasta/documento-teste.pdf"
                )
            },
        )


class InternalDocumentIndexAuthTests(TestCase):
    def setUp(self):
        self.integration_client = IntegrationClient.objects.create(
            client_name="Cliente Teste",
            customer_code="cliente_teste",
            bucket_name="bucket-cliente-teste",
            active=True,
        )

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_requires_bearer_token(self):
        client = APIClient()
        response = client.get(
            "/api/integrations/v1/internal/document-index/",
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Missing MCP bearer token.")

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_rejects_customer_code_mismatch(self):
        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.get(
            "/api/integrations/v1/internal/document-index/?customer_code=outro_cliente",
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["detail"],
            "customer_code mismatch for MCP bearer token.",
        )

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_query_matches_ad_dg_abbreviations(self):
        DocumentIndex.objects.create(
            client=self.integration_client,
            bucket_name="bucket-cliente-teste",
            object_key="CDA/2023/2023.06.13/Documenti/5. Direttore Generale/Replica SIM - Poteri AD e DG - 13.06.23.pdf",
            filename="Replica SIM - Poteri AD e DG - 13.06.23.pdf",
            extension=".pdf",
            size_bytes=1234,
            year="2023",
            document_type="nomina",
            document_family="nomina",
            topic_tags="direttore_generale,amministratore_delegato,nomina,poteri,deleghe",
            text_preview="Documento relativo ai poteri attribuiti ad AD e DG.",
            active=True,
        )

        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.get(
            (
                "/api/integrations/v1/internal/document-index/"
                "?query=amministratore delegato direttore generale poteri deleghe"
                "&year=2023"
                "&document_family=nomina"
                "&topic_tags=nomina,poteri,deleghe"
            ),
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertIn("Poteri AD e DG", response.json()[0]["filename"])


class DocumentIndexSearchHelpersTests(TestCase):
    def test_search_variants_expand_common_abbreviations(self):
        variants = search_variants("amministratore delegato")
        self.assertIn("ad", variants)

    def test_query_terms_for_search_includes_bigrams(self):
        terms = query_terms_for_search("direttore generale nomina")
        self.assertIn("direttore generale", terms)
