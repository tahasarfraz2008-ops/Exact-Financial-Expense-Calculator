from fastapi.testclient import TestClient

from app.presentation.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_calculation_100_div_3_times_3():
    response = client.post("/api/v1/calculations", json={"expression": "100 / 3 * 3"})
    assert response.status_code == 200
    body = response.json()
    assert body["exact_result"] == "100"
    assert body["is_exact"] is True


def test_create_calculation_100_div_3_is_flagged_repeating():
    response = client.post(
        "/api/v1/calculations", json={"expression": "100 / 3", "display_digits": 10}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["exact_result"] == "100/3"
    assert body["is_repeating"] is True


def test_get_calculation_by_id_round_trips():
    create_response = client.post("/api/v1/calculations", json={"expression": "10 / 6"})
    calculation_id = create_response.json()["calculation_id"]

    get_response = client.get(f"/api/v1/calculations/{calculation_id}")
    assert get_response.status_code == 200
    assert get_response.json()["exact_result"] == "5/3"


def test_get_unknown_calculation_returns_404():
    response = client.get("/api/v1/calculations/does-not-exist")
    assert response.status_code == 404


def test_invalid_expression_returns_400():
    response = client.post("/api/v1/calculations", json={"expression": "1 / 0"})
    assert response.status_code == 400


def test_round_endpoint():
    response = client.post(
        "/api/v1/round",
        json={"exact_value": "100/3", "decimal_places": 2, "rounding_mode": "HALF_UP"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rounded_value"] == "33.33"
    assert body["original_exact_value"] == "100/3"


def test_convert_endpoint():
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "100.00",
            "source_currency": "USD",
            "target_currency": "PKR",
            "exchange_rate": "278.4563",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["converted_settled_amount"] == "27845.63"
