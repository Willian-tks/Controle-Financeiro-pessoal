import unittest

from pydantic import ValidationError

from api.schemas import (
    ListCreateRequest,
    ListDetailResponse,
    ListItemCreateRequest,
    ListSummaryResponse,
)


class ListsPhase2SchemaTests(unittest.TestCase):
    def test_list_create_request_accepts_valid_payload(self):
        payload = ListCreateRequest(
            name="Compras da semana",
            type="Mercado",
            description="  itens essenciais  ",
            status="ATIVA",
        )
        self.assertEqual("Compras da semana", payload.name)
        self.assertEqual("Mercado", payload.type)
        self.assertEqual("itens essenciais", payload.description)
        self.assertEqual("ativa", payload.status)

    def test_list_create_request_rejects_invalid_status(self):
        with self.assertRaises(ValidationError):
            ListCreateRequest(name="Lista", type="Casa", status="rascunho")

    def test_list_item_create_request_rejects_invalid_numbers(self):
        with self.assertRaises(ValidationError):
            ListItemCreateRequest(name="Sabão", quantity=0, suggested_value=5)
        with self.assertRaises(ValidationError):
            ListItemCreateRequest(name="Sabão", quantity=1, suggested_value=-1)

    def test_list_item_create_request_accepts_unit_and_rejects_invalid_unit(self):
        payload = ListItemCreateRequest(name="Leite", quantity=2, unit="L", suggested_value=7.5)
        self.assertEqual("l", payload.unit)
        with self.assertRaises(ValidationError):
            ListItemCreateRequest(name="Leite", quantity=2, unit="caixa", suggested_value=7.5)

    def test_list_detail_response_has_safe_defaults(self):
        response = ListDetailResponse(
            id=1,
            workspace_id=101,
            name="Compras",
            type="Mercado",
            status="ativa",
        )
        self.assertEqual([], response.items)
        self.assertEqual(ListSummaryResponse(), response.summary)


if __name__ == "__main__":
    unittest.main()
