from datetime import datetime, timezone
from datetime import date
from unittest.mock import Mock, patch

import jwt
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from integrations.models import DocumentIndex, IntegrationApiKey, IntegrationClient
from integrations.services.mcp_auth import (
    build_mcp_access_token,
    decode_mcp_access_token,
)
from integrations.services.ricerca_documentale_runtime import (
    extract_ricerca_documentale_response_payload,
)
from core.services.document_retrieval.intent_classifier import classify_document_search_intent
from core.services.document_retrieval.presearch import (
    build_retrieval_guidance_candidates,
    build_presearch_candidates,
    should_run_presearch,
)
from core.services.document_retrieval.prompt_context import build_document_search_input
from core.services.document_retrieval.retrieval_strategies import get_retrieval_strategy
from integrations.views.document_index import (
    build_document_search_query_text,
    compute_postgres_fts_candidate_limit,
    query_terms_for_search,
    search_variants,
    score_document_match,
    score_fts_alignment,
    sort_documents_by_relevance,
)


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
    @patch("integrations.views.ricerca_documentale.get_presigned_urls_for_document_keys")
    @patch("integrations.views.ricerca_documentale.client.conversations.create")
    @patch("integrations.views.ricerca_documentale.client.responses.create")
    def test_ricerca_documentale_extracts_document_keys_from_tool_output(
        self,
        mock_create_response,
        mock_create_conversation,
        mock_get_presigned_urls_for_document_keys,
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
        mock_get_presigned_urls_for_document_keys.return_value = {
            "pasta/documento-teste.pdf": "https://signed.example/pasta/documento-teste.pdf"
        }

        response = self.api_client.post(
            "/api/integrations/v1/ricerca-documentale/",
            {"input": "Liste os documentos sobre compliance"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_get_presigned_urls_for_document_keys.assert_called_once_with(
            ["pasta/documento-teste.pdf"],
            customer_code="cliente_teste",
            fallback_bucket="bucket-cliente-teste",
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

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_query_matches_rso_abbreviation(self):
        DocumentIndex.objects.create(
            client=self.integration_client,
            bucket_name="bucket-cliente-teste",
            object_key=(
                "customer0047/activity33098/"
                "172-1776855582-replica-sim-rso_31032026-v.03.docx"
            ),
            filename="172-1776855582-replica-sim-rso_31032026-v.03.docx",
            extension=".docx",
            size_bytes=4321,
            year="2026",
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            text_preview="Relazione sulla Struttura Organizzativa approvata dal CdA.",
            active=True,
        )

        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.get(
            (
                "/api/integrations/v1/internal/document-index/"
                "?query=Quando%20%C3%A8%20stata%20approvata%20l%27ultima%20RSO"
            ),
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertIn("replica-sim-rso", response.json()[0]["filename"].lower())

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_query_matches_search_text(self):
        DocumentIndex.objects.create(
            client=self.integration_client,
            bucket_name="bucket-cliente-teste",
            object_key="customer0047/activity33098/verbale-speciale.docx",
            filename="verbale-speciale.docx",
            extension=".docx",
            size_bytes=2048,
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="governance",
            search_text=(
                "verbale-speciale.docx customer0047/activity33098/verbale-speciale.docx "
                "verbale_cda verbale governance DeltaBlu 7821 presidio interno"
            ),
            active=True,
        )

        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.get(
            (
                "/api/integrations/v1/internal/document-index/"
                "?query=DeltaBlu 7821 presidio interno"
            ),
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["filename"], "verbale-speciale.docx")

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_query_matches_extracted_text(self):
        DocumentIndex.objects.create(
            client=self.integration_client,
            bucket_name="bucket-cliente-teste",
            object_key="customer0047/activity33098/verbale-speciale.docx",
            filename="verbale-speciale.docx",
            extension=".docx",
            size_bytes=2048,
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="governance",
            text_preview="Verbale del consiglio.",
            extracted_text=(
                "Nel corso della seduta viene discussa la soglia operativa "
                "straordinaria DeltaBlu 7821 per il presidio interno."
            ),
            active=True,
        )

        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.get(
            (
                "/api/integrations/v1/internal/document-index/"
                "?query=DeltaBlu 7821 presidio interno"
            ),
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["filename"], "verbale-speciale.docx")

    @override_settings(
        DOCUMENT_INDEX_API_KEY="internal-index-key",
        MCP_INTERNAL_AUTH_SECRET="test-mcp-secret",
        MCP_INTERNAL_AUTH_ISSUER="backend-integrations",
        MCP_INTERNAL_AUTH_AUDIENCE="mcp-ricerca",
        MCP_INTERNAL_AUTH_TTL_SECONDS=300,
    )
    def test_internal_document_index_content_update_persists_extracted_text(self):
        document = DocumentIndex.objects.create(
            client=self.integration_client,
            bucket_name="bucket-cliente-teste",
            object_key="customer0047/activity33098/verbale-speciale.docx",
            filename="verbale-speciale.docx",
            extension=".docx",
            size_bytes=2048,
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="",
            control_function_tags="",
            text_preview="",
            extracted_text="",
            extraction_status=DocumentIndex.STATUS_PENDING,
            active=True,
        )

        client = APIClient()
        token = build_mcp_access_token(self.integration_client)
        response = client.post(
            "/api/integrations/v1/internal/document-index-content/",
            {
                "key": document.object_key,
                "text_preview": "Verbale del consiglio del 9 giugno 2025",
                "extracted_text": (
                    "Verbale del consiglio del 9 giugno 2025. "
                    "Approvazione delle modifiche alla Relazione sulla Struttura Organizzativa."
                ),
            },
            format="json",
            HTTP_X_INTERNAL_API_KEY="internal-index-key",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertIn(
            "Relazione sulla Struttura Organizzativa",
            document.extracted_text,
        )
        self.assertEqual(document.extraction_status, DocumentIndex.STATUS_READY)


class DocumentIndexSearchHelpersTests(TestCase):
    def test_build_document_search_query_text_prefers_raw_query(self):
        self.assertEqual(
            build_document_search_query_text('"presidio interno" rischi informatici', ["presidio interno", "rischi informatici"]),
            '"presidio interno" rischi informatici',
        )

    def test_compute_postgres_fts_candidate_limit_is_bounded(self):
        self.assertEqual(compute_postgres_fts_candidate_limit(5), 30)
        self.assertEqual(compute_postgres_fts_candidate_limit(40), 80)
        self.assertEqual(compute_postgres_fts_candidate_limit(100), 80)

    def test_score_fts_alignment_caps_bonus(self):
        document = DocumentIndex(filename="x", object_key="x")
        document.fts_rank = 0.9
        self.assertGreater(score_fts_alignment(document), 0)

        high_rank_document = DocumentIndex(filename="y", object_key="y")
        high_rank_document.fts_rank = 10
        self.assertEqual(score_fts_alignment(high_rank_document), 25)

    def test_score_document_match_prefers_verbale_for_governance_query(self):
        query_terms = query_terms_for_search(
            "verbale consiglio di amministrazione approvazione relazione struttura organizzativa"
        )

        verbale_document = DocumentIndex(
            filename="verbale-cda-09062025.docx",
            object_key="docs/verbale-cda-09062025.docx",
            document_family="verbale_cda",
            topic_tags="struttura_organizzativa",
        )
        relazione_document = DocumentIndex(
            filename="rso_31032026_v03_clean.docx",
            object_key="docs/rso_31032026_v03_clean.docx",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
        )

        self.assertGreater(
            score_document_match(verbale_document, query_terms),
            score_document_match(relazione_document, query_terms),
        )

    def test_score_document_match_prefers_policy_for_policy_query(self):
        query_terms = query_terms_for_search("policy gestione rischi informatici")

        policy_document = DocumentIndex(
            filename="policy-rischi-informatici.docx",
            object_key="docs/policy-rischi-informatici.docx",
            document_family="policy",
            topic_tags="risk, ict, cybersecurity",
        )
        verbale_document = DocumentIndex(
            filename="verbale-cda-09062025.docx",
            object_key="docs/verbale-cda-09062025.docx",
            document_family="verbale_cda",
            topic_tags="risk, ict, cybersecurity",
        )

        self.assertGreater(
            score_document_match(policy_document, query_terms),
            score_document_match(verbale_document, query_terms),
        )

    def test_search_variants_expand_common_abbreviations(self):
        variants = search_variants("amministratore delegato")
        self.assertIn("ad", variants)

    def test_query_terms_for_search_includes_bigrams(self):
        terms = query_terms_for_search("direttore generale nomina")
        self.assertIn("direttore generale", terms)

    def test_search_variants_expand_rso_abbreviation(self):
        variants = search_variants("rso")
        self.assertIn("struttura organizzativa", variants)
        self.assertIn("relazione sulla struttura organizzativa", variants)

    def test_document_index_infers_rso_family_and_topic_tag(self):
        object_key = "customer0047/activity33098/replica-sim-rso_31032026-v.03.docx"
        self.assertEqual(
            DocumentIndex.infer_document_family(object_key),
            "relazione_struttura_organizzativa",
        )
        self.assertIn(
            "struttura_organizzativa",
            DocumentIndex.infer_topic_tags(object_key),
        )

    def test_document_index_infers_document_date_from_filename(self):
        self.assertEqual(
            DocumentIndex.infer_document_date(
                "customer0047/activity33098/replica-sim-rso_31032026-v.03.docx"
            ),
            date(2026, 3, 31),
        )

    def test_sort_documents_prioritizes_document_date_for_latest_rso(self):
        older_document = DocumentIndex(
            filename="replica-sim-rso_09062025-v.01.docx",
            object_key="customer0047/activity33098/replica-sim-rso_09062025-v.01.docx",
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2025, 6, 9),
            text_preview=(
                "RSO approvata dal CdA con approvazione formale della struttura "
                "organizzativa e delibera del consiglio."
            ),
        )
        newer_document = DocumentIndex(
            filename="replica-sim-rso_31032026-v.03.docx",
            object_key="customer0047/activity33098/replica-sim-rso_31032026-v.03.docx",
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2026, 3, 31),
            text_preview="RSO aggiornata.",
        )

        sorted_documents = sort_documents_by_relevance(
            [older_document, newer_document],
            query_terms_for_search("Quando è stata approvata l'ultima RSO"),
        )

        self.assertEqual(
            sorted_documents[0].filename,
            "replica-sim-rso_31032026-v.03.docx",
        )

    def test_sort_documents_handles_mixed_document_dates_for_non_recency_query(self):
        undated_document = DocumentIndex(
            filename="policy-rischi-informatici.docx",
            object_key="customer0047/activity18635/policy-rischi-informatici.docx",
            document_type="policy",
            document_family="altro",
            topic_tags="risk,ict",
            text_preview="Policy in materia di gestione dei rischi informatici derivanti da terzi.",
        )
        dated_document = DocumentIndex(
            filename="verbale-rischi-informatici.docx",
            object_key="customer0047/activity18635/verbale-rischi-informatici.docx",
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="risk,ict,governance",
            document_date=date(2025, 2, 10),
            text_preview="Presidio interno sui rischi informatici discusso dal consiglio.",
        )

        sorted_documents = sort_documents_by_relevance(
            [undated_document, dated_document],
            query_terms_for_search("presidio interno rischi informatici"),
        )

        self.assertEqual(sorted_documents[0].filename, "verbale-rischi-informatici.docx")

    def test_presearch_candidates_prioritize_structured_rso_documents(self):
        client = IntegrationClient.objects.create(
            client_name="Cliente Presearch",
            customer_code="cliente_presearch",
            bucket_name="bucket-presearch",
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-presearch",
            object_key="CDA/2025/rso-09062025.docx",
            filename="rso-09062025.docx",
            extension=".docx",
            size_bytes=100,
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2025, 6, 9),
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-presearch",
            object_key="CDA/2026/rso-31032026.docx",
            filename="rso-31032026.docx",
            extension=".docx",
            size_bytes=100,
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2026, 3, 31),
            active=True,
        )

        user_input = "Confronta la RSO 2024 e 2025"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)
        candidates = build_presearch_candidates(
            user_input=user_input,
            intent_classification=intent,
            retrieval_strategy=strategy,
            customer_code="cliente_presearch",
        )


        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].filename, "rso-31032026.docx")

    def test_presearch_is_disabled_for_approval_or_verbale_queries(self):
        user_input = "Approvazione delle modifiche alla Relazione sulla Struttura Organizzativa della Societa"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)

        self.assertFalse(
            should_run_presearch(
                user_input=user_input,
                intent_classification=intent,
                retrieval_strategy=strategy,
            )
        )

    def test_presearch_is_disabled_for_non_year_grouped_queries(self):
        user_input = "Nomina dell'amministratore delegato e attribuzione dei poteri"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)

        self.assertFalse(
            should_run_presearch(
                user_input=user_input,
                intent_classification=intent,
                retrieval_strategy=strategy,
            )
        )

    def test_retrieval_guidance_skips_related_candidates_when_presearch_is_disabled(self):
        client = IntegrationClient.objects.create(
            client_name="Cliente Guidance",
            customer_code="cliente_guidance",
            bucket_name="bucket-guidance",
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-guidance",
            object_key="CDA/2025/verbale-cda-09062025.docx",
            filename="verbale-cda-09062025.docx",
            extension=".docx",
            size_bytes=100,
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="struttura_organizzativa",
            text_preview="Approvazione delle modifiche alla Relazione sulla Struttura Organizzativa.",
            document_date=date(2025, 6, 9),
            active=True,
        )

        user_input = "Approvazione delle modifiche alla Relazione sulla Struttura Organizzativa della Societa"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)
        guidance = build_retrieval_guidance_candidates(
            user_input=user_input,
            intent_classification=intent,
            retrieval_strategy=strategy,
            customer_code="cliente_guidance",
        )

        self.assertEqual(guidance.presearch_candidates, [])
        self.assertEqual(guidance.related_approval_candidates, [])

    def test_prompt_context_marks_primary_presearch_candidate(self):
        client = IntegrationClient.objects.create(
            client_name="Cliente Prompt",
            customer_code="cliente_prompt",
            bucket_name="bucket-prompt",
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-prompt",
            object_key="CDA/2025/rso-09062025.docx",
            filename="rso-09062025.docx",
            extension=".docx",
            size_bytes=100,
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2025, 6, 9),
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-prompt",
            object_key="CDA/2026/rso-31032026.docx",
            filename="rso-31032026.docx",
            extension=".docx",
            size_bytes=100,
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            document_date=date(2026, 3, 31),
            active=True,
        )

        user_input = "Confronta la RSO 2024 e 2025"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)
        candidates = build_presearch_candidates(
            user_input=user_input,
            intent_classification=intent,
            retrieval_strategy=strategy,
            customer_code="cliente_prompt",
        )

        model_input = build_document_search_input(
            user_input,
            intent,
            strategy,
            presearch_candidates=candidates,
        )

        self.assertIn(
            "presearch_available=true",
            model_input,
        )
        self.assertIn(
            "presearch_candidate_count=2",
            model_input,
        )
        self.assertIn(
            "get_document(mode='full')",
            model_input,
        )
        self.assertNotIn("presearch_primary_candidate=", model_input)
        self.assertNotIn("presearch_primary_excerpt=", model_input)
        self.assertNotIn("presearch_primary_sibling_signature=", model_input)

    def test_related_approval_candidates_are_not_exposed_in_prompt_context(self):
        client = IntegrationClient.objects.create(
            client_name="Cliente Approval",
            customer_code="cliente_approval",
            bucket_name="bucket-approval",
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-approval",
            object_key="CDA/2026/rso-31032026.docx",
            filename="rso-31032026.docx",
            extension=".docx",
            size_bytes=100,
            document_type="relazione",
            document_family="relazione_struttura_organizzativa",
            topic_tags="struttura_organizzativa",
            text_preview="Relazione sulla Struttura Organizzativa - Anno 2025",
            document_date=date(2026, 3, 31),
            active=True,
        )
        DocumentIndex.objects.create(
            client=client,
            bucket_name="bucket-approval",
            object_key="CDA/2025/verbale-cda-09062025.docx",
            filename="verbale-cda-09062025.docx",
            extension=".docx",
            size_bytes=100,
            document_type="verbale",
            document_family="verbale_cda",
            topic_tags="struttura_organizzativa",
            text_preview="Approvazione delle modifiche alla Relazione sulla Struttura Organizzativa.",
            document_date=date(2025, 6, 9),
            active=True,
        )

        user_input = "Confronta la RSO 2024 e 2025"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)
        candidates = build_presearch_candidates(
            user_input=user_input,
            intent_classification=intent,
            retrieval_strategy=strategy,
            customer_code="cliente_approval",
        )
        related_approval_candidates = candidates[:1]

        model_input = build_document_search_input(
            user_input,
            intent,
            strategy,
            presearch_candidates=candidates,
            related_approval_candidates=related_approval_candidates,
        )

        self.assertTrue(candidates)
        self.assertTrue(related_approval_candidates)
        self.assertNotIn(
            "related_approval_candidates_available=true",
            model_input,
        )
        self.assertNotIn(
            "related_approval_candidate_count=1",
            model_input,
        )
        self.assertNotIn("latest_explicit_approval_candidate_1=", model_input)

    def test_prompt_context_relaxes_structured_preferences_for_approval_queries(self):
        user_input = "Quando e stata approvata la Relazione sulla Struttura Organizzativa dal consiglio di amministrazione?"
        intent = classify_document_search_intent(user_input)
        strategy = get_retrieval_strategy(intent.intent_type)

        model_input = build_document_search_input(
            user_input,
            intent,
            strategy,
        )

        self.assertNotIn("preferred_document_families=", model_input)
        self.assertNotIn("preferred_topic_tags=", model_input)
        self.assertNotIn("group_by=", model_input)
        self.assertNotIn("evidence_grouping=", model_input)
        self.assertNotIn("retrieval_notes=", model_input)
        self.assertNotIn("stopping_rule=", model_input)
        self.assertNotIn("matched_signals=", model_input)
        self.assertNotIn("evidence_plan=", model_input)
        self.assertIn("evita catene di ricerche esplorative", model_input)


class RicercaDocumentaleRuntimeTests(TestCase):
    def test_extract_response_payload_accepts_raw_output_text(self):
        raw_output = (
            '{"response_text":"Risposta test","keys":["docs/test.pdf"]}'
        )

        payload = extract_ricerca_documentale_response_payload(raw_output)

        self.assertEqual(payload.raw_output, raw_output)
        self.assertEqual(payload.response_text, "Risposta test")
        self.assertEqual(payload.response_keys, ["docs/test.pdf"])
